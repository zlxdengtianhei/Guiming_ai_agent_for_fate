"""
测试选牌和代表牌选择功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.tarot.card_selection import CardSelectionService
from app.services.tarot.significator import SignificatorService
from app.core.database import get_supabase_service


async def test_get_deck():
    """测试从数据库获取牌堆"""
    print("=" * 60)
    print("测试1: 从数据库获取牌堆")
    print("=" * 60)
    
    service = CardSelectionService()
    
    # 测试PKT数据源
    print("\n测试PKT数据源...")
    pkt_deck = await service.get_deck_from_database(source='pkt')
    print(f"✅ PKT牌堆数量: {len(pkt_deck)}")
    
    if len(pkt_deck) > 0:
        print(f"示例牌: {pkt_deck[0].get('card_name_en')}")
    
    # 测试78degrees数据源（如果存在）
    print("\n测试78degrees数据源...")
    try:
        degrees_deck = await service.get_deck_from_database(source='78degrees')
        print(f"✅ 78degrees牌堆数量: {len(degrees_deck)}")
    except Exception as e:
        print(f"⚠️ 78degrees数据源测试失败: {e}")
    
    return pkt_deck


async def test_significator_selection():
    """测试代表牌选择"""
    print("\n" + "=" * 60)
    print("测试2: 代表牌选择")
    print("=" * 60)
    
    service = SignificatorService()
    
    # 测试用例1: 40岁以上女性
    print("\n测试用例1: 40岁以上女性，狮子座")
    significator, reason = await service.select_significator(
        age=45,
        gender='female',
        zodiac_sign='Leo',
        source='pkt'
    )
    print(f"✅ 代表牌: {significator.get('card_name_en')}")
    print(f"   选择原因: {reason}")
    
    # 测试用例2: 40岁以下男性
    print("\n测试用例2: 30岁男性，天蝎座")
    significator2, reason2 = await service.select_significator(
        age=30,
        gender='male',
        zodiac_sign='Scorpio',
        source='pkt'
    )
    print(f"✅ 代表牌: {significator2.get('card_name_en')}")
    print(f"   选择原因: {reason2}")
    
    # 测试用例3: 有性格类型
    print("\n测试用例3: 25岁女性，性格类型为cups")
    significator3, reason3 = await service.select_significator(
        age=25,
        gender='female',
        personality_type='cups',
        source='pkt'
    )
    print(f"✅ 代表牌: {significator3.get('card_name_en')}")
    print(f"   选择原因: {reason3}")
    
    return significator


async def test_card_selection():
    """测试选牌功能"""
    print("\n" + "=" * 60)
    print("测试3: 选牌功能")
    print("=" * 60)
    
    selection_service = CardSelectionService()
    significator_service = SignificatorService()
    
    # 1. 获取牌堆
    print("\n步骤1: 获取完整牌堆...")
    full_deck = await selection_service.get_deck_from_database(source='pkt')
    print(f"✅ 完整牌堆数量: {len(full_deck)}")
    
    # 2. 测试三牌占卜（不需要代表牌）
    print("\n步骤2: 三牌占卜选牌（不需要代表牌）...")
    shuffled_deck_three = await selection_service.shuffle_and_cut_deck(
        full_deck,
        significator=None,
        need_significator=False  # 三牌占卜不需要代表牌
    )
    print(f"✅ 三牌占卜牌堆数量: {len(shuffled_deck_three)} (应该是78张)")
    
    # 检查逆位情况
    reversed_count = sum(1 for card in shuffled_deck_three if card.get('is_reversed', False))
    print(f"✅ 逆位牌数量: {reversed_count} ({reversed_count/len(shuffled_deck_three)*100:.1f}%)")
    
    # 3. 三牌占卜选牌
    print("\n步骤3: 三牌占卜选牌...")
    selected_cards_three = await selection_service.select_cards_for_spread(
        spread_type='three_card',
        shuffled_deck=shuffled_deck_three,
        significator=None
    )
    
    print(f"✅ 选中了 {len(selected_cards_three)} 张牌:")
    for card in selected_cards_three:
        reversed_str = "逆位" if card.is_reversed else "正位"
        print(f"   [{card.position_order}] {card.position} ({card.position_description}): "
              f"{card.card_name_en} - {reversed_str}")
    
    # 4. 验证牌不重复
    card_ids = [card.card_id for card in selected_cards_three]
    if len(card_ids) == len(set(card_ids)):
        print("✅ 验证通过: 选中的牌没有重复")
    else:
        print("❌ 错误: 选中的牌有重复!")
    
    # 5. 测试凯尔特十字（需要代表牌）
    print("\n步骤4: 凯尔特十字占卜（需要代表牌）...")
    significator, reason = await significator_service.select_significator(
        age=28,
        gender='female',
        zodiac_sign='Leo',
        source='pkt'
    )
    print(f"✅ 代表牌: {significator.get('card_name_en')}")
    
    # 6. 洗牌和切牌（移除代表牌）
    print("\n步骤5: 洗牌和切牌（移除代表牌）...")
    shuffled_deck_cross = await selection_service.shuffle_and_cut_deck(
        full_deck,
        significator,
        need_significator=True  # 凯尔特十字需要代表牌
    )
    print(f"✅ 剩余牌堆数量: {len(shuffled_deck_cross)} (应该是77张)")
    
    # 7. 凯尔特十字选牌
    print("\n步骤6: 凯尔特十字占卜选牌...")
    selected_cards_cross = await selection_service.select_cards_for_spread(
        spread_type='celtic_cross',
        shuffled_deck=shuffled_deck_cross,
        significator=significator
    )
    
    print(f"✅ 选中了 {len(selected_cards_cross)} 张牌:")
    for card in selected_cards_cross[:3]:  # 只显示前3张
        reversed_str = "逆位" if card.is_reversed else "正位"
        print(f"   [{card.position_order}] {card.position}: {card.card_name_en} - {reversed_str}")
    print(f"   ... (共{len(selected_cards_cross)}张)")
    
    # 8. 验证代表牌不在选中牌中
    significator_id = significator.get('id')
    cross_card_ids = [card.card_id for card in selected_cards_cross]
    if significator_id not in cross_card_ids:
        print(f"✅ 验证通过: 代表牌({significator.get('card_name_en')})不在选中牌中")
    else:
        print(f"❌ 错误: 代表牌被选中了!")
    
    return selected_cards_three, selected_cards_cross


async def test_celtic_cross():
    """测试凯尔特十字占卜"""
    print("\n" + "=" * 60)
    print("测试4: 凯尔特十字占卜")
    print("=" * 60)
    
    selection_service = CardSelectionService()
    significator_service = SignificatorService()
    
    # 1. 获取牌堆
    full_deck = await selection_service.get_deck_from_database(source='pkt')
    
    # 2. 选择代表牌
    significator, reason = await significator_service.select_significator(
        age=35,
        gender='male',
        zodiac_sign='Gemini',
        source='pkt'
    )
    print(f"✅ 代表牌: {significator.get('card_name_en')}")
    
    # 3. 洗牌和切牌
    shuffled_deck = await selection_service.shuffle_and_cut_deck(
        full_deck,
        significator
    )
    
    # 4. 凯尔特十字选牌（10张）
    print("\n步骤4: 凯尔特十字占卜选牌（10张）...")
    selected_cards = await selection_service.select_cards_for_spread(
        spread_type='celtic_cross',
        shuffled_deck=shuffled_deck,
        significator=significator
    )
    
    print(f"✅ 选中了 {len(selected_cards)} 张牌:")
    for card in selected_cards:
        reversed_str = "逆位" if card.is_reversed else "正位"
        print(f"   [{card.position_order}] {card.position} ({card.position_description}): "
              f"{card.card_name_en} - {reversed_str}")
    
    # 5. 验证
    card_ids = [card.card_id for card in selected_cards]
    if len(card_ids) == len(set(card_ids)):
        print("✅ 验证通过: 选中的牌没有重复")
    else:
        print("❌ 错误: 选中的牌有重复!")
    
    significator_id = significator.get('id')
    if significator_id not in card_ids:
        print(f"✅ 验证通过: 代表牌不在选中牌中")
    else:
        print(f"❌ 错误: 代表牌被选中了!")
    
    return selected_cards


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("塔罗牌选牌功能测试")
    print("=" * 60)
    
    try:
        # 测试数据库连接
        print("\n检查数据库连接...")
        supabase = get_supabase_service()
        response = supabase.table('tarot_cards').select('id').limit(1).execute()
        if response.data:
            print("✅ 数据库连接正常")
        else:
            print("⚠️ 数据库中没有数据，请先导入塔罗牌数据")
            return
        
        # 运行测试
        await test_get_deck()
        await test_significator_selection()
        await test_card_selection()
        await test_celtic_cross()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

