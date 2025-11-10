-- =============================================================================
-- RAG向量搜索性能优化 - HNSW索引方案
-- =============================================================================
-- 使用HNSW索引替代IVFFlat索引，进一步提升向量搜索性能
-- 
-- HNSW优势：
-- - 通常比IVFFlat快10-100倍
-- - 对于716个chunks，性能提升明显
-- - 向量搜索时间从459ms降至<100ms
-- 
-- 注意：
-- - HNSW索引占用更多空间（约2-3倍）
-- - 但查询性能提升显著
-- =============================================================================

-- 检查当前索引和数据量
SELECT 
  indexname,
  indexdef,
  pg_size_pretty(pg_relation_size(indexrelid::regclass)) as index_size
FROM pg_indexes
WHERE tablename = 'rag_chunks';

SELECT 
  COUNT(*) as total_chunks,
  COUNT(DISTINCT source) as unique_sources
FROM rag_chunks;

-- =============================================================================
-- 创建HNSW索引
-- =============================================================================

-- 临时增加maintenance_work_mem以创建索引
SET maintenance_work_mem = '64MB';

-- 删除旧的IVFFlat索引
DROP INDEX IF EXISTS rag_chunks_vec_idx;

-- 创建HNSW索引
-- m = 16: 每个节点的连接数（推荐值）
-- ef_construction = 64: 构建时的搜索范围（推荐值）
CREATE INDEX rag_chunks_vec_hnsw_idx
    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- =============================================================================
-- 优化match_chunks函数，添加HNSW ef_search设置
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
  -- 设置HNSW ef_search参数（如果使用HNSW索引）
  -- ef_search控制搜索时的候选数量，值越大越准确但越慢
  -- 对于top_k=6，ef_search=20是一个好的平衡点
  SET LOCAL hnsw.ef_search = 20;
  
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

-- 检查索引大小
SELECT 
  indexname,
  pg_size_pretty(pg_relation_size(indexrelid::regclass)) as index_size
FROM pg_indexes
WHERE tablename = 'rag_chunks' AND indexname LIKE '%vec%';

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT '✅ RAG向量搜索性能优化完成（HNSW索引）！' as status,
       '已创建HNSW索引（m=16, ef_construction=64）' as optimization,
       '已更新match_chunks函数（ef_search=20）' as function_update,
       '预期性能提升：向量搜索从459ms降至<100ms' as expected_improvement;





