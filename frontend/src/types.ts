/**
 * TypeScript types for the application.
 * Matches the Pydantic models from the backend.
 */

export interface SourceChunk {
  filename: string;
  chunk_index: number;
  content: string;
  similarity: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceChunk[];
  trace?: string[];
}

export interface DocumentInfo {
  filename: string;
  chunk_count: number;
}

export interface ChatRequest {
  question: string;
  chat_history: { role: string; content: string }[];
}

export interface ChatResponse {
  question: string;
  answer: string;
  sources: SourceChunk[];
  trace?: string[];
}

export interface UploadResponse {
  filename: string;
  chunk_count: number;
  message: string;
}