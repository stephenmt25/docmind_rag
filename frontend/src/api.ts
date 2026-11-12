/**
 * API client functions.
 * All HTTP requests to the backend go through here.
 */
import axios from 'axios';
import type {
  ChatRequest,
  ChatResponse,
  DocumentInfo,
  HistoryMessage,
  UploadResponse,
} from './types';

// In development the backend runs on :8000 and Vite serves the UI on :5173.
// Set VITE_API_URL to point the UI at a different backend.
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: API_BASE_URL });

/** Upload a document (PDF or TXT) for ingestion. */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post<UploadResponse>('/api/documents/upload', formData);
  return response.data;
}

/** Ask a question and get an answer with its sources and pipeline trace. */
export async function askQuestion(
  question: string,
  chatHistory: HistoryMessage[] = [],
): Promise<ChatResponse> {
  const payload: ChatRequest = { question, chat_history: chatHistory };
  const response = await api.post<ChatResponse>('/api/chat', payload);
  return response.data;
}

/** List all ingested documents. */
export async function getDocuments(): Promise<DocumentInfo[]> {
  const response = await api.get<DocumentInfo[]>('/api/documents');
  return response.data;
}

/** Delete a document and all of its chunks. */
export async function deleteDocument(filename: string): Promise<void> {
  await api.delete(`/api/documents/${encodeURIComponent(filename)}`);
}

/** Turn an unknown thrown value into a message that is safe to show in the UI. */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (!error.response) return 'Cannot reach the DocMind API. Is the backend running?';
    return error.message;
  }
  return error instanceof Error ? error.message : 'Something went wrong.';
}
