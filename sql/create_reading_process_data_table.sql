-- =============================================================================
-- Tarot Reading System - Reading Process Data Table
-- 创建占卜过程数据表，用于记录占卜过程中的所有相关数据
-- =============================================================================
-- 
-- 使用说明：
-- 1. 登录 Supabase Dashboard
-- 2. 进入 SQL Editor
-- 3. 新建查询（New Query）
-- 4. 复制并粘贴此脚本
-- 5. 点击 Run 执行
-- =============================================================================

-- =============================================================================
-- 创建 reading_process_data 表 - 占卜过程数据记录
-- =============================================================================

CREATE TABLE IF NOT EXISTS reading_process_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reading_id UUID NOT NULL REFERENCES readings(id) ON DELETE CASCADE,
    
    -- 步骤信息
    step_name TEXT NOT NULL,  -- 步骤名称：'question_analysis', 'card_selection', 'pattern_analysis', 'rag_retrieval', 'final_interpretation'
    step_order INTEGER NOT NULL,  -- 步骤顺序（1, 2, 3...）
    
    -- 输入数据（JSONB格式，存储所有输入信息）
    input_data JSONB,  -- 包含：问题、用户信息、选中的牌等
    
    -- 输出数据（JSONB格式，存储所有输出信息）
    output_data JSONB,  -- 包含：分析结果、选中的牌、解读等
    
    -- Prompt信息
    prompt_type TEXT,  -- Prompt类型：'question_analysis', 'pattern_analysis', 'final_interpretation'
    prompt_content TEXT,  -- 完整的prompt内容
    
    -- RAG查询信息（如果是RAG相关步骤）
    rag_queries JSONB,  -- RAG查询列表，每个查询包含：query, result, citations
    
    -- 模型信息
    model_used TEXT,  -- 使用的模型名称（如：gpt-4o-mini, gpt-4o）
    temperature FLOAT,  -- 使用的温度参数
    
    -- 性能指标
    processing_time_ms INTEGER,  -- 处理时间（毫秒）
    tokens_used INTEGER,  -- 使用的token数（如果可用）
    
    -- 错误信息（如果有）
    error_message TEXT,  -- 错误消息（如果有）
    error_traceback TEXT,  -- 错误堆栈（如果有）
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_reading_process_data_reading_id ON reading_process_data(reading_id);
CREATE INDEX IF NOT EXISTS idx_reading_process_data_step_name ON reading_process_data(step_name);
CREATE INDEX IF NOT EXISTS idx_reading_process_data_step_order ON reading_process_data(reading_id, step_order);
CREATE INDEX IF NOT EXISTS idx_reading_process_data_created_at ON reading_process_data(created_at DESC);

-- GIN索引用于JSONB查询
CREATE INDEX IF NOT EXISTS idx_reading_process_data_input_data ON reading_process_data USING GIN(input_data);
CREATE INDEX IF NOT EXISTS idx_reading_process_data_output_data ON reading_process_data USING GIN(output_data);
CREATE INDEX IF NOT EXISTS idx_reading_process_data_rag_queries ON reading_process_data USING GIN(rag_queries);

-- RLS策略
ALTER TABLE reading_process_data ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own reading process data"
    ON reading_process_data FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM readings 
            WHERE readings.id = reading_process_data.reading_id 
            AND readings.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to reading_process_data"
    ON reading_process_data FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- 表注释
COMMENT ON TABLE reading_process_data IS '占卜过程数据表，记录占卜过程中所有步骤的详细数据，包括输入、输出、prompt、RAG查询等';
COMMENT ON COLUMN reading_process_data.step_name IS '步骤名称：question_analysis, card_selection, pattern_analysis, rag_retrieval, final_interpretation';
COMMENT ON COLUMN reading_process_data.input_data IS '输入数据（JSONB格式），包含步骤所需的所有输入信息';
COMMENT ON COLUMN reading_process_data.output_data IS '输出数据（JSONB格式），包含步骤产生的所有输出信息';
COMMENT ON COLUMN reading_process_data.prompt_content IS '完整的prompt内容，用于调试和可追溯性';
COMMENT ON COLUMN reading_process_data.rag_queries IS 'RAG查询列表（JSONB格式），每个查询包含query、result、citations';

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT '✅ 占卜过程数据表创建完成！' as status,
       '已创建表: reading_process_data' as tables,
       '已创建索引和RLS策略' as security;

