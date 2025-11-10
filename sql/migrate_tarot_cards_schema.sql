-- =============================================================================
-- Migration Script: Update tarot_cards table schema
-- =============================================================================
-- 迁移脚本：更新 tarot_cards 表结构
-- 
-- 更新内容：
-- 1. 重命名 card_name 为 card_name_en
-- 2. 添加 card_name_cn 字段
-- 3. 添加 symbolic_meaning 字段（大阿卡纳）
-- 4. 添加 additional_meanings 字段（小阿卡纳）
-- 5. 添加 image_url 字段
-- 6. 更新字段约束（NOT NULL）
-- 
-- 使用说明：
-- 1. 登录 Supabase Dashboard
-- 2. 进入 SQL Editor
-- 3. 复制并粘贴此脚本
-- 4. 点击 Run 执行
-- =============================================================================

-- Step 1: 添加新字段（如果不存在）
ALTER TABLE tarot_cards 
ADD COLUMN IF NOT EXISTS card_name_cn TEXT,
ADD COLUMN IF NOT EXISTS symbolic_meaning TEXT,
ADD COLUMN IF NOT EXISTS additional_meanings TEXT,
ADD COLUMN IF NOT EXISTS image_url TEXT;

-- Step 2: 如果 card_name 字段存在，重命名为 card_name_en
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tarot_cards' AND column_name = 'card_name'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tarot_cards' AND column_name = 'card_name_en'
    ) THEN
        ALTER TABLE tarot_cards RENAME COLUMN card_name TO card_name_en;
    END IF;
END $$;

-- Step 3: 更新约束（确保必需字段为 NOT NULL）
-- 注意：如果表中已有数据，这些操作可能会失败，需要先填充数据
DO $$
BEGIN
    -- 更新 card_number 约束
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tarot_cards' AND column_name = 'card_number' AND is_nullable = 'YES'
    ) THEN
        -- 先设置默认值，然后添加NOT NULL约束
        UPDATE tarot_cards SET card_number = 0 WHERE card_number IS NULL;
        ALTER TABLE tarot_cards ALTER COLUMN card_number SET NOT NULL;
    END IF;
    
    -- 更新 suit 约束
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tarot_cards' AND column_name = 'suit' AND is_nullable = 'YES'
    ) THEN
        UPDATE tarot_cards SET suit = 'major' WHERE suit IS NULL;
        ALTER TABLE tarot_cards ALTER COLUMN suit SET NOT NULL;
    END IF;
    
    -- 更新 description 约束
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tarot_cards' AND column_name = 'description' AND is_nullable = 'YES'
    ) THEN
        UPDATE tarot_cards SET description = '' WHERE description IS NULL;
        ALTER TABLE tarot_cards ALTER COLUMN description SET NOT NULL;
    END IF;
    
    -- 更新 upright_meaning 约束
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tarot_cards' AND column_name = 'upright_meaning' AND is_nullable = 'YES'
    ) THEN
        UPDATE tarot_cards SET upright_meaning = '' WHERE upright_meaning IS NULL;
        ALTER TABLE tarot_cards ALTER COLUMN upright_meaning SET NOT NULL;
    END IF;
    
    -- 更新 reversed_meaning 约束
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'tarot_cards' AND column_name = 'reversed_meaning' AND is_nullable = 'YES'
    ) THEN
        UPDATE tarot_cards SET reversed_meaning = '' WHERE reversed_meaning IS NULL;
        ALTER TABLE tarot_cards ALTER COLUMN reversed_meaning SET NOT NULL;
    END IF;
END $$;

-- Step 4: 创建新索引
CREATE INDEX IF NOT EXISTS tarot_cards_card_number_idx ON tarot_cards(card_number);
CREATE INDEX IF NOT EXISTS tarot_cards_card_name_en_idx ON tarot_cards(card_name_en);

-- Step 5: 验证迁移结果
SELECT 
    'Migration completed' as status,
    COUNT(*) as total_cards,
    COUNT(CASE WHEN card_name_en IS NOT NULL THEN 1 END) as cards_with_name_en,
    COUNT(CASE WHEN card_name_cn IS NOT NULL THEN 1 END) as cards_with_name_cn,
    COUNT(CASE WHEN symbolic_meaning IS NOT NULL THEN 1 END) as cards_with_symbolic_meaning,
    COUNT(CASE WHEN additional_meanings IS NOT NULL THEN 1 END) as cards_with_additional_meanings
FROM tarot_cards;

-- =============================================================================
-- 完成提示
-- =============================================================================

SELECT '✅ Schema migration completed!' as status,
       'Fields updated: card_name_en, card_name_cn, symbolic_meaning, additional_meanings, image_url' as changes,
       'Run build_tarot_database.py to populate with PKT data' as next_step;

