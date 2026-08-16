CREATE TABLE websearch_articles (
    id                  SERIAL PRIMARY KEY,
    title               TEXT NOT NULL,
    link                TEXT,
    abstract            TEXT,                    -- source text the embedding is computed from
    abstract_vector     vector(768),              -- pgvector column
    source              TEXT DEFAULT 'weekly_search',  
    status              TEXT DEFAULT 'confirmed',      -- 'confirmed' | 'needs_review' | 'rejected'
    relevance_reasoning TEXT                       -- LLM classifier output
);
