"""
分析RAG查询日志，提取查询信息、统计搜索结果、分析重复和质量
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any
import re


def load_log_file(log_path: str) -> Dict[str, Any]:
    """加载日志文件"""
    with open(log_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_rag_queries(log_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从日志中提取所有RAG查询"""
    rag_queries = []
    
    for step in log_data.get('steps', []):
        if step.get('step_name') == 'rag_retrieval':
            queries = step.get('rag_queries', [])
            if queries:
                rag_queries.extend(queries)
    
    return rag_queries


def analyze_query_stats(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析查询统计信息"""
    stats = {
        'total_queries': len(queries),
        'queries_by_type': defaultdict(int),
        'queries_by_card': defaultdict(list),
        'num_results_distribution': defaultdict(int),
        'similarity_stats': {
            'min': float('inf'),
            'max': float('-inf'),
            'avg': 0.0,
            'all': []
        },
        'source_distribution': defaultdict(int),
        'chunk_id_frequency': defaultdict(int)
    }
    
    total_similarity = 0
    similarity_count = 0
    
    for query in queries:
        query_type = query.get('type', 'unknown')
        stats['queries_by_type'][query_type] += 1
        
        # 统计每个卡牌的查询
        card_id = query.get('card_id')
        card_name = query.get('card_name_en', 'N/A')
        if card_id:
            stats['queries_by_card'][card_name].append({
                'type': query_type,
                'query': query.get('query', ''),
                'num_results': query.get('result', {}).get('debug', {}).get('num_results', 0)
            })
        
        # 统计搜索结果数量
        result = query.get('result', {})
        debug = result.get('debug', {})
        num_results = debug.get('num_results', 0)
        stats['num_results_distribution'][num_results] += 1
        
        # 统计相似度分数
        citations = result.get('citations', [])
        for citation in citations:
            similarity = citation.get('similarity', 0)
            stats['similarity_stats']['all'].append(similarity)
            total_similarity += similarity
            similarity_count += 1
            
            if similarity < stats['similarity_stats']['min']:
                stats['similarity_stats']['min'] = similarity
            if similarity > stats['similarity_stats']['max']:
                stats['similarity_stats']['max'] = similarity
            
            # 统计来源分布
            source = citation.get('source', 'unknown')
            stats['source_distribution'][source] += 1
            
            # 统计chunk_id频率
            chunk_id = citation.get('chunk_id', 'unknown')
            stats['chunk_id_frequency'][chunk_id] += 1
    
    # 计算平均相似度
    if similarity_count > 0:
        stats['similarity_stats']['avg'] = total_similarity / similarity_count
    
    return stats


def find_duplicate_chunks(queries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """找出重复的chunk_id（在不同查询中出现）"""
    chunk_usage = defaultdict(list)
    
    for idx, query in enumerate(queries):
        query_type = query.get('type', 'unknown')
        card_name = query.get('card_name_en', 'N/A')
        result = query.get('result', {})
        citations = result.get('citations', [])
        
        for citation in citations:
            chunk_id = citation.get('chunk_id')
            if chunk_id:
                chunk_usage[chunk_id].append({
                    'query_index': idx,
                    'query_type': query_type,
                    'card_name': card_name,
                    'query': query.get('query', ''),
                    'similarity': citation.get('similarity', 0),
                    'source': citation.get('source', '')
                })
    
    # 只返回出现多次的chunk
    duplicates = {chunk_id: usages for chunk_id, usages in chunk_usage.items() if len(usages) > 1}
    return duplicates


def analyze_query_quality(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """分析查询质量"""
    quality_analysis = {
        'queries_with_no_results': [],
        'queries_with_low_similarity': [],
        'queries_with_high_similarity': [],
        'queries_by_quality': {
            'excellent': [],  # 最高相似度 > 0.6
            'good': [],      # 最高相似度 0.4-0.6
            'fair': [],      # 最高相似度 0.3-0.4
            'poor': []       # 最高相似度 < 0.3 或 无结果
        }
    }
    
    for idx, query in enumerate(queries):
        query_type = query.get('type', 'unknown')
        card_name = query.get('card_name_en', 'N/A')
        result = query.get('result', {})
        debug = result.get('debug', {})
        citations = result.get('citations', [])
        
        query_info = {
            'index': idx,
            'type': query_type,
            'card_name': card_name,
            'query': query.get('query', ''),
            'num_results': debug.get('num_results', 0)
        }
        
        if not citations:
            quality_analysis['queries_with_no_results'].append(query_info)
            quality_analysis['queries_by_quality']['poor'].append(query_info)
        else:
            max_similarity = max(c.get('similarity', 0) for c in citations)
            query_info['max_similarity'] = max_similarity
            
            if max_similarity > 0.6:
                quality_analysis['queries_with_high_similarity'].append(query_info)
                quality_analysis['queries_by_quality']['excellent'].append(query_info)
            elif max_similarity >= 0.4:
                quality_analysis['queries_by_quality']['good'].append(query_info)
            elif max_similarity >= 0.3:
                quality_analysis['queries_by_quality']['fair'].append(query_info)
            else:
                quality_analysis['queries_with_low_similarity'].append(query_info)
                quality_analysis['queries_by_quality']['poor'].append(query_info)
    
    return quality_analysis


def create_query_result_mapping(queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """创建问题与RAG搜索结果的对应关系"""
    mapping = []
    
    for idx, query in enumerate(queries):
        query_type = query.get('type', 'unknown')
        card_name = query.get('card_name_en', 'N/A')
        query_text = query.get('query', '')
        result = query.get('result', {})
        debug = result.get('debug', {})
        citations = result.get('citations', [])
        
        mapping_entry = {
            'query_index': idx + 1,
            'query_type': query_type,
            'card_name': card_name if card_name != 'N/A' else None,
            'query_text': query_text,
            'num_results_retrieved': debug.get('num_results', 0),
            'top_doc_ids': debug.get('top_doc_ids', []),
            'citations': [
                {
                    'source': c.get('source', ''),
                    'chunk_id': c.get('chunk_id', ''),
                    'similarity': c.get('similarity', 0)
                }
                for c in citations
            ],
            'result_text_preview': result.get('text', '')[:200] + '...' if len(result.get('text', '')) > 200 else result.get('text', ''),
            'latency_ms': debug.get('latency_ms', 0)
        }
        
        mapping.append(mapping_entry)
    
    return mapping


def generate_report(log_path: str, output_dir: str = None):
    """生成完整的分析报告"""
    print(f"正在分析日志文件: {log_path}")
    
    # 加载日志
    log_data = load_log_file(log_path)
    question = log_data.get('question', 'N/A')
    
    # 提取RAG查询
    queries = extract_rag_queries(log_data)
    print(f"找到 {len(queries)} 个RAG查询")
    
    if not queries:
        print("⚠️ 未找到RAG查询记录")
        return
    
    # 分析统计信息
    stats = analyze_query_stats(queries)
    
    # 查找重复
    duplicates = find_duplicate_chunks(queries)
    
    # 质量分析
    quality = analyze_query_quality(queries)
    
    # 创建映射
    mapping = create_query_result_mapping(queries)
    
    # 生成报告
    report = {
        'question': question,
        'summary': {
            'total_queries': stats['total_queries'],
            'queries_by_type': dict(stats['queries_by_type']),
            'total_unique_chunks': len(stats['chunk_id_frequency']),
            'duplicate_chunks_count': len(duplicates),
            'similarity_stats': {
                'min': stats['similarity_stats']['min'] if stats['similarity_stats']['min'] != float('inf') else 0,
                'max': stats['similarity_stats']['max'] if stats['similarity_stats']['max'] != float('-inf') else 0,
                'avg': stats['similarity_stats']['avg']
            },
            'source_distribution': dict(stats['source_distribution']),
            'quality_distribution': {
                'excellent': len(quality['queries_by_quality']['excellent']),
                'good': len(quality['queries_by_quality']['good']),
                'fair': len(quality['queries_by_quality']['fair']),
                'poor': len(quality['queries_by_quality']['poor'])
            }
        },
        'query_result_mapping': mapping,
        'duplicate_analysis': {
            'total_duplicate_chunks': len(duplicates),
            'duplicates': {
                chunk_id: usages
                for chunk_id, usages in list(duplicates.items())[:20]  # 只显示前20个
            }
        },
        'quality_analysis': {
            'queries_with_no_results': quality['queries_with_no_results'],
            'queries_with_low_similarity': quality['queries_with_low_similarity'][:10],  # 只显示前10个
            'queries_with_high_similarity': quality['queries_with_high_similarity'][:10],
            'quality_distribution': {
                k: len(v) for k, v in quality['queries_by_quality'].items()
            }
        },
        'detailed_stats': {
            'num_results_distribution': dict(stats['num_results_distribution']),
            'queries_by_card': {
                card: len(queries) for card, queries in stats['queries_by_card'].items()
            },
            'top_10_most_used_chunks': sorted(
                stats['chunk_id_frequency'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    }
    
    # 保存报告
    if output_dir is None:
        output_dir = Path(log_path).parent
    
    output_path = Path(output_dir) / f"rag_analysis_{Path(log_path).stem}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n✅ 分析完成！报告已保存到: {output_path}")
    
    # 打印摘要
    print("\n" + "="*80)
    print("RAG查询分析摘要")
    print("="*80)
    print(f"问题: {question}")
    print(f"\n总查询数: {stats['total_queries']}")
    print(f"\n查询类型分布:")
    for query_type, count in sorted(stats['queries_by_type'].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {query_type}: {count}")
    
    print(f"\n每次搜索获取的数据数量分布:")
    for num_results, count in sorted(stats['num_results_distribution'].items()):
        print(f"  - {num_results} 个结果: {count} 次查询")
    
    print(f"\n相似度统计:")
    print(f"  - 最低: {stats['similarity_stats']['min']:.4f}")
    print(f"  - 最高: {stats['similarity_stats']['max']:.4f}")
    print(f"  - 平均: {stats['similarity_stats']['avg']:.4f}")
    
    print(f"\n来源分布:")
    for source, count in sorted(stats['source_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {source}: {count} 次引用")
    
    print(f"\n重复分析:")
    print(f"  - 有 {len(duplicates)} 个chunk在不同查询中重复出现")
    if duplicates:
        print(f"  - 重复最多的chunk:")
        sorted_dups = sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)
        for chunk_id, usages in sorted_dups[:5]:
            print(f"    - {chunk_id}: 出现在 {len(usages)} 个查询中")
            for usage in usages[:3]:  # 只显示前3个使用情况
                print(f"      * {usage['query_type']} ({usage['card_name']}): {usage['query'][:50]}...")
    
    print(f"\n质量分析:")
    print(f"  - 优秀 (相似度>0.6): {len(quality['queries_by_quality']['excellent'])}")
    print(f"  - 良好 (相似度0.4-0.6): {len(quality['queries_by_quality']['good'])}")
    print(f"  - 一般 (相似度0.3-0.4): {len(quality['queries_by_quality']['fair'])}")
    print(f"  - 较差 (相似度<0.3或无结果): {len(quality['queries_by_quality']['poor'])}")
    
    if quality['queries_with_no_results']:
        print(f"\n⚠️ 有 {len(quality['queries_with_no_results'])} 个查询没有返回结果")
    
    return report


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python analyze_rag_queries.py <log_file_path> [output_dir]")
        sys.exit(1)
    
    log_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    generate_report(log_path, output_dir)





