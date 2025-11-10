-- 创建塔罗牌数据库表结构
-- 用于存储PKT和78degrees的塔罗牌和占卜方法数据

-- 1. 塔罗牌表 (tarot_cards)
CREATE TABLE IF NOT EXISTS tarot_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL CHECK (source IN ('pkt', '78degrees')),
    card_name_en TEXT NOT NULL,
    card_name_cn TEXT,
    card_number INTEGER NOT NULL,
    suit TEXT NOT NULL CHECK (suit IN ('major', 'wands', 'cups', 'swords', 'pentacles')),
    arcana TEXT NOT NULL CHECK (arcana IN ('major', 'minor')),
    description TEXT,
    symbolic_meaning TEXT,
    upright_meaning TEXT,
    reversed_meaning TEXT,
    additional_meanings TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    -- 确保同一source中card_name_en唯一
    UNIQUE(source, card_name_en)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tarot_cards_source ON tarot_cards(source);
CREATE INDEX IF NOT EXISTS idx_tarot_cards_card_number ON tarot_cards(card_number);
CREATE INDEX IF NOT EXISTS idx_tarot_cards_suit ON tarot_cards(suit);
CREATE INDEX IF NOT EXISTS idx_tarot_cards_arcana ON tarot_cards(arcana);
CREATE INDEX IF NOT EXISTS idx_tarot_cards_source_card_number ON tarot_cards(source, card_number);

-- 2. 占卜方法表 (divination_methods)
CREATE TABLE IF NOT EXISTS divination_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL CHECK (source IN ('pkt', '78degrees')),
    chunk_id TEXT NOT NULL,
    text TEXT NOT NULL,
    source_book TEXT, -- 存储原始来源，如 "PKT - The Pictorial Key to the Tarot, Part III, Section 6"
    method_type TEXT, -- 如 'celtic_cross', 'three_card_spread', 'general_principles' 等
    type TEXT CHECK (type IN ('divination_method', 'interpretation')),
    section TEXT, -- 如 "Part III, Section 6"
    title TEXT,
    card_count INTEGER, -- 如果需要，如10 for Celtic Cross
    lines TEXT, -- 原始行号信息
    interpretation_type TEXT, -- 如 'recurrence'
    position TEXT, -- 如 'natural', 'reversed'
    arcana_type TEXT, -- 'major' or 'minor'
    suit TEXT, -- 对于minor arcana
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    -- 确保同一source中chunk_id唯一
    UNIQUE(source, chunk_id)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_divination_methods_source ON divination_methods(source);
CREATE INDEX IF NOT EXISTS idx_divination_methods_method_type ON divination_methods(method_type);
CREATE INDEX IF NOT EXISTS idx_divination_methods_type ON divination_methods(type);
CREATE INDEX IF NOT EXISTS idx_divination_methods_source_chunk_id ON divination_methods(source, chunk_id);

-- 3. 添加更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tarot_cards_updated_at BEFORE UPDATE ON tarot_cards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_divination_methods_updated_at BEFORE UPDATE ON divination_methods
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. 启用行级安全（如果需要）
-- ALTER TABLE tarot_cards ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE divination_methods ENABLE ROW LEVEL SECURITY;

-- 5. 创建注释
COMMENT ON TABLE tarot_cards IS '存储塔罗牌信息，包括PKT和78degrees两个来源';
COMMENT ON TABLE divination_methods IS '存储占卜方法和解释，包括PKT和78degrees两个来源';
COMMENT ON COLUMN tarot_cards.source IS '数据来源：pkt (Pictorial Key to the Tarot) 或 78degrees (78 Degrees of Wisdom)';
COMMENT ON COLUMN divination_methods.source IS '数据来源：pkt 或 78degrees';
COMMENT ON COLUMN divination_methods.chunk_id IS '唯一标识符，用于标识特定的方法或解释片段';

