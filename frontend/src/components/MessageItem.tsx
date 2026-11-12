/**
 * A single chat message. Assistant messages also render the pipeline trace
 * (which graph nodes ran) and the source chunks the answer was grounded in.
 */
import type { ReactNode } from 'react';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage, SourceChunk } from '../types';
import {
  ChevronIcon,
  DatabaseIcon,
  FileIcon,
  GlobeIcon,
  RewriteIcon,
  ShieldIcon,
  SparkIcon,
} from './icons';

type StepKind = 'rewrite' | 'retrieve' | 'web' | 'generate' | 'blocked';

/** Map a trace label from backend/graph.py onto a visual style. */
function classifyStep(step: string): { kind: StepKind; icon: ReactNode } {
  if (step.includes('Hallucination')) return { kind: 'blocked', icon: <ShieldIcon size={13} /> };
  if (step.includes('Web')) return { kind: 'web', icon: <GlobeIcon size={13} /> };
  if (step.includes('Retrieval')) return { kind: 'retrieve', icon: <DatabaseIcon size={13} /> };
  if (step.includes('Generation')) return { kind: 'generate', icon: <SparkIcon size={13} /> };
  return { kind: 'rewrite', icon: <RewriteIcon size={13} /> };
}

function Trace({ steps }: { steps: string[] }) {
  return (
    <ol className="trace" aria-label="Pipeline steps">
      {steps.map((step, i) => {
        const { kind, icon } = classifyStep(step);
        return (
          <li key={i} className={`trace-step trace-${kind}`}>
            {i > 0 && <ChevronIcon size={12} className="trace-arrow" />}
            <span className="trace-pill">
              {icon}
              {step}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function Source({ source }: { source: SourceChunk }) {
  // Web results carry a placeholder score from the backend, so no similarity is shown for them.
  const isWeb = source.filename.startsWith('Web Search');
  const percent = Math.max(0, Math.min(1, source.similarity)) * 100;

  return (
    <li className={`source${isWeb ? ' is-web' : ''}`}>
      <div className="source-head">
        <span className="source-name">
          {isWeb ? <GlobeIcon size={13} /> : <FileIcon size={13} />}
          {source.filename}
        </span>
        <span className="source-chunk">
          {isWeb ? `result ${source.chunk_index + 1}` : `chunk ${source.chunk_index}`}
        </span>
        {!isWeb && (
          <span className="source-score" title="Cosine similarity to the query">
            <span className="score-bar">
              <span style={{ width: `${percent}%` }} />
            </span>
            {source.similarity.toFixed(3)}
          </span>
        )}
      </div>
      <p className="source-content">{source.content}</p>
    </li>
  );
}

export default function MessageItem({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="message user">
        <div className="bubble">{message.content}</div>
      </div>
    );
  }

  const sources = message.sources ?? [];

  return (
    <div className={`message assistant${message.isError ? ' is-error' : ''}`}>
      {message.trace && message.trace.length > 0 && <Trace steps={message.trace} />}

      <div className="answer">
        <ReactMarkdown>{message.content}</ReactMarkdown>
      </div>

      {sources.length > 0 && (
        <details className="sources">
          <summary>
            <ChevronIcon size={13} className="sources-caret" />
            {sources.length} {sources.length === 1 ? 'source' : 'sources'}
          </summary>
          <ul className="source-list">
            {sources.map((source, i) => (
              <Source key={i} source={source} />
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
