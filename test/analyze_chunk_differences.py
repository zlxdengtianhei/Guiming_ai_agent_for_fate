"""
分析初始测试和测试2的chunk差异
"""

import json
from collections import defaultdict, Counter

# 读取初始测试结果
with open('test/result/rag_optimization_test_20251107_214927.json', 'r', encoding='utf-8') as f:
    initial_data = json.load(f)

# 读取测试2结果
with open('test/result/rag_threshold_merge_test_20251107_233832.json', 'r', encoding='utf-8') as f:
    test2_data = json.load(f)

# 提取chunk信息
initial_queries = initial_data.get('rag_analysis', {}).get('query_to_chunks', {})
test2_queries = test2_data.get('test2_merged_queries', {}).get('analysis', {}).get('query_to_chunks', {})

# 收集所有chunk
initial_chunks = set()
initial_chunk_to_queries = defaultdict(list)

for query, info in initial_queries.items():
    chunk_ids = info.get('chunk_ids', [])
    for chunk_id in chunk_ids:
        initial_chunks.add(chunk_id)
        initial_chunk_to_queries[chunk_id].append(query)

test2_chunks = set()
test2_chunk_to_queries = defaultdict(list)

for query, info in test2_queries.items():
    chunk_ids = info.get('chunk_ids', [])
    for chunk_id in chunk_ids:
        test2_chunks.add(chunk_id)
        test2_chunk_to_queries[chunk_id].append(query)

# 分析差异
only_in_initial = initial_chunks - test2_chunks
only_in_test2 = test2_chunks - initial_chunks
common_chunks = initial_chunks & test2_chunks

print("="*80)
print("Chunk对比分析")
print("="*80)

print(f"\n初始测试总chunk数: {len(initial_chunks)}")
print(f"测试2总chunk数: {len(test2_chunks)}")
print(f"共同chunk数: {len(common_chunks)}")
print(f"仅在初始测试中的chunk数: {len(only_in_initial)}")
print(f"仅在测试2中的chunk数: {len(only_in_test2)}")

if only_in_initial:
    print(f"\n仅在初始测试中的chunk ({len(only_in_initial)}个):")
    for chunk_id in sorted(only_in_initial):
        queries = initial_chunk_to_queries[chunk_id]
        print(f"  - {chunk_id}")
        print(f"    出现在查询: {queries[0][:80]}...")
        if len(queries) > 1:
            print(f"    (共{len(queries)}个查询)")

if only_in_test2:
    print(f"\n仅在测试2中的chunk ({len(only_in_test2)}个):")
    for chunk_id in sorted(only_in_test2):
        queries = test2_chunk_to_queries[chunk_id]
        print(f"  - {chunk_id}")
        print(f"    出现在查询: {queries[0][:80]}...")
        if len(queries) > 1:
            print(f"    (共{len(queries)}个查询)")

# 分析chunk使用频率
print("\n" + "="*80)
print("Chunk使用频率对比")
print("="*80)

initial_usage = Counter()
for query, info in initial_queries.items():
    for chunk_id in info.get('chunk_ids', []):
        initial_usage[chunk_id] += 1

test2_usage = Counter()
for query, info in test2_queries.items():
    for chunk_id in info.get('chunk_ids', []):
        test2_usage[chunk_id] += 1

# 找出使用频率变化较大的chunk
print("\n使用频率变化较大的chunk:")
usage_changes = []
for chunk_id in common_chunks:
    initial_count = initial_usage[chunk_id]
    test2_count = test2_usage[chunk_id]
    if initial_count != test2_count:
        usage_changes.append((chunk_id, initial_count, test2_count, test2_count - initial_count))

usage_changes.sort(key=lambda x: abs(x[3]), reverse=True)
for chunk_id, init_count, test2_count, diff in usage_changes[:20]:
    print(f"  {chunk_id}: {init_count}次 → {test2_count}次 (变化: {diff:+d})")

# 保存详细分析
analysis_result = {
    'initial_chunks': sorted(list(initial_chunks)),
    'test2_chunks': sorted(list(test2_chunks)),
    'common_chunks': sorted(list(common_chunks)),
    'only_in_initial': sorted(list(only_in_initial)),
    'only_in_test2': sorted(list(only_in_test2)),
    'chunk_usage_comparison': {
        chunk_id: {
            'initial_count': initial_usage[chunk_id],
            'test2_count': test2_usage[chunk_id],
            'difference': test2_usage[chunk_id] - initial_usage[chunk_id]
        }
        for chunk_id in (initial_chunks | test2_chunks)
    }
}

with open('test/result/chunk_difference_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(analysis_result, f, ensure_ascii=False, indent=2)

print(f"\n详细分析结果已保存到: test/result/chunk_difference_analysis.json")




