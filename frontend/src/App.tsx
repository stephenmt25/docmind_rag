/**
 * Root component. Owns application state and coordinates the Sidebar
 * (document management) and the ChatPanel (conversation).
 */
import { useCallback, useEffect, useState } from 'react';
import './App.css';
import type { ChatMessage, DocumentInfo } from './types';
import {
  askQuestion,
  deleteDocument,
  getDocuments,
  getErrorMessage,
  uploadDocument,
} from './api';
import Sidebar from './components/Sidebar';
import ChatPanel from './components/ChatPanel';

/** Number of previous messages sent with each question for follow-up context. */
const HISTORY_WINDOW = 4;
const TOAST_DURATION_MS = 4500;

interface Toast {
  kind: 'success' | 'error';
  text: string;
}

export default function App() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [toast, setToast] = useState<Toast | null>(null);

  const refreshDocuments = useCallback(async () => {
    try {
      setDocuments(await getDocuments());
    } catch (error) {
      setToast({ kind: 'error', text: getErrorMessage(error) });
    }
  }, []);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), TOAST_DURATION_MS);
    return () => clearTimeout(timer);
  }, [toast]);

  async function handleUpload(file: File) {
    setIsUploading(true);
    try {
      const result = await uploadDocument(file);
      setToast({ kind: 'success', text: `Indexed ${result.filename} (${result.chunk_count} chunks)` });
      await refreshDocuments();
    } catch (error) {
      setToast({ kind: 'error', text: `Upload failed: ${getErrorMessage(error)}` });
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDelete(filename: string) {
    try {
      await deleteDocument(filename);
      setToast({ kind: 'success', text: `Deleted ${filename}` });
      await refreshDocuments();
    } catch (error) {
      setToast({ kind: 'error', text: `Delete failed: ${getErrorMessage(error)}` });
    }
  }

  async function handleSend(question: string) {
    const history = messages
      .filter((m) => !m.isError)
      .slice(-HISTORY_WINDOW)
      .map(({ role, content }) => ({ role, content }));

    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setIsLoading(true);

    try {
      const response = await askQuestion(question, history);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.answer,
          sources: response.sources,
          trace: response.trace,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: getErrorMessage(error), isError: true },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="app">
      <Sidebar
        documents={documents}
        isUploading={isUploading}
        onUpload={handleUpload}
        onDelete={handleDelete}
      />
      <ChatPanel
        messages={messages}
        isLoading={isLoading}
        hasDocuments={documents.length > 0}
        onSend={handleSend}
        onNewChat={() => setMessages([])}
      />

      {toast && (
        <div className={`toast toast-${toast.kind}`} role="status">
          {toast.text}
        </div>
      )}
    </div>
  );
}
