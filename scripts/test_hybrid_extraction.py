#!/usr/bin/env python3
"""
测试混合提取方法 - 单张卡牌测试
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "extract_78degrees_cards_hybrid.py"))
from extract_78degrees_cards_hybrid import SeventyEightDegreesHybridExtractor

async def test_single_card():
    """测试提取单张卡牌"""
    doc_path = Path(__file__).parent.parent / "docs" / "78_degrees_of_wisdom.txt"
    
    if not doc_path.exists():
        print(f"文档不存在: {doc_path}")
        return
    
    extractor = SeventyEightDegreesHybridExtractor(doc_path)
    
    # 测试提取 The Fool
    print("=" * 60)
    print("测试提取: The Fool")
    print("=" * 60)
    
    card_data = await extractor.extract_major_arcana_card("The Fool", 0)
    
    print(f"\n卡牌名称: {card_data['card_name_en']}")
    print(f"描述长度: {len(card_data['description'])} 字符")
    print(f"象征意义长度: {len(card_data.get('symbolic_meaning', ''))} 字符")
    print(f"正位含义长度: {len(card_data['upright_meaning'])} 字符")
    print(f"逆位含义长度: {len(card_data['reversed_meaning'])} 字符")
    
    print("\n描述预览:")
    print(card_data['description'][:200] + "..." if len(card_data['description']) > 200 else card_data['description'])
    
    print("\n正位含义预览:")
    print(card_data['upright_meaning'][:200] + "..." if len(card_data['upright_meaning']) > 200 else card_data['upright_meaning'])
    
    print("\n逆位含义预览:")
    print(card_data['reversed_meaning'][:200] + "..." if len(card_data['reversed_meaning']) > 200 else card_data['reversed_meaning'])

if __name__ == "__main__":
    asyncio.run(test_single_card())

