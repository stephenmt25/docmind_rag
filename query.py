import os
from dotenv import load_dotenv
import psycopg
from google import genai

load_dotenv()

# Configure Gemini with the new package
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Connect to Postgres (pgvector)
conn = psycopg.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()


def embed_query(question: str) -> list[float]:
    """Embed the user's question."""
    result = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=question
    )
    return result.embeddings[0].values


def retrieve_chunks(question_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Find the top_k most similar chunks using cosine similarity."""
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
        {"filename": r[0], "chunk_index": r[1], "content": r[2], "similarity": r[3]}
        for r in rows
    ]


def answer_question(question: str, top_k: int = 5) -> str:
    print(f"\nQuestion: {question}")
    print("Retrieving relevant chunks...")

    question_embedding = embed_query(question)
    chunks = retrieve_chunks(question_embedding, top_k=top_k)

    # Show what was retrieved
    print(f"\nTop {top_k} chunks retrieved:")
    for i, chunk in enumerate(chunks):
        print(f"  [{i+1}] {chunk['filename']} (chunk {chunk['chunk_index']}) — similarity: {chunk['similarity']:.3f}")
        print(f"      \"{chunk['content'][:100]}...\"")

    # Build the prompt
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

    print("\nGenerating answer...")
    response = client.models.generate_content(
        model="models/gemini-3-flash-preview",
        contents=prompt
    )
    return response.text


if __name__ == "__main__":
    while True:
        question = input("\nAsk a question (or type 'quit' to exit): ").strip()
        if question.lower() == "quit":
            break
        if question:
            answer = answer_question(question)
            print(f"\nAnswer:\n{answer}")

cursor.close()
conn.close()