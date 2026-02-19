/**
 * API client functions.
 * All HTTP requests to the backend go through here.
 */
import axios from 'axios';
import type { ChatRequest, ChatResponse, DocumentInfo, UploadResponse } from './types';

// Base URL for API requests
// In development: backend runs on :8000, frontend on :3000
// In production: both served from same origin
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Upload a document (PDF or txt)
 */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post<UploadResponse>(
    `${API_BASE_URL}/api/documents/upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );

  return response.data;
}

/**
 * Ask a question and get an answer with sources
 */
export async function askQuestion(question: string, chatHistory: {role: string, content: string}[] = []): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/api/chat', {
    question,
    chat_history: chatHistory,
  } as ChatRequest);

  return response.data;
}
/**
 * Get list of all uploaded documents
 */
export async function getDocuments(): Promise<DocumentInfo[]> {
  const response = await api.get<DocumentInfo[]>('/api/documents');
  return response.data;
}

/**
 * Delete a document
 */
export async function deleteDocument(filename: string): Promise<void> {
  await api.delete(`/api/documents/${filename}`);
}