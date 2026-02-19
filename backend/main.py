"""
FastAPI application with REST endpoints.
Handles HTTP concerns, delegates business logic to services.py.
"""
import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from models import ChatRequest, ChatResponse, DocumentInfo, UploadResponse
from database import get_document_list, delete_document
from services import ingest_document, answer_question
from graph import rag_app

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
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "DocMind API is running"}


@app.post("/api/documents/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and ingest a document (PDF or txt).
    
    Steps:
    1. Save uploaded file to temp location
    2. Extract text and chunk it
    3. Embed chunks and store in database
    4. Clean up temp file
    
    Returns: filename, chunk_count, success message
    """
    # Validate file type
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Only .pdf and .txt files are supported")
    
    # Save uploaded file temporarily
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Ingest the document
        chunk_count = ingest_document(temp_path, file.filename)
        
        return UploadResponse(
            filename=file.filename,
            chunk_count=chunk_count,
            message=f"Successfully ingested {chunk_count} chunks from {file.filename}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        # Convert Pydantic Message objects to dicts for LangGraph
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.chat_history]

        # Prepare the state for LangGraph
        initial_state = {
            "question": request.question, 
            "chat_history": history_dicts, # <-- Pass it here
            "chunks": [], 
            "trace": []
        }   
        
        # Execute the graph
        result = rag_app.invoke(initial_state)
        
        # Note: We return result['trace'] to the frontend as well
        return ChatResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["chunks"],
            trace=result.get("trace", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Execution Error: {str(e)}")


@app.get("/api/documents", response_model=list[DocumentInfo])
async def list_documents():
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
async def remove_document(filename: str):
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