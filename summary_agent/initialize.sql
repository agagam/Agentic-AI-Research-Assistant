CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE pdf_chunks (
            id SERIAL PRIMARY KEY,
            publication_id INTEGER,
            source_pdf TEXT NOT NULL,
            page_number INTEGER,
            chunk_text TEXT NOT NULL,
            embedding vector({EMBEDDING_DIM}),
            created_at TIMESTAMPTZ DEFAULT now()
        );

-- Approximate nearest-neighbor index (cosine distance) for fast similarity search
-- lists - number of clusters
CREATE INDEX IF NOT EXISTS pdf_chunks_embedding_idx
ON pdf_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

ANALYZE pdf_chunks;