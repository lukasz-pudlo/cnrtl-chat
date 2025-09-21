CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Entry chunks table with rich JSONB metadata
CREATE TABLE IF NOT EXISTS cnrtl_chunks (
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(50) UNIQUE NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    
    -- JSONB fields for flexible metadata storage
    metadata JSONB NOT NULL DEFAULT '{}',
    entry_info JSONB NOT NULL DEFAULT '{}',
    processing_info JSONB NOT NULL DEFAULT '{}',
    
    -- Extracted fields for performance
    entry_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Query analytics table
CREATE TABLE IF NOT EXISTS query_analytics (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    query_metadata JSONB DEFAULT '{}',
    response_metadata JSONB DEFAULT '{}',
    user_session JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for JSONB fields
CREATE INDEX IF NOT EXISTS idx_chunks_metadata 
ON cnrtl_chunks USING gin(metadata);

CREATE INDEX IF NOT EXISTS idx_chunks_entry_info 
ON cnrtl_chunks USING gin(entry_info);

CREATE INDEX IF NOT EXISTS idx_analytics_query_metadata 
ON query_analytics USING gin(query_metadata);

-- Create vector similarity index
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
ON cnrtl_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Create fallback IVFFlat index
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_ivfflat 
ON cnrtl_chunks USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_chunks_entry_type 
ON cnrtl_chunks (entry_type);

CREATE INDEX IF NOT EXISTS idx_analytics_created_at 
ON query_analytics (created_at);
