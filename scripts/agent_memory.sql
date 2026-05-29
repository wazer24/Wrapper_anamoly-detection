CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS agent_memory;

CREATE TABLE IF NOT EXISTS agent_memory.optimization_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(64) NOT NULL,
    query_text TEXT NOT NULL,
    query_embedding vector(768) NOT NULL, -- Gemini Text Embedding model
    diagnosis_json JSONB NOT NULL,
    proposed_fix TEXT,
    risk_level INT,
    baseline_cost FLOAT,
    validated_cost FLOAT,
    human_feedback VARCHAR(32), -- 'APPROVED', 'REJECTED'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Note: Ensure vector_cosine_ops is compatible with your PostgreSQL version and index extension
CREATE INDEX IF NOT EXISTS optimization_history_embedding_idx ON agent_memory.optimization_history 
USING hnsw (query_embedding vector_cosine_ops);
