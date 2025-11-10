-- =============================================================================
-- 添加代表牌选择优先级字段到 user_profiles 表
-- =============================================================================

-- 添加 significator_priority 字段
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS significator_priority TEXT DEFAULT 'question_first' 
CHECK (significator_priority IN ('question_first', 'personality_first', 'zodiac_first'));

-- 添加注释
COMMENT ON COLUMN user_profiles.significator_priority IS '代表牌选择优先级：question_first（问题优先）、personality_first（性格优先）或 zodiac_first（星座优先），默认为 question_first';

-- 更新现有记录的默认值（如果字段已存在但值为NULL）
UPDATE user_profiles 
SET significator_priority = 'question_first' 
WHERE significator_priority IS NULL;

