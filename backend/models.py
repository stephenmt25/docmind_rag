"""
Pydantic models for request/response validation.
These provide type safety and automatic validation at the API boundary.
"""
from pydantic import BaseModel
from typing import List, Optional


class ChatRequest(BaseModel):
    """Request body for /api/chat endpoint"""
    question: str


class SourceChunk(BaseModel):
    """A source chunk retrieved from the database"""
    filename: str
    chunk_index: int
    content: str
    similarity: float


class ChatResponse(BaseModel):
    """Response body for /api/chat endpoint"""
    question: str
    answer: str
    sources: List[SourceChunk]


class DocumentInfo(BaseModel):
    """Information about an uploaded document"""
    filename: str
    chunk_count: int


class UploadResponse(BaseModel):
    """Response after uploading a document"""
    filename: str
    chunk_count: int
    message: str


class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str