#!/usr/bin/env python3
"""
分析两个塔罗牌JSON文件，检查：
1. 每个卡片是否有详细的图像描述
2. 小阿卡纳是否每个花色都有不同的图像描述
3. 卡牌名称是否正确
"""

import json
from collections import defaultdict

def analyze_tarot_files():
    # 读取文件
    with open('database/data/pkt_tarot_cards.json', 'r', encoding='utf-8') as f:
        pkt = json.load(f)
    
    with open('database/data/78degrees_tarot_cards.json', 'r', encoding='utf-8') as f:
        degrees78 = json.load(f)
    
    print("=" * 80)
    print("塔罗牌JSON文件分析报告")
    print("=" * 80)
    print()
    
    # 1. 检查图像描述
    print("1. 图像描述检查")
    print("-" * 80)
    
    pkt_major = [c for c in pkt if c['arcana'] == 'major']
    pkt_minor = [c for c in pkt if c['arcana'] == 'minor']
    degrees78_major = [c for c in degrees78 if c['arcana'] == 'major']
    degrees78_minor = [c for c in degrees78 if c['arcana'] == 'minor']
    
    print(f"PKT文件:")
    print(f"  大阿卡纳: {len(pkt_major)} 张")
    print(f"  小阿卡纳: {len(pkt_minor)} 张")
    print(f"  有描述的大阿卡纳: {sum(1 for c in pkt_major if c.get('description', '').strip())}")
    print(f"  有描述的小阿卡纳: {sum(1 for c in pkt_minor if c.get('description', '').strip())}")
    
    print(f"\n78degrees文件:")
    print(f"  大阿卡纳: {len(degrees78_major)} 张")
    print(f"  小阿卡纳: {len(degrees78_minor)} 张")
    print(f"  有描述的大阿卡纳: {sum(1 for c in degrees78_major if c.get('description', '').strip())}")
    print(f"  有描述的小阿卡纳: {sum(1 for c in degrees78_minor if c.get('description', '').strip())}")
    
    # 检查描述长度
    pkt_desc_lengths = [len(c.get('description', '')) for c in pkt]
    degrees78_desc_lengths = [len(c.get('description', '')) for c in degrees78]
    
    print(f"\n描述长度统计:")
    print(f"  PKT平均描述长度: {sum(pkt_desc_lengths) / len(pkt_desc_lengths):.1f} 字符")
    print(f"  78degrees平均描述长度: {sum(degrees78_desc_lengths) / len(degrees78_desc_lengths):.1f} 字符")
    print(f"  PKT最短描述: {min(pkt_desc_lengths)} 字符")
    print(f"  PKT最长描述: {max(pkt_desc_lengths)} 字符")
    
    # 2. 检查小阿卡纳是否每个花色都有不同图像
    print("\n" + "=" * 80)
    print("2. 小阿卡纳图像描述分析")
    print("-" * 80)
    
    # 按数字和花色分组
    pkt_by_number = defaultdict(dict)
    for card in pkt_minor:
        card_num = card['card_number']
        suit = card['suit']
        pkt_by_number[card_num][suit] = card
    
    # 检查每个数字的四个花色是否有不同描述
    print("\n检查数字牌（Ace-10）是否每个花色都有独特的图像描述:")
    print()
    
    suit_elements = {
        'wands': ['wand', 'staff', 'club', 'stave', 'rod'],
        'cups': ['cup', 'water', 'chalice', 'ewer'],
        'swords': ['sword', 'weapon', 'blade'],
        'pentacles': ['pentacle', 'coin', 'money', 'disk']
    }
    
    for num in sorted(pkt_by_number.keys()):
        if num > 10:  # 跳过宫廷牌
            continue
        
        suits = pkt_by_number[num]
        if len(suits) == 4:  # 应该有4个花色
            descriptions = {suit: suits[suit].get('description', '') for suit in suits}
            
            # 检查每个描述是否包含对应花色的元素
            all_have_suit_elements = True
            for suit, desc in descriptions.items():
                has_element = any(elem.lower() in desc.lower() for elem in suit_elements.get(suit, []))
                if not has_element and desc:  # 如果有描述但不包含元素
                    all_have_suit_elements = False
            
            # 检查描述是否不同
            unique_descriptions = len(set(descriptions.values()))
            
            card_name = f"Ace" if num == 1 else f"{num}"
            print(f"{card_name}:")
            print(f"  四个花色都有描述: {all(descriptions.values())}")
            print(f"  描述都包含对应花色元素: {all_have_suit_elements}")
            print(f"  独特描述数量: {unique_descriptions}/4")
            
            if num <= 3:  # 显示前3个的详细示例
                for suit in ['wands', 'cups', 'swords', 'pentacles']:
                    if suit in descriptions:
                        desc = descriptions[suit]
                        print(f"    {suit}: {desc[:80]}...")
            print()
    
    # 3. 检查卡牌名称
    print("=" * 80)
    print("3. 卡牌名称检查")
    print("-" * 80)
    
    pkt_names = {c['card_name_en']: c for c in pkt}
    degrees78_names = {c['card_name_en']: c for c in degrees78}
    
    # 检查名称差异
    pkt_only = set(pkt_names.keys()) - set(degrees78_names.keys())
    degrees78_only = set(degrees78_names.keys()) - set(pkt_names.keys())
    
    print(f"\n名称差异:")
    if pkt_only:
        print(f"  只在PKT文件中存在: {pkt_only}")
    if degrees78_only:
        print(f"  只在78degrees文件中存在: {degrees78_only}")
    
    # 检查是否有拼写差异（如Judgement vs Judgment）
    common_names = set(pkt_names.keys()) & set(degrees78_names.keys())
    print(f"\n共同卡片数: {len(common_names)}")
    
    # 检查中文名称
    print("\n中文名称检查（前10个大阿卡纳）:")
    for i, card in enumerate(pkt_major[:10]):
        print(f"  {card['card_name_en']}: {card.get('card_name_cn', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)

if __name__ == '__main__':
    analyze_tarot_files()




