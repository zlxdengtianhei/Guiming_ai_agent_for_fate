#!/usr/bin/env python3
"""
对比PKT和78度塔罗牌数据库的差异
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

def load_json_file(filepath: str) -> List[Dict]:
    """加载JSON文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def normalize_card_name(name: str) -> str:
    """标准化牌名以便比较"""
    return name.strip().lower()

def create_card_index(cards: List[Dict]) -> Dict[str, Dict]:
    """创建卡片索引，以(card_number, suit)为键"""
    index = {}
    for card in cards:
        key = (card.get('card_number'), card.get('suit', ''), card.get('arcana', ''))
        index[key] = card
    return index

def compare_field(field_name: str, pkt_value: Any, degrees78_value: Any) -> Dict[str, Any]:
    """比较单个字段"""
    result = {
        'field': field_name,
        'pkt_value': pkt_value if pkt_value else '(空)',
        'degrees78_value': degrees78_value if degrees78_value else '(空)',
        'pkt_length': len(str(pkt_value)) if pkt_value else 0,
        'degrees78_length': len(str(degrees78_value)) if degrees78_value else 0,
        'different': str(pkt_value).strip() != str(degrees78_value).strip()
    }
    return result

def compare_cards(pkt_card: Dict, degrees78_card: Dict) -> Dict[str, Any]:
    """比较两张牌"""
    comparison = {
        'card_name_en': pkt_card.get('card_name_en', ''),
        'card_number': pkt_card.get('card_number'),
        'suit': pkt_card.get('suit', ''),
        'fields_comparison': {}
    }
    
    # 比较各个字段
    fields_to_compare = [
        'description',
        'symbolic_meaning', 
        'upright_meaning',
        'reversed_meaning',
        'card_name_cn'
    ]
    
    for field in fields_to_compare:
        pkt_val = pkt_card.get(field, '')
        degrees78_val = degrees78_card.get(field, '')
        comparison['fields_comparison'][field] = compare_field(field, pkt_val, degrees78_val)
    
    return comparison

def analyze_differences(pkt_cards: List[Dict], degrees78_cards: List[Dict]) -> Dict[str, Any]:
    """分析两个数据库的差异"""
    
    # 创建索引
    pkt_index = {}
    degrees78_index = {}
    
    for card in pkt_cards:
        key = (card.get('card_number'), card.get('suit', ''), card.get('arcana', ''))
        pkt_index[key] = card
    
    for card in degrees78_cards:
        key = (card.get('card_number'), card.get('suit', ''), card.get('arcana', ''))
        degrees78_index[key] = card
    
    # 统计信息
    stats = {
        'total_pkt_cards': len(pkt_cards),
        'total_degrees78_cards': len(degrees78_cards),
        'common_cards': 0,
        'only_in_pkt': [],
        'only_in_degrees78': [],
    }
    
    # 比较结果
    comparisons = []
    field_differences = defaultdict(int)
    length_differences = defaultdict(list)
    
    # 找到所有唯一的键
    all_keys = set(pkt_index.keys()) | set(degrees78_index.keys())
    
    for key in all_keys:
        pkt_card = pkt_index.get(key)
        degrees78_card = degrees78_index.get(key)
        
        if pkt_card and degrees78_card:
            stats['common_cards'] += 1
            comparison = compare_cards(pkt_card, degrees78_card)
            comparisons.append(comparison)
            
            # 统计字段差异
            for field, field_comp in comparison['fields_comparison'].items():
                if field_comp['different']:
                    field_differences[field] += 1
                
                # 统计长度差异
                length_diff = field_comp['degrees78_length'] - field_comp['pkt_length']
                length_differences[field].append({
                    'card': comparison['card_name_en'],
                    'length_diff': length_diff,
                    'pkt_length': field_comp['pkt_length'],
                    'degrees78_length': field_comp['degrees78_length']
                })
        elif pkt_card:
            stats['only_in_pkt'].append({
                'card_name': pkt_card.get('card_name_en', ''),
                'key': key
            })
        elif degrees78_card:
            stats['only_in_degrees78'].append({
                'card_name': degrees78_card.get('card_name_en', ''),
                'key': key
            })
    
    return {
        'statistics': stats,
        'field_differences': dict(field_differences),
        'length_differences': dict(length_differences),
        'detailed_comparisons': comparisons
    }

