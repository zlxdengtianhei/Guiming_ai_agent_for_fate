-- =============================================================================
-- Add imagery_description column to readings table
-- 为 readings 表添加 imagery_description 字段
-- =============================================================================
-- 
-- 使用说明：
-- 1. 登录 Supabase Dashboard
-- 2. 进入 SQL Editor
-- 3. 新建查询（New Query）
-- 4. 复制并粘贴此脚本
-- 5. 点击 Run 执行
-- =============================================================================

-- 添加 imagery_description 字段到 readings 表
ALTER TABLE readings ADD COLUMN IF NOT EXISTS imagery_description TEXT;

-- 添加注释
COMMENT ON COLUMN readings.imagery_description IS '牌阵意象描述，由LLM生成的完整意象描述文本';

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT '✅ imagery_description 字段已添加到 readings 表' as status;



