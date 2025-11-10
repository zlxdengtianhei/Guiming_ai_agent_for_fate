"""
输出初始测试和测试2的查询问题对比
"""

import json
from pathlib import Path

# 读取初始优化结果
initial_file = Path(__file__).parent / "result" / "rag_optimization_test_20251107_214927.json"
with open(initial_file, 'r', encoding='utf-8') as f:
    initial_data = json.load(f)

# 读取测试2结果（需要运行新的测试2）
test2_file = Path(__file__).parent / "result" / "rag_threshold_merge_test_20251107_225926.json"
if test2_file.exists():
    with open(test2_file, 'r', encoding='utf-8') as f:
        test2_data = json.load(f)
else:
    test2_data = None

print("="*80)
print("初始测试（阈值0.5）的查询问题")
print("="*80)

rag_analysis = initial_data.get('rag_analysis', {})
query_to_chunks = rag_analysis.get('query_to_chunks', {})

print(f"\n总查询数: {len(query_to_chunks)}")
print(f"\n查询列表:\n")

# 按类型分组
queries_by_type = {}
for query, info in query_to_chunks.items():
    query_type = info.get('type', 'unknown')
    if query_type not in queries_by_type:
        queries_by_type[query_type] = []
    queries_by_type[query_type].append(query)

# 输出查询
for query_type in sorted(queries_by_type.keys()):
    print(f"\n【{query_type}】({len(queries_by_type[query_type])}个查询):")
    for i, query in enumerate(queries_by_type[query_type], 1):
        print(f"  {i}. {query}")

if test2_data:
    print("\n" + "="*80)
    print("测试2（融合查询）的查询问题")
    print("="*80)
    
    test2_analysis = test2_data.get('test2_merged_queries', {}).get('analysis', {})
    test2_query_to_chunks = test2_analysis.get('query_to_chunks', {})
    
    print(f"\n总查询数: {len(test2_query_to_chunks)}")
    print(f"\n查询列表:\n")
    
    # 按类型分组
    test2_queries_by_type = {}
    for query, info in test2_query_to_chunks.items():
        query_type = info.get('type', 'unknown')
        if query_type not in test2_queries_by_type:
            test2_queries_by_type[query_type] = []
        test2_queries_by_type[query_type].append(query)
    
    # 验证：确保所有查询都被提取
    print(f"验证: 提取到 {len(test2_queries_by_type)} 种查询类型，共 {sum(len(v) for v in test2_queries_by_type.values())} 个查询\n")
    
    # 按类别分组输出
    card_queries = ['basic_and_upright_meaning', 'basic_and_reversed_meaning', 'visual_description', 'position_and_psychological_meaning']
    method_queries = ['method_steps', 'position_interpretation', 'psychological_background', 'traditional_method']
    pattern_queries = ['number_patterns', 'suit_distribution', 'reversed_pattern', 'card_relationships']
    
    print("\n【卡牌信息查询】:")
    card_count = 0
    for query_type in card_queries:
        if query_type in test2_queries_by_type:
            count = len(test2_queries_by_type[query_type])
            card_count += count
            print(f"\n  {query_type} ({count}个查询):")
            for i, query in enumerate(test2_queries_by_type[query_type], 1):
                print(f"    {i}. {query}")
    print(f"\n  小计: {card_count}个查询")
    
    print("\n【占卜方法查询】:")
    method_count = 0
    for query_type in method_queries:
        if query_type in test2_queries_by_type:
            count = len(test2_queries_by_type[query_type])
            method_count += count
            print(f"\n  {query_type} ({count}个查询):")
            for i, query in enumerate(test2_queries_by_type[query_type], 1):
                print(f"    {i}. {query}")
    print(f"\n  小计: {method_count}个查询")
    
    print("\n【牌型分析查询】:")
    pattern_count = 0
    for query_type in pattern_queries:
        if query_type in test2_queries_by_type:
            count = len(test2_queries_by_type[query_type])
            pattern_count += count
            print(f"\n  {query_type} ({count}个查询):")
            for i, query in enumerate(test2_queries_by_type[query_type], 1):
                print(f"    {i}. {query}")
    print(f"\n  小计: {pattern_count}个查询")
    
    # 其他查询类型
    other_types = [t for t in test2_queries_by_type.keys() if t not in card_queries + method_queries + pattern_queries]
    if other_types:
        print("\n【其他查询】:")
        for query_type in other_types:
            print(f"\n  {query_type} ({len(test2_queries_by_type[query_type])}个查询):")
            for i, query in enumerate(test2_queries_by_type[query_type], 1):
                print(f"    {i}. {query}")
    
    # 对比
    print("\n" + "="*80)
    print("查询对比分析")
    print("="*80)
    
    initial_queries = set(query_to_chunks.keys())
    test2_queries = set(test2_query_to_chunks.keys())
    
    print(f"\n初始测试查询数: {len(initial_queries)}")
    print(f"测试2查询数: {len(test2_queries)}")
    print(f"差异: {len(initial_queries) - len(test2_queries)}个查询")
    
    print(f"\n初始测试查询类型: {len(queries_by_type)}种")
    print(f"测试2查询类型: {len(test2_queries_by_type)}种")
else:
    print("\n⚠️ 测试2结果文件不存在，请先运行测试2")

