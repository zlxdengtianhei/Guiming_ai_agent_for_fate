"""
测试RAG优化后的完整占卜流程 - 分析重复率和性能
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path
from collections import Counter
from datetime import datetime

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.tarot.reading_service import ReadingService
from app.models.schemas import UserProfileCreate
from app.core.database import get_supabase_service


def analyze_rag_duplicates(rag_queries):
    """分析RAG查询的重复chunk情况"""
    chunk_usage = Counter()
    query_to_chunks = {}
    
    for query_record in rag_queries:
        query = query_record.get('query', '')
        query_type = query_record.get('type', 'unknown')
        citations = query_record.get('result', {}).get('citations', [])
        
        chunk_ids = []
        for citation in citations:
            chunk_id = citation.get('chunk_id', '')
            if chunk_id:
                chunk_ids.append(chunk_id)
                chunk_usage[chunk_id] += 1
        
        if chunk_ids:
            query_to_chunks[query] = {
                'type': query_type,
                'chunk_ids': chunk_ids,
                'chunk_count': len(chunk_ids)
            }
    
    # 找出重复使用的chunks
    duplicate_chunks = {chunk_id: count for chunk_id, count in chunk_usage.items() if count > 1}
    
    # 统计信息
    total_queries = len(query_to_chunks)
    total_unique_chunks = len(chunk_usage)
    total_chunk_uses = sum(chunk_usage.values())
    duplicate_count = len(duplicate_chunks)
    duplicate_uses = sum(duplicate_chunks.values())
    
    # 计算重复率
    if total_chunk_uses > 0:
        duplicate_rate = (duplicate_uses - duplicate_count) / total_chunk_uses * 100
    else:
        duplicate_rate = 0
    
    return {
        'total_queries': total_queries,
        'total_unique_chunks': total_unique_chunks,
        'total_chunk_uses': total_chunk_uses,
        'duplicate_chunks': duplicate_chunks,
        'duplicate_count': duplicate_count,
        'duplicate_uses': duplicate_uses,
        'duplicate_rate': duplicate_rate,
        'query_to_chunks': query_to_chunks,
        'chunk_usage': dict(chunk_usage)
    }


async def test_optimized_reading():
    """测试优化后的完整占卜流程"""
    print("\n" + "="*80)
    print("测试: RAG优化后的完整占卜流程")
    print("="*80)
    
    service = ReadingService()
    
    # 创建测试用户信息
    user_profile = UserProfileCreate(
        age=30,
        gender="male",
        zodiac_sign="Scorpio",
        appearance_type="swords",
        personality_type="cups",
        preferred_source="pkt"
    )
    
    question = "我下个月运势如何"
    
    print(f"\n问题: {question}")
    print(f"用户信息: {user_profile.age}岁, {user_profile.gender}, {user_profile.zodiac_sign}")
    print("\n开始占卜...")
    
    start_time = time.time()
    
    try:
        result = await service.create_reading(
            question=question,
            user_id=None,
            user_selected_spread=None,
            user_profile=user_profile,
            use_rag_for_pattern=False,
            preferred_source="pkt"  # 使用pkt数据源
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        elapsed_seconds = elapsed_ms / 1000
        
        print(f"\n✅ 完整占卜流程完成")
        print(f"总耗时: {elapsed_seconds:.2f}秒 ({elapsed_ms}ms)")
        
        # 提取RAG查询信息 - 从数据库读取
        supabase = get_supabase_service()
        
        # 从reading_process_data表读取RAG查询信息
        rag_queries = []
        if result.get('reading_id'):
            # 查找rag_retrieval步骤的记录，rag_queries是直接字段
            process_data = supabase.table('reading_process_data').select('*').eq('reading_id', result['reading_id']).eq('step_name', 'rag_retrieval').execute()
            if process_data.data:
                for record in process_data.data:
                    if record.get('rag_queries'):
                        rag_queries.extend(record['rag_queries'])
            
            # 如果还没有找到，尝试从所有步骤中查找rag_queries字段
            if not rag_queries:
                all_process_data = supabase.table('reading_process_data').select('*').eq('reading_id', result['reading_id']).execute()
                for record in all_process_data.data:
                    if record.get('rag_queries'):
                        rag_queries.extend(record['rag_queries'])
        
        # 分析RAG重复率
        if rag_queries:
            analysis = analyze_rag_duplicates(rag_queries)
            
            print(f"\n" + "="*80)
            print("RAG重复率分析")
            print("="*80)
            print(f"总查询数: {analysis['total_queries']}")
            print(f"唯一文档块数: {analysis['total_unique_chunks']}")
            print(f"文档块总使用次数: {analysis['total_chunk_uses']}")
            print(f"重复使用的文档块数: {analysis['duplicate_count']}")
            print(f"重复使用次数: {analysis['duplicate_uses']}")
            print(f"重复率: {analysis['duplicate_rate']:.2f}%")
            
            # 显示最严重的重复chunks
            if analysis['duplicate_chunks']:
                print(f"\n重复使用的文档块 (前10个):")
                sorted_duplicates = sorted(
                    analysis['duplicate_chunks'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
                for chunk_id, count in sorted_duplicates:
                    print(f"  - {chunk_id}: 被{count}个查询使用")
            
            # 显示查询类型统计
            query_types = Counter()
            for query_info in analysis['query_to_chunks'].values():
                query_types[query_info['type']] += 1
            
            print(f"\n查询类型统计:")
            for query_type, count in query_types.most_common():
                print(f"  - {query_type}: {count}个查询")
        else:
            print("\n⚠️ 未找到RAG查询信息")
            analysis = None
        
        # 保存结果
        result_file = Path(__file__).parent / "result" / f"rag_optimization_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_file.parent.mkdir(exist_ok=True)
        
        output = {
            'question': question,
            'user_profile': user_profile.dict() if hasattr(user_profile, 'dict') else str(user_profile),
            'total_time_ms': elapsed_ms,
            'total_time_seconds': elapsed_seconds,
            'rag_analysis': analysis,
            'reading_result': {
                'reading_id': result.get('reading_id'),
                'spread_type': result.get('spread_type'),
                'question_analysis': result.get('question_analysis'),
                'cards_count': len(result.get('cards', [])),
                'pattern_analysis_method': result.get('metadata', {}).get('pattern_analysis_method'),
            }
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到: {result_file}")
        
        return result, analysis, elapsed_ms
        
    except Exception as e:
        print(f"\n❌ 完整占卜流程失败: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


if __name__ == "__main__":
    asyncio.run(test_optimized_reading())

