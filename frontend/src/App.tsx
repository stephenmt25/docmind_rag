/**
 * Main App component.
 * Manages state and coordinates DocumentPanel and ChatPanel.
 */
import React, { useState, useEffect } from 'react';
import './App.css';
import type { ChatMessage, DocumentInfo, SourceChunk } from './types';
import { uploadDocument, askQuestion, getDocuments, deleteDocument } from './api';

function App() {
  // State management
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // Load documents on mount
  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  }

  async function handleFileUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const result = await uploadDocument(file);
      alert(`Success! ${result.message}`);
      await loadDocuments(); // Refresh document list
    } catch (error: any) {
      alert(`Upload failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setIsUploading(false);
      // Reset file input
      event.target.value = '';
    }
  }

  async function handleDeleteDocument(filename: string) {
    if (!window.confirm(`Delete ${filename}?`)) return;

    try {
      await deleteDocument(filename);
      await loadDocuments();
      alert(`Deleted ${filename}`);
    } catch (error: any) {
      alert(`Delete failed: ${error.response?.data?.detail || error.message}`);
    }
  }

  async function handleSendMessage() {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: inputValue,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await askQuestion(inputValue);

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message}`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyPress(event: React.KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSendMessage();
    }
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>DocMind</h1>
        <p>Chat with your documents using AI</p>
      </header>

      <div className="container">
        {/* Document Panel */}
        <div className="document-panel">
          <h2>Documents</h2>

          <div className="upload-section">
            <label htmlFor="file-upload" className="upload-button">
              {isUploading ? 'Uploading...' : 'Upload Document'}
            </label>
            <input
              id="file-upload"
              type="file"
              accept=".pdf,.txt"
              onChange={handleFileUpload}
              disabled={isUploading}
              style={{ display: 'none' }}
            />
          </div>

          <div className="document-list">
            {documents.length === 0 ? (
              <p className="empty-state">No documents uploaded yet</p>
            ) : (
              documents.map((doc) => (
                <div key={doc.filename} className="document-item">
                  <div className="document-info">
                    <strong>{doc.filename}</strong>
                    <span className="chunk-count">{doc.chunk_count} chunks</span>
                  </div>
                  <button
                    onClick={() => handleDeleteDocument(doc.filename)}
                    className="delete-button"
                  >
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Chat Panel */}
        <div className="chat-panel">
          <div className="messages">
            {messages.length === 0 ? (
              <div className="empty-state">
                <p>Upload a document and start asking questions!</p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                  <div className="message-content">{msg.content}</div>

                  {msg.sources && msg.sources.length > 0 && (
                    <details className="sources">
                      <summary>Sources ({msg.sources.length})</summary>
                      <div className="source-list">
                        {msg.sources.map((source, i) => (
                          <div key={i} className="source-item">
                            <strong>
                              {source.filename} (chunk {source.chunk_index})
                            </strong>
                            <span className="similarity">
                              similarity: {source.similarity.toFixed(3)}
                            </span>
                            <p className="source-content">
                              {source.content.substring(0, 150)}...
                            </p>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              ))
            )}

            {isLoading && (
              <div className="message assistant">
                <div className="message-content">Thinking...</div>
              </div>
            )}
          </div>

          <div className="input-area">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about your documents..."
              rows={3}
              disabled={isLoading}
            />
            <button onClick={handleSendMessage} disabled={isLoading || !inputValue.trim()}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;