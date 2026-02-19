# 🧠 DocMind — Full‑Stack Retrieval‑Augmented Generation (RAG)

DocMind lets you upload documents (PDF/TXT), create searchable vector embeddings, and chat with your documents using Google Gemini (GenAI). Answers are produced by a RAG pipeline and include the source chunks used to reason the response.

## Features

- Document ingestion: extract text from PDF/TXT, chunk, embed, and store vectors.
- Conversational Q&A: ask questions; the system retrieves top chunks and generates grounded answers.
- Transparent sources: UI returns source chunks and similarity scores for each answer.
- Document management: list uploaded documents and delete documents (removes all chunks).
- Graph-based orchestration: LangGraph/DDGS-driven workflow with grounding checks and web-search fallback.

## Architecture & Tech Stack

- Backend: FastAPI (Python) exposing REST endpoints. Business logic in `backend/services.py` and graph orchestration in `backend/graph.py`.
- Models & LLMs: Google GenAI / Gemini used for embeddings and generation (`genai` client).
- Database: PostgreSQL (Supabase suggested) with vector column for embeddings; connection pooling via `psycopg_pool`.
- Frontend: React + TypeScript + Vite. Communicates with backend REST API.
- Utilities: small CLI scripts available in the project root (`ingest.py`, `query.py`, `list_models.py`).

## Repo layout (important files)

- `backend/main.py` — FastAPI app and HTTP endpoints.
- `backend/services.py` — RAG business logic (ingest, retrieve, generate, grounding checks).
- `backend/database.py` — DB connection pool and helper functions.
- `backend/models.py` — Pydantic request/response models used by the API.
- `backend/graph.py` — LangGraph workflow that composes retrieval, generation and fallback logic.
- `ingest.py` — CLI-style script to ingest a local file directly (standalone).
- `query.py` — Simple CLI conversational query runner (embeds, retrieves, generates).
- `list_models.py` — Lists available Gemini models for your API key.
- `frontend/` — React + TypeScript UI (dev server via `npm run dev`).

## Environment variables

Create a `.env` with at least these variables (used by backend and scripts):

- `GEMINI_API_KEY` — API key for Google GenAI / Gemini.
- `DATABASE_URL` — Full PostgreSQL connection string (Supabase or other).

Optional (local dev):

- `PORT` — backend port (default 8000)

## Database schema

This project expects a single table to store document chunks:

- Table: `documents`
  - `filename` (text)
  - `chunk_index` (int)
  - `content` (text)
  - `embedding` (vector/pgvector or Supabase vector type)

Adjust the column type for `embedding` to match your DB provider (e.g., `vector` for pgvector).

## API Endpoints

- `GET /` — health check
- `POST /api/documents/upload` — upload and ingest a PDF or TXT file (multipart form `file`).
  - Response: `{ filename, chunk_count, message }`
- `GET /api/documents` — list uploaded documents with `chunk_count`.
- `DELETE /api/documents/{filename}` — delete all chunks for a file.
- `POST /api/chat` — chat endpoint. Request body (JSON):

  {
    "question": "...",
    "chat_history": [{ "role": "user|assistant", "content": "..." }, ...]
  }

  Response: `{ question, answer, sources, trace }` where `sources` contains filename, chunk_index, content, similarity.

## CLI utilities

- `python ingest.py <path_to_file> [chunk_size]` — ingest a local file directly (uses Gemini embeddings + DB).
- `python query.py` — interactive CLI to ask questions using stored documents.
- `python list_models.py` — prints available Gemini models for your API key.

## Rate limiting & model choices

- Embeddings use `models/gemini-embedding-001`.
- Generation uses preview models in code (e.g. `models/gemini-3-flash-preview`); update as needed.
- The ingest pipeline pauses 35 seconds every 50 chunk embeddings to avoid hitting API rate limits — you may tune this.

## Local development & run

Backend (from `docmind` root):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Or build frontend and serve static files from `backend/static` for production.

## Example usage (curl)

Upload a document:

```bash
curl -F "file=@/path/to/doc.pdf" http://localhost:8000/api/documents/upload
```

Chat with documents:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the main idea?","chat_history":[]}'
```

List documents:

```bash
curl http://localhost:8000/api/documents
```

Delete a document:

```bash
curl -X DELETE http://localhost:8000/api/documents/yourfile.pdf
```

## Troubleshooting

- `GEMINI_API_KEY` errors: verify API key and network access.
- Database errors: confirm `DATABASE_URL` and that the `documents` table exists with correct `embedding` type.
- Rate limits: if embedding/generation fails, increase the pause in `services.py` or shard ingestion.

## Notes & next steps

- The graph in `backend/graph.py` contains routing logic, web-search fallback, and a grounding check that can be tuned.
- You can swap Gemini models or add alternative embedding providers by updating `services.py`.

---

If you want, I can also:

- Add example `.env.example` with required variables.
- Add a small `docker-compose.yml` to run Postgres + backend + frontend locally.
- Expand the frontend README with usage screenshots and API examples.