def format_report(analysis: Dict[str, Any]) -> str:
    """格式化报告"""
    report = []
    report.append("=" * 80)
    report.append("塔罗牌数据库对比分析报告")
    report.append("=" * 80)
    report.append("")
    
    # 统计信息
    stats = analysis['statistics']
    report.append("【总体统计】")
    report.append(f"PKT数据库卡片总数: {stats['total_pkt_cards']}")
    report.append(f"78度数据库卡片总数: {stats['total_degrees78_cards']}")
    report.append(f"共同卡片数: {stats['common_cards']}")
    report.append(f"仅在PKT中的卡片: {len(stats['only_in_pkt'])}")
    report.append(f"仅在78度中的卡片: {len(stats['only_in_degrees78'])}")
    report.append("")
    
    # 字段差异统计
    report.append("【字段差异统计】")
    field_diffs = analysis['field_differences']
    for field, count in sorted(field_diffs.items(), key=lambda x: x[1], reverse=True):
        total = stats['common_cards']
        percentage = (count / total * 100) if total > 0 else 0
        report.append(f"  {field}: {count}/{total} ({percentage:.1f}%) 张牌有差异")
    report.append("")
    
    # 长度差异分析
    report.append("【内容长度差异分析】")
    length_diffs = analysis['length_differences']
    for field, differences in length_diffs.items():
        if differences:
            avg_diff = sum(d['length_diff'] for d in differences) / len(differences)
            max_diff = max(differences, key=lambda x: x['length_diff'])
            min_diff = min(differences, key=lambda x: x['length_diff'])
            
            report.append(f"\n  {field}:")
            report.append(f"    平均长度差异: {avg_diff:.0f} 字符 (78度比PKT{'长' if avg_diff > 0 else '短'})")
            report.append(f"    最大差异: {max_diff['length_diff']} 字符 ({max_diff['card']})")
            report.append(f"    最小差异: {min_diff['length_diff']} 字符 ({min_diff['card']})")
            
            # 找出差异最大的5张牌
            top_diff = sorted(differences, key=lambda x: abs(x['length_diff']), reverse=True)[:5]
            report.append(f"    差异最大的5张牌:")
            for diff in top_diff:
                report.append(f"      - {diff['card']}: {diff['length_diff']:+d} 字符 "
                            f"(PKT: {diff['pkt_length']}, 78度: {diff['degrees78_length']})")
    report.append("")
    
    # 详细对比示例（前10张有差异的牌）
    report.append("【详细对比示例（前10张有显著差异的牌）】")
    comparisons = analysis['detailed_comparisons']
    
    # 找出差异最大的牌
    significant_diffs = []
    for comp in comparisons:
        diff_score = 0
        for field, field_comp in comp['fields_comparison'].items():
            if field_comp['different']:
                diff_score += abs(field_comp['degrees78_length'] - field_comp['pkt_length'])
        if diff_score > 0:
            significant_diffs.append((comp, diff_score))
    
    significant_diffs.sort(key=lambda x: x[1], reverse=True)
    
    for i, (comp, score) in enumerate(significant_diffs[:10], 1):
        report.append(f"\n{i}. {comp['card_name_en']} (#{comp['card_number']}, {comp['suit']})")
        report.append(f"   差异总分数: {score} 字符")
        
        for field, field_comp in comp['fields_comparison'].items():
            if field_comp['different']:
                pkt_len = field_comp['pkt_length']
                deg78_len = field_comp['degrees78_length']
                len_diff = deg78_len - pkt_len
                
                report.append(f"   {field}:")
                report.append(f"     PKT长度: {pkt_len} 字符")
                report.append(f"     78度长度: {deg78_len} 字符")
                report.append(f"     差异: {len_diff:+d} 字符")
                
                # 显示内容摘要（前100字符）
                pkt_preview = str(field_comp['pkt_value'])[:100] + "..." if len(str(field_comp['pkt_value'])) > 100 else str(field_comp['pkt_value'])
                deg78_preview = str(field_comp['degrees78_value'])[:100] + "..." if len(str(field_comp['degrees78_value'])) > 100 else str(field_comp['degrees78_value'])
                
                report.append(f"     PKT内容预览: {pkt_preview}")
                report.append(f"     78度内容预览: {deg78_preview}")
    
    report.append("")
    report.append("=" * 80)
    
    return "\n".join(report)

def main():
    """主函数"""
    # 文件路径
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    pkt_file = project_root / 'rag' / 'data' / 'pkt_tarot_cards.json'
    degrees78_file = project_root / 'rag' / 'data' / '78degrees_tarot_cards.json'
    output_file = project_root / 'TAROT_DATABASE_COMPARISON.md'
    
    print("正在加载数据...")
    pkt_cards = load_json_file(str(pkt_file))
    degrees78_cards = load_json_file(str(degrees78_file))
    
    print("正在分析差异...")
    analysis = analyze_differences(pkt_cards, degrees78_cards)
    
    print("正在生成报告...")
    report = format_report(analysis)
    
    # 保存报告
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n报告已保存到: {output_file}")
    print("\n" + report)

if __name__ == '__main__':
    main()

