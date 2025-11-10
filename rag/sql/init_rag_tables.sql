-- =============================================================================
-- RAG Vector Storage Setup for Tarot Agent
-- =============================================================================
-- 为RAG（检索增强生成）系统创建向量存储表
-- 
-- 使用说明：
-- 1. 登录 Supabase Dashboard
-- 2. 进入 SQL Editor
-- 3. 新建查询（New Query）
-- 4. 复制并粘贴此脚本
-- 5. 点击 Run 执行
-- =============================================================================

-- =============================================================================
-- STEP 1: Enable pgvector extension for vector similarity search
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- STEP 2: Create the RAG chunks table for storing text and embeddings
-- =============================================================================

CREATE TABLE IF NOT EXISTS rag_chunks (
    id BIGSERIAL PRIMARY KEY,
    chunk_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,  -- URL or identifier of the source document
    text TEXT NOT NULL,    -- The actual text content
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small dimension (1536)
    metadata JSONB DEFAULT '{}',  -- Additional metadata (e.g., card_name, section)
    created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- STEP 3: Create performance indexes for fast vector search
-- =============================================================================

-- Vector similarity index using IVFFlat algorithm
-- Note: For better performance with large datasets, consider HNSW index
CREATE INDEX IF NOT EXISTS rag_chunks_vec_idx
    ON rag_chunks USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Regular B-tree indexes for filtering and sorting
CREATE INDEX IF NOT EXISTS rag_chunks_src_idx ON rag_chunks (source);
CREATE INDEX IF NOT EXISTS rag_chunks_chunk_id_idx ON rag_chunks (chunk_id);
CREATE INDEX IF NOT EXISTS rag_chunks_created_at_idx ON rag_chunks (created_at DESC);
CREATE INDEX IF NOT EXISTS rag_chunks_metadata_idx ON rag_chunks USING gin (metadata);

-- =============================================================================
-- STEP 4: Create vector similarity search function
-- =============================================================================

CREATE OR REPLACE FUNCTION match_chunks (
  query_embedding vector(1536),
  match_count int DEFAULT 6,
  min_similarity float DEFAULT 0.0,
  filter_source text DEFAULT NULL
)
RETURNS TABLE (
  chunk_id text,
  source text,
  text text,
  similarity float,
  metadata jsonb,
  created_at timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    rag_chunks.chunk_id,
    rag_chunks.source,
    rag_chunks.text,
    1 - (rag_chunks.embedding <=> query_embedding) as similarity,
    rag_chunks.metadata,
    rag_chunks.created_at
  FROM rag_chunks
  WHERE 
    (filter_source IS NULL OR rag_chunks.source = filter_source)
    AND 1 - (rag_chunks.embedding <=> query_embedding) >= min_similarity
  ORDER BY rag_chunks.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- =============================================================================
-- STEP 5: Create helper function to get database statistics
-- =============================================================================

CREATE OR REPLACE FUNCTION get_chunk_stats()
RETURNS TABLE (
  total_chunks bigint,
  unique_sources bigint,
  latest_chunk timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    COUNT(*) as total_chunks,
    COUNT(DISTINCT source) as unique_sources,
    MAX(created_at) as latest_chunk
  FROM rag_chunks;
END;
$$;

-- =============================================================================
-- STEP 6: Create Row Level Security (RLS) policies
-- =============================================================================

-- Enable RLS on the table
ALTER TABLE rag_chunks ENABLE ROW LEVEL SECURITY;

-- Allow all operations for service role (your backend)
CREATE POLICY "Allow service role full access" ON rag_chunks
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Allow read access for authenticated users (future frontend)
CREATE POLICY "Allow authenticated read access" ON rag_chunks
  FOR SELECT USING (auth.role() = 'authenticated');

-- Allow anonymous read access for development (remove in production if needed)
CREATE POLICY "Allow anonymous read access" ON rag_chunks
  FOR SELECT USING (true);

-- =============================================================================
-- STEP 7: Grant permissions
-- =============================================================================

GRANT EXECUTE ON FUNCTION match_chunks(vector, int, float, text) TO authenticated;
GRANT EXECUTE ON FUNCTION match_chunks(vector, int, float, text) TO anon;
GRANT EXECUTE ON FUNCTION get_chunk_stats() TO authenticated;
GRANT EXECUTE ON FUNCTION get_chunk_stats() TO anon;

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT '✅ RAG数据库初始化完成！' as status,
       '已创建表: rag_chunks' as tables,
       '已启用pgvector扩展' as extension,
       '已创建向量索引和搜索函数' as functions;

