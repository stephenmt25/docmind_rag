"""
Business logic for RAG pipeline.
Separated from HTTP concerns so it's testable and reusable.
"""
import os
import time
from google import genai
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def extract_text_from_file(filepath: str) -> str:
    """Extract text from PDF or txt file"""
    if filepath.endswith(".pdf"):
        reader = PdfReader(filepath)
        return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    elif filepath.endswith(".txt"):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError("Only .pdf and .txt files are supported")


def chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " "]
    )
    return splitter.split_text(text)


def embed_text(text: str) -> list[float]:
    """Generate embedding using Gemini"""
    result = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values


def ingest_document(filepath: str, filename: str, chunk_size: int = 512) -> int:
    """
    Ingest a document: extract text, chunk, embed, store.
    Returns the number of chunks created.
    
    Uses rate limiting (35s pause every 50 chunks) to respect API limits.
    """
    text = extract_text_from_file(filepath)
    chunks = chunk_text(text, chunk_size=chunk_size)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for i, chunk in enumerate(chunks):
            embedding = embed_text(chunk)
            cursor.execute(
                "INSERT INTO documents (filename, chunk_index, content, embedding) VALUES (%s, %s, %s, %s)",
                (filename, i, chunk, embedding)
            )
            
            # Rate limiting: pause every 50 chunks
            if (i + 1) % 50 == 0 and (i + 1) < len(chunks):
                time.sleep(35)
    
    return len(chunks)

def rewrite_query(question: str, chat_history: list[dict]) -> str:
    """
    Rewrites a conversational query into a standalone query using the chat history.
    """
    if not chat_history:
        return question
        
    history_text = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history])
    
    prompt = f"""You are a Search Optimizer. Given a conversation history and a new question, your ONLY goal is to output 2-3 keywords that represent the SUBJECT being discussed.
    
RULES:
- NO conversational filler (e.g., remove "summarize", "explain", "tell me").
- NO formatting instructions (e.g., remove "one sentence", "bullet points").
- Resolve all pronouns (it, they, them) to the actual topic.

Example:
History: "What are tokens?" "Tokens are subword units."
Question: "Can you summarize it in one sentence?"
Output: "tokens definition summary"

History:
{history_text}

Latest Question: {question}

Output Search Keywords:"""
    
    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Query rewrite failed: {e}")
        return question
    
def retrieve_chunks(question: str, top_k: int = 5) -> list[dict]:
    """
    Retrieve top_k most similar chunks for a question.
    Returns list of dicts with filename, chunk_index, content, similarity.
    """
    question_embedding = embed_text(question)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT filename, chunk_index, content,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM documents
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (question_embedding, question_embedding, top_k)
        )
        rows = cursor.fetchall()
        return [
            {
                "filename": r[0],
                "chunk_index": r[1],
                "content": r[2],
                "similarity": r[3]
            }
            for r in rows
        ]


def generate_answer(question: str, chunks: list[dict], chat_history: list[dict] = None) -> str:
    """
    Generate an answer using retrieved chunks as context.
    Returns the answer text.
    """
    # Format chat history if it exists
    history_text = ""
    if chat_history:
        history_text = "--- PREVIOUS CONVERSATION HISTORY ---\n"
        for msg in chat_history:
            history_text += f"{msg['role'].upper()}: {msg['content']}\n"
        history_text += "-------------------------------------\n\n"

    # Build context from chunks
    context = "\n\n---\n\n".join(
        f"Source: {c['filename']}, chunk {c['chunk_index']}\n{c['content']}"
        for c in chunks
    )
    
    prompt = f"""You are a helpful assistant. Answer the question below using ONLY the context provided.
If the context does not contain enough information to answer, say "I don't have enough information to answer that."
Do not make anything up.

{history_text}Context:
{context}

Current Question: {question}

Answer:"""
    
    response = client.models.generate_content(
        model="models/gemini-3-flash-preview",
        contents=prompt
    )
    return response.text


def answer_question(question: str, top_k: int = 5) -> dict:
    """
    Full RAG pipeline: retrieve chunks + generate answer.
    Returns dict with question, answer, and sources.
    """
    chunks = retrieve_chunks(question, top_k=top_k)
    
    if not chunks:
        return {
            "question": question,
            "answer": "No documents have been uploaded yet. Please upload a document first.",
            "sources": []
        }
    
    answer = generate_answer(question, chunks)
    
    return {
        "question": question,
        "answer": answer,
        "sources": chunks
    }

def check_if_grounded(chunks: list[dict], answer: str) -> bool:
    """
    Evaluates if the generated answer is grounded in the provided context.
    Returns True if grounded, False if hallucinated.
    """
    if not chunks:
        return False
        
    context = "\n\n".join([c['content'] for c in chunks])
    
    prompt = f"""You are a strict grading assistant. 
Your job is to check if the ANSWER is entirely supported by the CONTEXT.
If the ANSWER contains any facts or claims not present in the CONTEXT, you must reject it.

CONTEXT:
{context}

ANSWER:
{answer}

Is the answer completely grounded in the context? Reply with exactly YES or NO.
"""
    try:
        response = client.models.generate_content(
            model="models/gemini-3-flash-preview",
            contents=prompt
        )
        # Check if the model replied with "YES"
        return "YES" in response.text.strip().upper()
    except Exception as e:
        print(f"Grounding check failed: {e}")
        return False # Fail safe