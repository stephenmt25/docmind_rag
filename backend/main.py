"""
FastAPI application with REST endpoints.
Handles HTTP concerns, delegates business logic to services.py.
"""
import os
import shutil
import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from models import ChatRequest, ChatResponse, DocumentInfo, UploadResponse
from database import get_document_list, delete_document
from services import ingest_document
from graph import rag_app

SUPPORTED_EXTENSIONS = {".pdf", ".txt"}

app = FastAPI(title="DocMind API")

# CORS middleware - allows frontend to call backend from different port during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "DocMind API is running"}


@app.post("/api/documents/upload", response_model=UploadResponse)
def upload_document(file: UploadFile = File(...)):
    """
    Upload and ingest a document (PDF or TXT).

    Steps:
    1. Save the upload to a temporary file
    2. Extract text and chunk it
    3. Embed chunks and store them in the database
    4. Clean up the temporary file

    Declared as a sync endpoint so FastAPI runs it in a worker thread:
    ingestion is blocking (embedding calls plus rate-limit pauses) and
    must not stall the event loop.

    Returns: filename, chunk_count, success message
    """
    # Keep only the base name so a crafted filename cannot point outside the temp dir.
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are supported")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
            shutil.copyfileobj(file.file, tmp)
            temp_path = tmp.name

        chunk_count = ingest_document(temp_path, filename)

        return UploadResponse(
            filename=filename,
            chunk_count=chunk_count,
            message=f"Successfully ingested {chunk_count} chunks from {filename}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Answer a question by running the LangGraph RAG pipeline.

    Returns the answer, the source chunks it was generated from, and a
    trace of the graph nodes that executed (shown in the UI).
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        initial_state = {
            "question": request.question,
            "chat_history": [{"role": msg.role, "content": msg.content} for msg in request.chat_history],
            "chunks": [],
            "trace": [],
        }

        result = rag_app.invoke(initial_state)

        return ChatResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["chunks"],
            trace=result.get("trace", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Execution Error: {str(e)}")


@app.get("/api/documents", response_model=list[DocumentInfo])
def list_documents():
    """
    Get list of all uploaded documents with chunk counts.
    
    Returns: list of {filename, chunk_count}
    """
    try:
        documents = get_document_list()
        return documents
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")


@app.delete("/api/documents/{filename}")
def remove_document(filename: str):
    """
    Delete a document and all its chunks.
    
    Returns: success message with deletion count
    """
    try:
        deleted_count = delete_document(filename)
        
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")
        
        return {"message": f"Deleted {deleted_count} chunks from {filename}"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


# Serve static files (for production - frontend build files)
# In development, frontend runs separately on its own port
if os.path.exists("./static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)