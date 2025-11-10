-- =============================================================================
-- Tarot Reading System - Database Migration
-- 创建用户个人信息表和扩展占卜相关表
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
-- 1. 创建 user_profiles 表 - 用户个人信息
-- =============================================================================

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 基本信息（用于选择代表牌）
    age INTEGER,                    -- 年龄（用于代表牌选择：40岁为分界）
    gender TEXT CHECK (gender IN ('male', 'female', 'other')),  -- 性别
    zodiac_sign TEXT,               -- 星座（用于元素对应）
    appearance_type TEXT CHECK (appearance_type IN ('wands', 'cups', 'swords', 'pentacles')),  -- 外貌类型
    personality_type TEXT CHECK (personality_type IN ('wands', 'cups', 'swords', 'pentacles')),  -- 性格类型
    
    -- 偏好设置
    preferred_source TEXT DEFAULT 'pkt' CHECK (preferred_source IN ('pkt', '78degrees', 'both')),  -- 偏好的数据源
    preferred_spread TEXT CHECK (preferred_spread IN ('auto', 'three_card', 'celtic_cross', 'work_cycle')),  -- 默认占卜方式
    
    -- 元数据
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_zodiac_sign ON user_profiles(zodiac_sign);

-- 更新时间戳触发器
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS策略
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role has full access to user_profiles"
    ON user_profiles FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- =============================================================================
-- 2. 扩展 readings 表 - 添加占卜流程相关字段
-- =============================================================================

-- 问题分析结果
ALTER TABLE readings ADD COLUMN IF NOT EXISTS question_domain TEXT CHECK (question_domain IN ('love', 'career', 'health', 'finance', 'personal_growth', 'general'));
ALTER TABLE readings ADD COLUMN IF NOT EXISTS question_complexity TEXT CHECK (question_complexity IN ('simple', 'moderate', 'complex'));
ALTER TABLE readings ADD COLUMN IF NOT EXISTS question_summary TEXT;

-- 占卜方式选择
ALTER TABLE readings ADD COLUMN IF NOT EXISTS spread_type TEXT NOT NULL DEFAULT 'three_card';
ALTER TABLE readings ADD COLUMN IF NOT EXISTS auto_selected_spread BOOLEAN DEFAULT TRUE;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS spread_reason TEXT;

-- 代表牌信息
ALTER TABLE readings ADD COLUMN IF NOT EXISTS significator_card_id UUID REFERENCES tarot_cards(id);
ALTER TABLE readings ADD COLUMN IF NOT EXISTS significator_selection_reason TEXT;

-- 牌型分析结果
ALTER TABLE readings ADD COLUMN IF NOT EXISTS spread_pattern_analysis JSONB;

-- 解读相关
ALTER TABLE readings ADD COLUMN IF NOT EXISTS interpretation TEXT;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS interpretation_metadata JSONB;

-- 状态管理
ALTER TABLE readings ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'card_selected', 'analyzing', 'completed', 'error'));
ALTER TABLE readings ADD COLUMN IF NOT EXISTS current_step TEXT CHECK (current_step IN ('question_analysis', 'card_selection', 'pattern_analysis', 'rag_retrieval', 'interpretation'));

-- 时间戳
ALTER TABLE readings ADD COLUMN IF NOT EXISTS question_analyzed_at TIMESTAMPTZ;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS cards_selected_at TIMESTAMPTZ;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS analysis_completed_at TIMESTAMPTZ;
ALTER TABLE readings ADD COLUMN IF NOT EXISTS interpreted_at TIMESTAMPTZ;

-- 索引
CREATE INDEX IF NOT EXISTS idx_readings_status ON readings(status);
CREATE INDEX IF NOT EXISTS idx_readings_current_step ON readings(current_step);
CREATE INDEX IF NOT EXISTS idx_readings_significator_card_id ON readings(significator_card_id);

-- =============================================================================
-- 3. 扩展 reading_cards 表 - 添加位置信息
-- =============================================================================

-- 位置信息（如果不存在）
ALTER TABLE reading_cards ADD COLUMN IF NOT EXISTS position TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE reading_cards ADD COLUMN IF NOT EXISTS position_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE reading_cards ADD COLUMN IF NOT EXISTS position_description TEXT;

-- 附加信息
ALTER TABLE reading_cards ADD COLUMN IF NOT EXISTS card_selected_at TIMESTAMPTZ DEFAULT now();

-- 关系信息（用于分析）
ALTER TABLE reading_cards ADD COLUMN IF NOT EXISTS related_positions TEXT[];

-- 确保唯一约束（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'reading_cards_reading_id_position_order_key'
    ) THEN
        ALTER TABLE reading_cards ADD CONSTRAINT reading_cards_reading_id_position_order_key 
        UNIQUE(reading_id, position_order);
    END IF;
END $$;

-- =============================================================================
-- 4. 创建 reading_analysis_log 表 - 分析日志
-- =============================================================================

CREATE TABLE IF NOT EXISTS reading_analysis_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reading_id UUID REFERENCES readings(id) ON DELETE CASCADE,
    
    -- 步骤信息
    step_type TEXT NOT NULL CHECK (step_type IN ('question_analysis', 'card_selection', 'pattern_analysis', 'rag_query', 'interpretation')),
    step_order INTEGER NOT NULL,
    
    -- 输入输出
    input_data JSONB,
    output_data JSONB,
    model_used TEXT,
    prompt_used TEXT,
    
    -- 性能指标
    processing_time_ms INTEGER,
    tokens_used INTEGER,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_reading_analysis_log_reading_id ON reading_analysis_log(reading_id);
CREATE INDEX IF NOT EXISTS idx_reading_analysis_log_step_type ON reading_analysis_log(step_type);
CREATE INDEX IF NOT EXISTS idx_reading_analysis_log_step_order ON reading_analysis_log(reading_id, step_order);

-- RLS策略
ALTER TABLE reading_analysis_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own reading logs"
    ON reading_analysis_log FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM readings 
            WHERE readings.id = reading_analysis_log.reading_id 
            AND readings.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to reading_analysis_log"
    ON reading_analysis_log FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- =============================================================================
-- 5. 添加表注释
-- =============================================================================

COMMENT ON TABLE user_profiles IS '用户个人信息表，用于个性化解读和代表牌选择';
COMMENT ON COLUMN user_profiles.age IS '年龄，用于代表牌选择（40岁为分界）';
COMMENT ON COLUMN user_profiles.gender IS '性别：male/female/other';
COMMENT ON COLUMN user_profiles.zodiac_sign IS '星座，用于元素对应（火象→Wands, 水象→Cups, 风象→Swords, 土象→Pentacles）';
COMMENT ON COLUMN user_profiles.appearance_type IS '外貌类型，对应花色';
COMMENT ON COLUMN user_profiles.personality_type IS '性格类型，覆盖外貌类型';

COMMENT ON TABLE reading_analysis_log IS '占卜分析日志表，记录每个分析步骤的详细信息';

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT '✅ 数据库迁移完成！' as status,
       '已创建表: user_profiles, reading_analysis_log' as tables,
       '已扩展表: readings, reading_cards' as extended_tables,
       '已创建索引和RLS策略' as security;

