-- DocMind database schema.
-- Run once against your Postgres database (docker-compose applies it automatically).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id          BIGSERIAL PRIMARY KEY,
    filename    TEXT        NOT NULL,
    chunk_index INTEGER     NOT NULL,
    content     TEXT        NOT NULL,
    -- gemini-embedding-001 returns 3072-dimensional vectors by default.
    embedding   VECTOR(3072) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Used by the document list and delete endpoints.
CREATE INDEX IF NOT EXISTS documents_filename_idx ON documents (filename);

-- Similarity search runs as an exact scan, which is fine at this scale.
-- pgvector's HNSW/IVFFlat indexes support at most 2000 dimensions for the
-- `vector` type, so an approximate index would mean reducing the embedding
-- size (output_dimensionality) or indexing a halfvec cast.
