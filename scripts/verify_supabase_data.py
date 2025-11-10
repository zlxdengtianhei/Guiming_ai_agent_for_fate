#!/usr/bin/env python3
"""
验证 Supabase 数据库中的塔罗牌数据
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import get_supabase_service

def verify_data():
    """验证数据库中的数据"""
    supabase = get_supabase_service()
    
    print("=" * 60)
    print("验证 Supabase 数据库中的塔罗牌数据")
    print("=" * 60)
    
    # 1. 检查总数
    result = supabase.table("tarot_cards").select("card_name_en", count="exact").eq("source", "78degrees").execute()
    total_count = result.count if hasattr(result, 'count') else len(result.data)
    print(f"\n✅ 78degrees 来源的卡牌总数: {total_count}")
    
    # 2. 检查特定的问题卡牌
    problem_cards = ["The Empress", "The Hanged Man", "The Moon", "The World"]
    
    print("\n" + "=" * 60)
    print("检查特定卡牌的数据完整性")
    print("=" * 60)
    
    for card_name in problem_cards:
        result = supabase.table("tarot_cards").select(
            "card_name_en, upright_meaning, reversed_meaning"
        ).eq("source", "78degrees").eq("card_name_en", card_name).execute()
        
        if result.data:
            card = result.data[0]
            upright_len = len(card.get("upright_meaning", "") or "")
            reversed_len = len(card.get("reversed_meaning", "") or "")
            
            print(f"\n📋 {card_name}:")
            print(f"   正位含义长度: {upright_len} 字符")
            print(f"   逆位含义长度: {reversed_len} 字符")
            
            # 检查是否有问题
            if upright_len == 0:
                print(f"   ⚠️  警告: 正位含义为空")
            if reversed_len == 0:
                print(f"   ⚠️  警告: 逆位含义为空")
            if reversed_len > 100000:
                print(f"   ⚠️  警告: 逆位含义异常长 ({reversed_len} 字符)")
            
            # 显示前200字符预览
            if upright_len > 0:
                preview = card.get("upright_meaning", "")[:200]
                print(f"   正位含义预览: {preview}...")
            if reversed_len > 0:
                preview = card.get("reversed_meaning", "")[:200]
                print(f"   逆位含义预览: {preview}...")
        else:
            print(f"\n❌ {card_name}: 未找到")
    
    # 3. 统计信息
    print("\n" + "=" * 60)
    print("数据统计")
    print("=" * 60)
    
    # 检查有正位含义的卡牌数
    result = supabase.table("tarot_cards").select("card_name_en", count="exact").eq("source", "78degrees").not_.is_("upright_meaning", "null").neq("upright_meaning", "").execute()
    upright_count = result.count if hasattr(result, 'count') else len(result.data)
    print(f"有正位含义的卡牌: {upright_count}/{total_count}")
    
    # 检查有逆位含义的卡牌数
    result = supabase.table("tarot_cards").select("card_name_en", count="exact").eq("source", "78degrees").not_.is_("reversed_meaning", "null").neq("reversed_meaning", "").execute()
    reversed_count = result.count if hasattr(result, 'count') else len(result.data)
    print(f"有逆位含义的卡牌: {reversed_count}/{total_count}")
    
    # 检查大阿卡纳和小阿卡纳
    result = supabase.table("tarot_cards").select("card_name_en", count="exact").eq("source", "78degrees").eq("arcana", "major").execute()
    major_count = result.count if hasattr(result, 'count') else len(result.data)
    print(f"大阿卡纳: {major_count}")
    
    result = supabase.table("tarot_cards").select("card_name_en", count="exact").eq("source", "78degrees").eq("arcana", "minor").execute()
    minor_count = result.count if hasattr(result, 'count') else len(result.data)
    print(f"小阿卡纳: {minor_count}")
    
    print("\n" + "=" * 60)
    print("验证完成!")
    print("=" * 60)

if __name__ == "__main__":
    verify_data()

