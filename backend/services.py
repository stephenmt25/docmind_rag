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


def generate_answer(question: str, chunks: list[dict]) -> str:
    """
    Generate an answer using retrieved chunks as context.
    Returns the answer text.
    """
    # Build context from chunks
    context = "\n\n---\n\n".join(
        f"Source: {c['filename']}, chunk {c['chunk_index']}\n{c['content']}"
        for c in chunks
    )
    
    prompt = f"""You are a helpful assistant. Answer the question below using ONLY the context provided.
If the context does not contain enough information to answer, say "I don't have enough information to answer that."
Do not make anything up.

Context:
{context}

Question: {question}

Answer:"""
    
    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
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