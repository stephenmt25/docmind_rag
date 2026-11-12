import os
import sys
import time
from dotenv import load_dotenv
import psycopg
from google import genai
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

load_dotenv()

# Configure Gemini with the new package
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Connect to Postgres (pgvector)
conn = psycopg.connect(os.getenv("DATABASE_URL"))
cursor = conn.cursor()


def extract_text(filepath: str) -> str:
    """Extract text from a PDF or .txt file."""
    if filepath.endswith(".pdf"):
        reader = PdfReader(filepath)
        return "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    elif filepath.endswith(".txt"):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError("Only .pdf and .txt files are supported.")


def split_text(text: str, chunk_size: int = 512, chunk_overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " "]
    )
    return splitter.split_text(text)


def embed_text(text: str) -> list[float]:
    """Generate an embedding for a piece of text using Gemini."""
    result = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values


def ingest_file(filepath: str, chunk_size: int = 512):
    filename = os.path.basename(filepath)
    print(f"Extracting text from {filename}...")
    text = extract_text(filepath)

    print(f"Splitting into chunks (size={chunk_size})...")
    chunks = split_text(text, chunk_size=chunk_size)
    print(f"  → {len(chunks)} chunks created")

    print("Embedding and storing chunks...")
    for i, chunk in enumerate(chunks):
        embedding = embed_text(chunk)
        cursor.execute(
            "INSERT INTO documents (filename, chunk_index, content, embedding) VALUES (%s, %s, %s, %s)",
            (filename, i, chunk, embedding)
        )
        if (i + 1) % 10 == 0:
            print(f"  → {i + 1}/{len(chunks)} chunks stored")
        
        # Rate limiting: sleep after every 50 requests to stay under 100/min
        if (i + 1) % 50 == 0:
            print("  → Pausing 35 seconds to respect rate limits...")
            time.sleep(35)

    conn.commit()
    print(f"Done. {len(chunks)} chunks ingested from {filename}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <path_to_file> [chunk_size]")
        sys.exit(1)

    filepath = sys.argv[1]
    chunk_size = int(sys.argv[2]) if len(sys.argv) > 2 else 512
    ingest_file(filepath, chunk_size=chunk_size)

cursor.close()
conn.close()