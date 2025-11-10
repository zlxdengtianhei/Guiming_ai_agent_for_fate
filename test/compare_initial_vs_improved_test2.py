"""
对比初始测试和改进后的测试2的chunk差异
"""

import json
from collections import defaultdict, Counter

# 读取初始测试结果
with open('test/result/rag_optimization_test_20251107_214927.json', 'r', encoding='utf-8') as f:
    initial_data = json.load(f)

# 读取改进后的测试2结果
with open('test/result/rag_threshold_merge_test_20251108_000643.json', 'r', encoding='utf-8') as f:
    improved_test2_data = json.load(f)

# 提取chunk信息
initial_queries = initial_data.get('rag_analysis', {}).get('query_to_chunks', {})
improved_test2_queries = improved_test2_data.get('test2_merged_queries', {}).get('analysis', {}).get('query_to_chunks', {})

# 收集所有chunk
initial_chunks = set()
initial_chunk_to_queries = defaultdict(list)

for query, info in initial_queries.items():
    chunk_ids = info.get('chunk_ids', [])
    for chunk_id in chunk_ids:
        initial_chunks.add(chunk_id)
        initial_chunk_to_queries[chunk_id].append(query)

improved_test2_chunks = set()
improved_test2_chunk_to_queries = defaultdict(list)

for query, info in improved_test2_queries.items():
    chunk_ids = info.get('chunk_ids', [])
    for chunk_id in chunk_ids:
        improved_test2_chunks.add(chunk_id)
        improved_test2_chunk_to_queries[chunk_id].append(query)

# 分析差异
only_in_initial = initial_chunks - improved_test2_chunks
only_in_improved = improved_test2_chunks - initial_chunks
common_chunks = initial_chunks & improved_test2_chunks

print("="*80)
print("初始测试 vs 改进后的测试2 - Chunk对比分析")
print("="*80)

print(f"\n初始测试总chunk数: {len(initial_chunks)}")
print(f"改进后测试2总chunk数: {len(improved_test2_chunks)}")
print(f"共同chunk数: {len(common_chunks)}")
print(f"仅在初始测试中的chunk数: {len(only_in_initial)}")
print(f"仅在改进后测试2中的chunk数: {len(only_in_improved)}")
print(f"覆盖率: {len(common_chunks) / len(initial_chunks) * 100:.2f}%")

if only_in_initial:
    print(f"\n⚠️ 仍在初始测试中但未在改进后测试2中找到的chunk ({len(only_in_initial)}个):")
    for chunk_id in sorted(only_in_initial):
        queries = initial_chunk_to_queries[chunk_id]
        print(f"  - {chunk_id}")
        print(f"    出现在初始测试的查询: {queries[0][:70]}...")
        if len(queries) > 1:
            print(f"    (共{len(queries)}个查询)")

if only_in_improved:
    print(f"\n✅ 改进后测试2新增的chunk ({len(only_in_improved)}个):")
    for chunk_id in sorted(only_in_improved):
        queries = improved_test2_chunk_to_queries[chunk_id]
        print(f"  - {chunk_id}")
        print(f"    出现在改进后测试2的查询: {queries[0][:70]}...")
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

improved_test2_usage = Counter()
for query, info in improved_test2_queries.items():
    for chunk_id in info.get('chunk_ids', []):
        improved_test2_usage[chunk_id] += 1

# 找出使用频率变化较大的chunk
print("\n使用频率变化较大的chunk:")
usage_changes = []
for chunk_id in (initial_chunks | improved_test2_chunks):
    initial_count = initial_usage[chunk_id]
    improved_count = improved_test2_usage[chunk_id]
    if initial_count != improved_count:
        usage_changes.append((chunk_id, initial_count, improved_count, improved_count - initial_count))

usage_changes.sort(key=lambda x: abs(x[3]), reverse=True)
for chunk_id, init_count, improved_count, diff in usage_changes[:20]:
    print(f"  {chunk_id}: {init_count}次 → {improved_count}次 (变化: {diff:+d})")

# 检查之前丢失的chunk是否被找回
print("\n" + "="*80)
print("检查之前丢失的chunk是否被找回")
print("="*80)

# 之前丢失的chunk列表（从之前的分析中）
previously_missing = [
    '78degrees-section-0209#1',
    '78degrees-section-0225#1',
    '78degrees-section-0226#1',
    '78degrees-section-0239#1',
    '78degrees-section-0241#1',
    '78degrees-section-0244#1',
    '78degrees-section-0256#1',
    '78degrees-section-0264#1',
    'pkt-section-0045#2',
    'pkt-section-0086#1'
]

recovered = []
still_missing = []

for chunk_id in previously_missing:
    if chunk_id in improved_test2_chunks:
        recovered.append(chunk_id)
        print(f"✅ 已找回: {chunk_id}")
    else:
        still_missing.append(chunk_id)
        print(f"❌ 仍缺失: {chunk_id}")

print(f"\n找回率: {len(recovered)}/{len(previously_missing)} = {len(recovered)/len(previously_missing)*100:.1f}%")

# 保存详细分析
analysis_result = {
    'initial_chunks': sorted(list(initial_chunks)),
    'improved_test2_chunks': sorted(list(improved_test2_chunks)),
    'common_chunks': sorted(list(common_chunks)),
    'only_in_initial': sorted(list(only_in_initial)),
    'only_in_improved': sorted(list(only_in_improved)),
    'coverage_rate': len(common_chunks) / len(initial_chunks) * 100,
    'previously_missing_chunks': previously_missing,
    'recovered_chunks': recovered,
    'still_missing_chunks': still_missing,
    'recovery_rate': len(recovered) / len(previously_missing) * 100 if previously_missing else 0,
    'chunk_usage_comparison': {
        chunk_id: {
            'initial_count': initial_usage[chunk_id],
            'improved_test2_count': improved_test2_usage[chunk_id],
            'difference': improved_test2_usage[chunk_id] - initial_usage[chunk_id]
        }
        for chunk_id in (initial_chunks | improved_test2_chunks)
    }
}

with open('test/result/initial_vs_improved_test2_analysis.json', 'w', encoding='utf-8') as f:
    json.dump(analysis_result, f, ensure_ascii=False, indent=2)

print(f"\n详细分析结果已保存到: test/result/initial_vs_improved_test2_analysis.json")




