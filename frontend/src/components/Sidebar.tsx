/**
 * Sidebar: branding, document upload (click or drag-and-drop) and the document list.
 */
import { useState } from 'react';
import type { ChangeEvent, DragEvent } from 'react';
import type { DocumentInfo } from '../types';
import { FileIcon, LogoMark, TrashIcon, UploadIcon } from './icons';

interface SidebarProps {
  documents: DocumentInfo[];
  isUploading: boolean;
  onUpload: (file: File) => void;
  onDelete: (filename: string) => void;
}

export default function Sidebar({ documents, isUploading, onUpload, onDelete }: SidebarProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  const totalChunks = documents.reduce((sum, doc) => sum + doc.chunk_count, 0);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) onUpload(file);
    event.target.value = '';
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file && !isUploading) onUpload(file);
  }

  return (
    <aside className="sidebar">
      <div className="brand">
        <LogoMark />
        <div>
          <h1>DocMind</h1>
          <p>Chat with your documents</p>
        </div>
      </div>

      <label
        htmlFor="file-upload"
        className={`dropzone${isDragging ? ' is-dragging' : ''}${isUploading ? ' is-busy' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        {isUploading ? <span className="spinner" /> : <UploadIcon size={18} />}
        <span className="dropzone-title">
          {isUploading ? 'Chunking and embedding…' : 'Upload a document'}
        </span>
        <span className="dropzone-hint">
          {isUploading ? 'Large files can take a minute' : 'PDF or TXT · click or drop'}
        </span>
        <input
          id="file-upload"
          type="file"
          accept=".pdf,.txt"
          onChange={handleFileChange}
          disabled={isUploading}
          hidden
        />
      </label>

      <div className="section-label">
        <span>Knowledge base</span>
        <span className="count">{documents.length}</span>
      </div>

      <ul className="document-list">
        {documents.length === 0 && <li className="list-empty">No documents indexed yet.</li>}

        {documents.map((doc) =>
          pendingDelete === doc.filename ? (
            <li key={doc.filename} className="document-item is-confirming">
              <span className="confirm-text">Delete this document?</span>
              <button
                className="btn-danger"
                onClick={() => {
                  setPendingDelete(null);
                  onDelete(doc.filename);
                }}
              >
                Delete
              </button>
              <button className="btn-ghost" onClick={() => setPendingDelete(null)}>
                Cancel
              </button>
            </li>
          ) : (
            <li key={doc.filename} className="document-item">
              <span className="document-icon">
                <FileIcon />
              </span>
              <div className="document-info">
                <strong title={doc.filename}>{doc.filename}</strong>
                <span>{doc.chunk_count} chunks</span>
              </div>
              <button
                className="icon-button"
                aria-label={`Delete ${doc.filename}`}
                onClick={() => setPendingDelete(doc.filename)}
              >
                <TrashIcon size={15} />
              </button>
            </li>
          ),
        )}
      </ul>

      <footer className="sidebar-footer">
        <div className="stat">
          <strong>{totalChunks.toLocaleString()}</strong>
          <span>chunks indexed</span>
        </div>
        <div className="stack">Gemini · pgvector · LangGraph</div>
      </footer>
    </aside>
  );
}
