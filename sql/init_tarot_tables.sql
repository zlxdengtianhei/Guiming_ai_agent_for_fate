-- =============================================================================
-- Tarot Agent Database Initialization
-- =============================================================================
-- 塔罗占卜系统数据库初始化脚本
-- 
-- 使用说明：
-- 1. 登录 Supabase Dashboard
-- 2. 进入 SQL Editor
-- 3. 新建查询（New Query）
-- 4. 复制并粘贴此脚本
-- 5. 点击 Run 执行
-- =============================================================================

-- =============================================================================
-- 1. 创建 readings 表 - 占卜记录
-- =============================================================================

CREATE TABLE IF NOT EXISTS readings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    spread_type TEXT NOT NULL DEFAULT 'three_card',
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    interpretation TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- 2. 创建 tarot_cards 表 - 标准78张塔罗牌
-- =============================================================================

CREATE TABLE IF NOT EXISTS tarot_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_name_en TEXT NOT NULL UNIQUE,     -- 英文名称（唯一标识）
    card_name_cn TEXT,                     -- 中文名称
    card_number INTEGER NOT NULL,          -- 编号：大阿卡纳0-21，小阿卡纳1-14
    suit TEXT NOT NULL,                    -- 花色：major/wands/cups/swords/pentacles
    arcana TEXT NOT NULL,                  -- 类别：major/minor
    description TEXT NOT NULL,             -- 完整PKT原文图像描述
    upright_meaning TEXT NOT NULL,         -- PKT原文正位占卜含义
    reversed_meaning TEXT NOT NULL,        -- PKT原文逆位占卜含义
    symbolic_meaning TEXT,                 -- 深层象征意义和哲学解释（大阿卡纳）
    additional_meanings TEXT,              -- 额外占卜含义（小阿卡纳，来自PART III section 4）
    image_url TEXT,                        -- 图片链接（可选）
    created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- 3. 创建 reading_cards 表 - 占卜中的卡牌关联
-- =============================================================================

CREATE TABLE IF NOT EXISTS reading_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reading_id UUID REFERENCES readings(id) ON DELETE CASCADE,
    card_id UUID REFERENCES tarot_cards(id) ON DELETE CASCADE,
    position TEXT NOT NULL, -- past, present, future, etc.
    is_reversed BOOLEAN DEFAULT FALSE,
    position_order INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(reading_id, position_order)
);

-- =============================================================================
-- 4. 创建索引
-- =============================================================================

-- Readings 表索引
CREATE INDEX IF NOT EXISTS readings_user_id_idx ON readings(user_id);
CREATE INDEX IF NOT EXISTS readings_created_at_idx ON readings(created_at DESC);
CREATE INDEX IF NOT EXISTS readings_spread_type_idx ON readings(spread_type);

-- Reading cards 表索引
CREATE INDEX IF NOT EXISTS reading_cards_reading_id_idx ON reading_cards(reading_id);
CREATE INDEX IF NOT EXISTS reading_cards_card_id_idx ON reading_cards(card_id);

-- Tarot cards 表索引
CREATE INDEX IF NOT EXISTS tarot_cards_suit_idx ON tarot_cards(suit);
CREATE INDEX IF NOT EXISTS tarot_cards_arcana_idx ON tarot_cards(arcana);
CREATE INDEX IF NOT EXISTS tarot_cards_card_number_idx ON tarot_cards(card_number);
CREATE INDEX IF NOT EXISTS tarot_cards_card_name_en_idx ON tarot_cards(card_name_en);

-- =============================================================================
-- 5. 启用 Row Level Security (RLS)
-- =============================================================================

ALTER TABLE readings ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_cards ENABLE ROW LEVEL SECURITY;
-- tarot_cards 表通常不需要RLS，因为它是公共参考数据

-- =============================================================================
-- 6. 创建 RLS 策略
-- =============================================================================

-- Readings 表策略
CREATE POLICY "Users can view their own readings"
    ON readings FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create their own readings"
    ON readings FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own readings"
    ON readings FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own readings"
    ON readings FOR DELETE
    USING (auth.uid() = user_id);

-- Service role 可以访问所有数据（用于后端操作）
CREATE POLICY "Service role has full access to readings"
    ON readings FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Reading cards 表策略
CREATE POLICY "Users can view their own reading cards"
    ON reading_cards FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM readings 
            WHERE readings.id = reading_cards.reading_id 
            AND readings.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can create reading cards for their readings"
    ON reading_cards FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM readings 
            WHERE readings.id = reading_cards.reading_id 
            AND readings.user_id = auth.uid()
        )
    );

CREATE POLICY "Service role has full access to reading_cards"
    ON reading_cards FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- Tarot cards 表策略 - 允许所有人读取（公共参考数据）
CREATE POLICY "Anyone can view tarot cards"
    ON tarot_cards FOR SELECT
    USING (true);

-- =============================================================================
-- 7. 创建辅助函数
-- =============================================================================

-- 获取用户的占卜记录
CREATE OR REPLACE FUNCTION get_user_readings(user_uuid UUID)
RETURNS TABLE (
    id UUID,
    question TEXT,
    spread_type TEXT,
    interpretation TEXT,
    status TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        readings.id,
        readings.question,
        readings.spread_type,
        readings.interpretation,
        readings.status,
        readings.created_at
    FROM readings
    WHERE readings.user_id = user_uuid
    ORDER BY readings.created_at DESC;
END;
$$;

-- 获取占卜的详细信息（包括卡牌）
CREATE OR REPLACE FUNCTION get_reading_details(reading_uuid UUID)
RETURNS TABLE (
    reading_id UUID,
    question TEXT,
    spread_type TEXT,
    interpretation TEXT,
    card_name_en TEXT,
    card_name_cn TEXT,
    card_suit TEXT,
    card_position TEXT,
    is_reversed BOOLEAN,
    position_order INTEGER
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id as reading_id,
        r.question,
        r.spread_type,
        r.interpretation,
        tc.card_name_en,
        tc.card_name_cn,
        tc.suit as card_suit,
        rc.position as card_position,
        rc.is_reversed,
        rc.position_order
    FROM readings r
    LEFT JOIN reading_cards rc ON r.id = rc.reading_id
    LEFT JOIN tarot_cards tc ON rc.card_id = tc.id
    WHERE r.id = reading_uuid
    ORDER BY rc.position_order;
END;
$$;

-- 更新时间戳触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为 readings 表创建更新时间戳触发器
CREATE TRIGGER update_readings_updated_at
    BEFORE UPDATE ON readings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 8. 授予权限
-- =============================================================================

GRANT EXECUTE ON FUNCTION get_user_readings(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_reading_details(UUID) TO authenticated;

-- =============================================================================
-- 9. 插入初始数据（可选）- 78张标准塔罗牌
-- =============================================================================

-- 注意：这里只插入几张示例牌，完整的78张牌需要通过 build_tarot_database.py 脚本从PKT文档提取
-- 示例数据已移除，使用脚本提取的完整PKT原文数据

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT '✅ 数据库初始化完成！' as status,
       '已创建表: readings, tarot_cards, reading_cards' as tables,
       '已启用RLS并创建策略' as security,
       '已创建辅助函数' as functions;

