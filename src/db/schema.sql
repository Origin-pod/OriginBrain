-- Schema for OriginSteward

-- Drops: Raw input from Extension/App
CREATE TABLE IF NOT EXISTS drops (
    id UUID PRIMARY KEY,
    type TEXT NOT NULL, -- 'url', 'text', 'tweet', 'image'
    payload TEXT NOT NULL,
    note TEXT,
    status TEXT DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_msg TEXT
);

-- Artifacts: Processed content (Markdown/JSON)
CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY,
    drop_id UUID REFERENCES drops(id),
    title TEXT,
    content TEXT, -- Markdown content
    metadata JSONB, -- Source URL, Author, Tags, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings: Vector data
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY,
    artifact_id UUID REFERENCES artifacts(id),
    vector JSONB, -- Storing as JSON array for simplicity (or float[] if using pgvector later)
    model TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_drops_status ON drops(status);
CREATE INDEX IF NOT EXISTS idx_artifacts_drop_id ON artifacts(drop_id);
