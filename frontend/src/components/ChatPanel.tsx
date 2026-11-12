/**
 * Chat panel: header, message list (with empty and loading states) and the composer.
 */
import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { ChatMessage } from '../types';
import MessageItem from './MessageItem';
import { ArrowUpIcon, PlusIcon, SparkIcon } from './icons';

const SUGGESTIONS = [
  'Summarize the key points',
  'What are the main conclusions?',
  'Which terms are defined, and how?',
];

interface ChatPanelProps {
  messages: ChatMessage[];
  isLoading: boolean;
  hasDocuments: boolean;
  onSend: (question: string) => void;
  onNewChat: () => void;
}

export default function ChatPanel({
  messages,
  isLoading,
  hasDocuments,
  onSend,
  onNewChat,
}: ChatPanelProps) {
  const [input, setInput] = useState('');
  const endRef = useRef<HTMLDivElement>(null);

  // Keep the newest message in view.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' });
  }, [messages, isLoading]);

  function submit() {
    const question = input.trim();
    if (!question || isLoading) return;
    onSend(question);
    setInput('');
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <main className="chat">
      <header className="chat-header">
        <div>
          <h2>Ask your documents</h2>
          <p>Every answer shows the steps the pipeline took and the passages it used.</p>
        </div>
        <button className="btn-ghost" onClick={onNewChat} disabled={messages.length === 0}>
          <PlusIcon size={14} />
          New chat
        </button>
      </header>

      <div className="messages">
        <div className="messages-inner">
          {messages.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">
                <SparkIcon size={22} />
              </span>
              <h3>{hasDocuments ? 'What would you like to know?' : 'Start by adding a document'}</h3>
              <p>
                {hasDocuments
                  ? 'Questions are answered from your indexed documents. If nothing relevant is found, DocMind falls back to a web search, and every answer is checked against its sources before you see it.'
                  : 'Upload a PDF or TXT file in the sidebar. It is chunked, embedded and stored in Postgres so you can ask questions about it.'}
              </p>
              {hasDocuments && (
                <div className="suggestions">
                  {SUGGESTIONS.map((text) => (
                    <button key={text} onClick={() => setInput(text)}>
                      {text}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            messages.map((message, i) => <MessageItem key={i} message={message} />)
          )}

          {isLoading && (
            <div className="message assistant">
              <div className="thinking" role="status">
                <span className="dots">
                  <i />
                  <i />
                  <i />
                </span>
                Running the pipeline…
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="composer">
        <div className="composer-box">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your documents…"
            rows={1}
            disabled={isLoading}
          />
          <button
            className="send"
            onClick={submit}
            disabled={isLoading || !input.trim()}
            aria-label="Send"
          >
            <ArrowUpIcon size={17} />
          </button>
        </div>
        <p className="composer-hint">Enter to send · Shift + Enter for a new line</p>
      </div>
    </main>
  );
}
