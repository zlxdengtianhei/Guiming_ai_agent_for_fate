"""
对比初始优化和测试2（融合查询）的chunk使用情况
"""

import json
from pathlib import Path
from collections import Counter

# 读取初始优化结果
initial_file = Path(__file__).parent / "result" / "rag_optimization_test_20251107_214927.json"
with open(initial_file, 'r', encoding='utf-8') as f:
    initial_data = json.load(f)

# 读取测试2结果
test2_file = Path(__file__).parent / "result" / "rag_threshold_merge_test_20251107_225926.json"
with open(test2_file, 'r', encoding='utf-8') as f:
    test2_data = json.load(f)

# 提取chunk使用情况
def extract_chunks(data):
    """从测试数据中提取所有使用的chunk"""
    chunks = set()
    chunk_usage = Counter()
    
    # 尝试从rag_analysis中提取
    rag_analysis = data.get('rag_analysis', {})
    if rag_analysis:
        chunk_usage_dict = rag_analysis.get('chunk_usage', {})
        for chunk_id, count in chunk_usage_dict.items():
            chunks.add(chunk_id)
            chunk_usage[chunk_id] = count
    
    # 尝试从test2_merged_queries中提取
    test2_data = data.get('test2_merged_queries', {})
    if test2_data:
        analysis = test2_data.get('analysis', {})
        if analysis:
            chunk_usage_dict = analysis.get('chunk_usage', {})
            for chunk_id, count in chunk_usage_dict.items():
                chunks.add(chunk_id)
                chunk_usage[chunk_id] = count
    
    return chunks, chunk_usage

# 提取初始优化的chunks
initial_chunks, initial_usage = extract_chunks(initial_data)

# 提取测试2的chunks
test2_chunks, test2_usage = extract_chunks(test2_data)

# 对比分析
common_chunks = initial_chunks & test2_chunks
only_initial = initial_chunks - test2_chunks
only_test2 = test2_chunks - initial_chunks

print("="*80)
print("Chunk使用情况对比分析")
print("="*80)

print(f"\n初始优化（阈值0.5）:")
print(f"  总chunk数: {len(initial_chunks)}")
print(f"  总使用次数: {sum(initial_usage.values())}")

print(f"\n测试2（融合查询）:")
print(f"  总chunk数: {len(test2_chunks)}")
print(f"  总使用次数: {sum(test2_usage.values())}")

print(f"\n共同使用的chunks:")
print(f"  数量: {len(common_chunks)}")
print(f"  占比（相对于初始优化）: {len(common_chunks)/len(initial_chunks)*100:.1f}%")
print(f"  占比（相对于测试2）: {len(common_chunks)/len(test2_chunks)*100:.1f}%")

print(f"\n仅在初始优化中使用的chunks:")
print(f"  数量: {len(only_initial)}")
if only_initial:
    print(f"  列表:")
    for chunk_id in sorted(only_initial):
        count = initial_usage[chunk_id]
        print(f"    - {chunk_id}: 使用{count}次")

print(f"\n仅在测试2中使用的chunks:")
print(f"  数量: {len(only_test2)}")
if only_test2:
    print(f"  列表:")
    for chunk_id in sorted(only_test2):
        count = test2_usage[chunk_id]
        print(f"    - {chunk_id}: 使用{count}次")

# 分析共同chunks的使用次数变化
print(f"\n共同chunks的使用次数变化:")
print(f"  {'Chunk ID':<40} {'初始优化':<12} {'测试2':<12} {'变化':<10}")
print(f"  {'-'*40} {'-'*12} {'-'*12} {'-'*10}")

changes = []
for chunk_id in sorted(common_chunks):
    initial_count = initial_usage[chunk_id]
    test2_count = test2_usage[chunk_id]
    change = test2_count - initial_count
    changes.append((chunk_id, initial_count, test2_count, change))
    if abs(change) > 0:  # 只显示有变化的
        print(f"  {chunk_id:<40} {initial_count:<12} {test2_count:<12} {change:+d}")

# 统计变化
increased = sum(1 for _, _, _, c in changes if c > 0)
decreased = sum(1 for _, _, _, c in changes if c < 0)
unchanged = sum(1 for _, _, _, c in changes if c == 0)

print(f"\n变化统计:")
print(f"  使用次数增加的chunks: {increased}个")
print(f"  使用次数减少的chunks: {decreased}个")
print(f"  使用次数不变的chunks: {unchanged}个")

# 分析查询类型
print(f"\n" + "="*80)
print("查询类型对比")
print("="*80)

def extract_query_types(data):
    """提取查询类型"""
    query_types = Counter()
    
    # 从rag_analysis中提取
    rag_analysis = data.get('rag_analysis', {})
    if rag_analysis:
        query_to_chunks = rag_analysis.get('query_to_chunks', {})
        for query_info in query_to_chunks.values():
            query_type = query_info.get('type', 'unknown')
            query_types[query_type] += 1
    
    # 从test2_merged_queries中提取
    test2_data = data.get('test2_merged_queries', {})
    if test2_data:
        analysis = test2_data.get('analysis', {})
        if analysis:
            query_to_chunks = analysis.get('query_to_chunks', {})
            for query_info in query_to_chunks.values():
                query_type = query_info.get('type', 'unknown')
                query_types[query_type] += 1
    
    return query_types

initial_query_types = extract_query_types(initial_data)
test2_query_types = extract_query_types(test2_data)

print(f"\n初始优化的查询类型:")
for query_type, count in initial_query_types.most_common():
    print(f"  {query_type}: {count}个查询")

print(f"\n测试2的查询类型:")
for query_type, count in test2_query_types.most_common():
    print(f"  {query_type}: {count}个查询")

# 保存对比结果
output = {
    'initial_optimization': {
        'total_chunks': len(initial_chunks),
        'total_uses': sum(initial_usage.values()),
        'chunks': list(initial_chunks),
        'chunk_usage': dict(initial_usage),
        'query_types': dict(initial_query_types)
    },
    'test2_merged_queries': {
        'total_chunks': len(test2_chunks),
        'total_uses': sum(test2_usage.values()),
        'chunks': list(test2_chunks),
        'chunk_usage': dict(test2_usage),
        'query_types': dict(test2_query_types)
    },
    'comparison': {
        'common_chunks': list(common_chunks),
        'common_count': len(common_chunks),
        'only_initial': list(only_initial),
        'only_initial_count': len(only_initial),
        'only_test2': list(only_test2),
        'only_test2_count': len(only_test2),
        'common_chunks_usage_changes': [
            {
                'chunk_id': chunk_id,
                'initial_count': initial_count,
                'test2_count': test2_count,
                'change': change
            }
            for chunk_id, initial_count, test2_count, change in changes
        ],
        'usage_changes_stats': {
            'increased': increased,
            'decreased': decreased,
            'unchanged': unchanged
        }
    }
}

output_file = Path(__file__).parent / "result" / "chunk_comparison.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n对比结果已保存到: {output_file}")

