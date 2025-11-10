"""
对比所有测试的chunk结果
"""

import json
from collections import defaultdict, Counter
from pathlib import Path

# 读取所有测试结果
test_files = {
    'initial': 'test/result/rag_optimization_test_20251107_214927.json',
    'test2_before': 'test/result/rag_threshold_merge_test_20251107_233832.json',
    'test2_improved': 'test/result/rag_threshold_merge_test_20251108_000643.json',
}

# 找到最新的测试2结果（融合了suit的版本）
result_dir = Path('test/result')
latest_test2_files = sorted(result_dir.glob('rag_threshold_merge_test_*.json'), reverse=True)
if latest_test2_files:
    test_files['test2_final'] = str(latest_test2_files[0])

all_tests = {}
for test_name, file_path in test_files.items():
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if test_name == 'initial':
                queries = data.get('rag_analysis', {}).get('query_to_chunks', {})
            else:
                queries = data.get('test2_merged_queries', {}).get('analysis', {}).get('query_to_chunks', {})
            all_tests[test_name] = {
                'queries': queries,
                'data': data
            }
    except Exception as e:
        print(f"⚠️ 无法读取 {test_name}: {e}")

# 收集每个测试的chunk
test_chunks = {}
test_query_counts = {}
for test_name, test_data in all_tests.items():
    chunks = set()
    chunk_to_queries = defaultdict(list)
    queries = test_data['queries']
    
    for query, info in queries.items():
        chunk_ids = info.get('chunk_ids', [])
        for chunk_id in chunk_ids:
            chunks.add(chunk_id)
            chunk_to_queries[chunk_id].append(query)
    
    test_chunks[test_name] = chunks
    test_query_counts[test_name] = len(queries)

# 获取初始测试的所有chunk作为基准
initial_chunks = test_chunks.get('initial', set())

print("="*80)
print("所有测试的Chunk对比分析")
print("="*80)

print(f"\n基准（初始测试）:")
print(f"  查询数: {test_query_counts.get('initial', 0)}")
print(f"  唯一Chunk数: {len(initial_chunks)}")

for test_name in ['test2_before', 'test2_improved', 'test2_final']:
    if test_name not in test_chunks:
        continue
    
    chunks = test_chunks[test_name]
    common = initial_chunks & chunks
    only_in_initial = initial_chunks - chunks
    only_in_test = chunks - initial_chunks
    coverage = len(common) / len(initial_chunks) * 100 if initial_chunks else 0
    
    print(f"\n{test_name}:")
    print(f"  查询数: {test_query_counts.get(test_name, 0)}")
    print(f"  唯一Chunk数: {len(chunks)}")
    print(f"  共同Chunk数: {len(common)}")
    print(f"  覆盖率: {coverage:.2f}%")
    print(f"  丢失Chunk数: {len(only_in_initial)}")
    print(f"  新增Chunk数: {len(only_in_test)}")

# 对比所有测试
print("\n" + "="*80)
print("详细对比")
print("="*80)

# 找出所有测试都有的chunk
all_test_names = list(test_chunks.keys())
if len(all_test_names) > 1:
    common_to_all = test_chunks[all_test_names[0]]
    for test_name in all_test_names[1:]:
        common_to_all &= test_chunks[test_name]
    print(f"\n所有测试都有的chunk数: {len(common_to_all)}")

# 对比test2_improved和test2_final
if 'test2_improved' in test_chunks and 'test2_final' in test_chunks:
    improved_chunks = test_chunks['test2_improved']
    final_chunks = test_chunks['test2_final']
    
    only_in_improved = improved_chunks - final_chunks
    only_in_final = final_chunks - improved_chunks
    common_both = improved_chunks & final_chunks
    
    print("\n" + "="*80)
    print("test2_improved vs test2_final (融合suit后)")
    print("="*80)
    print(f"test2_improved Chunk数: {len(improved_chunks)}")
    print(f"test2_final Chunk数: {len(final_chunks)}")
    print(f"共同Chunk数: {len(common_both)}")
    print(f"仅在test2_improved中: {len(only_in_improved)}")
    print(f"仅在test2_final中: {len(only_in_final)}")
    print(f"Chunk变化: {len(final_chunks) - len(improved_chunks):+d}")
    
    if only_in_improved:
        print(f"\n⚠️ 在test2_improved中但不在test2_final中的chunk ({len(only_in_improved)}个):")
        for chunk_id in sorted(only_in_improved)[:10]:
            print(f"  - {chunk_id}")
    
    if only_in_final:
        print(f"\n✅ 在test2_final中新增的chunk ({len(only_in_final)}个):")
        for chunk_id in sorted(only_in_final)[:10]:
            print(f"  - {chunk_id}")

# 保存详细分析
analysis_result = {
    'test_summary': {
        test_name: {
            'query_count': test_query_counts.get(test_name, 0),
            'unique_chunks': len(chunks),
            'coverage_rate': len(initial_chunks & chunks) / len(initial_chunks) * 100 if initial_chunks else 0,
            'missing_chunks': len(initial_chunks - chunks),
            'new_chunks': len(chunks - initial_chunks)
        }
        for test_name, chunks in test_chunks.items()
    },
    'initial_chunks': sorted(list(initial_chunks)),
    'test_chunks': {
        test_name: sorted(list(chunks))
        for test_name, chunks in test_chunks.items()
    }
}

with open('test/result/all_tests_comparison.json', 'w', encoding='utf-8') as f:
    json.dump(analysis_result, f, ensure_ascii=False, indent=2)

print(f"\n详细分析结果已保存到: test/result/all_tests_comparison.json")




