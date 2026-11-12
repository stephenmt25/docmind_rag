/**
 * TypeScript types for the application.
 * Mirrors the Pydantic models in backend/models.py.
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
  /** Ordered list of pipeline steps the backend graph executed for this answer. */
  trace?: string[];
  /** True when the message is a client-side error notice rather than a model answer. */
  isError?: boolean;
}

export interface HistoryMessage {
  role: string;
  content: string;
}

export interface DocumentInfo {
  filename: string;
  chunk_count: number;
}

export interface ChatRequest {
  question: string;
  chat_history: HistoryMessage[];
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
