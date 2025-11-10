-- =============================================================================
-- Add interpretation_full_text and interpretation_summary columns to readings table
-- 为 readings 表添加 interpretation_full_text 和 interpretation_summary 字段
-- =============================================================================
-- 
-- 使用说明：
-- 1. 登录 Supabase Dashboard
-- 2. 进入 SQL Editor
-- 3. 新建查询（New Query）
-- 4. 复制并粘贴此脚本
-- 5. 点击 Run 执行
-- =============================================================================

-- 添加 interpretation_full_text 字段（保存完整的LLM原始输出）
ALTER TABLE readings ADD COLUMN IF NOT EXISTS interpretation_full_text TEXT;

-- 添加 interpretation_summary 字段（保存摘要，用于预览或隐藏数据）
ALTER TABLE readings ADD COLUMN IF NOT EXISTS interpretation_summary TEXT;

-- 添加注释
COMMENT ON COLUMN readings.interpretation_full_text IS '完整的LLM原始解读输出，保存完整的流式生成文本';
COMMENT ON COLUMN readings.interpretation_summary IS '解读摘要，用于预览或隐藏数据（通常是前500字符或自动生成的摘要）';
COMMENT ON COLUMN readings.interpretation IS '格式化后的解读文本（包含整体解读、位置解读、关系分析等结构化内容）';

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT '✅ interpretation_full_text 和 interpretation_summary 字段已添加到 readings 表' as status;



