-- =============================================================================
-- RAG向量搜索性能优化
-- =============================================================================
-- 优化IVFFlat索引参数，提升向量搜索性能
-- 
-- 当前问题：
-- - IVFFlat索引的lists参数设置为100，对于716个chunks来说太大
-- - 向量搜索耗时763ms，应该<100ms
-- 
-- 优化方案：
-- 1. 调整IVFFlat索引的lists参数（rows/1000，对于716个chunks，建议lists=1-10）
-- 2. 考虑使用HNSW索引（更快，但占用更多空间）
-- 3. 设置ivfflat.probes参数优化查询性能
-- =============================================================================

-- 检查当前索引
SELECT 
  indexname,
  indexdef,
  pg_size_pretty(pg_relation_size(indexrelid::regclass)) as index_size
FROM pg_indexes
WHERE tablename = 'rag_chunks';

-- 检查当前数据量
SELECT 
  COUNT(*) as total_chunks,
  COUNT(DISTINCT source) as unique_sources
FROM rag_chunks;

-- =============================================================================
-- 方案1: 优化IVFFlat索引（推荐，适合当前数据量）
-- =============================================================================

-- 删除旧索引
DROP INDEX IF EXISTS rag_chunks_vec_idx;

-- 创建优化的IVFFlat索引
-- lists参数：对于716个chunks，设置为rows/1000 = 1（最小为1）
-- 但为了更好的性能，可以设置为10左右
CREATE INDEX rag_chunks_vec_idx
    ON rag_chunks USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 10);

-- 设置查询时的probes参数（默认是lists的值）
-- 这个参数控制搜索时检查的列表数量，值越大越准确但越慢
-- 对于lists=10，probes=5是一个好的平衡点
-- 注意：这个设置是会话级别的，需要在查询前设置
-- 我们可以在match_chunks函数中设置，或者使用SET命令

-- =============================================================================
-- 方案2: 使用HNSW索引（更快，但占用更多空间）
-- =============================================================================
-- HNSW索引通常比IVFFlat快10-100倍，但占用更多空间
-- 对于716个chunks，HNSW索引大小约增加2-3倍

-- 删除IVFFlat索引（如果使用HNSW）
-- DROP INDEX IF EXISTS rag_chunks_vec_idx;

-- 创建HNSW索引
-- CREATE INDEX rag_chunks_vec_hnsw_idx
--     ON rag_chunks USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

-- =============================================================================
-- 优化match_chunks函数，添加probes设置
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
  -- 设置IVFFlat probes参数（如果使用IVFFlat索引）
  -- 对于lists=10，probes=5是一个好的平衡点
  -- 注意：这个设置只在当前函数执行期间有效
  SET LOCAL ivfflat.probes = 5;
  
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
-- 验证优化效果
-- =============================================================================

-- 测试查询性能（使用EXPLAIN ANALYZE）
-- 注意：需要先有一个查询向量，这里只是示例
-- EXPLAIN ANALYZE
-- SELECT
--   chunk_id,
--   source,
--   text,
--   1 - (embedding <=> '[你的查询向量]'::vector) as similarity
-- FROM rag_chunks
-- ORDER BY embedding <=> '[你的查询向量]'::vector
-- LIMIT 5;

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT '✅ RAG向量搜索性能优化完成！' as status,
       '已优化IVFFlat索引（lists=10）' as optimization,
       '已更新match_chunks函数（probes=5）' as function_update,
       '建议：如果数据量继续增长，考虑使用HNSW索引' as recommendation;





