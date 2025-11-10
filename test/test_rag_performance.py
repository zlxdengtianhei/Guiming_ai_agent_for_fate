"""
RAG性能分析测试脚本
分析RAG查询各步骤的耗时，找出性能瓶颈
"""

import asyncio
import time
import json
import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.rag import rag_service
from app.services.embedding import embedding_service
from app.services.rag_database import rag_db
from app.services.chat import chat_service


async def test_embedding_performance():
    """测试embedding生成性能"""
    print("\n=== Embedding性能测试 ===")
    
    query = "Four of Cups tarot card meaning divinatory meaning"
    
    # 测试1: 首次生成（无缓存）
    start = time.time()
    embedding1 = await embedding_service.embed_query(query)
    time1 = (time.time() - start) * 1000
    print(f"首次embedding生成: {time1:.2f}ms")
    
    # 测试2: 第二次生成（应该使用缓存）
    start = time.time()
    embedding2 = await rag_service._get_cached_embedding(query)
    time2 = (time.time() - start) * 1000
    print(f"缓存embedding获取: {time2:.2f}ms")
    
    # 测试3: 不同查询（无缓存）
    query2 = "Five of Swords tarot card meaning"
    start = time.time()
    embedding3 = await embedding_service.embed_query(query2)
    time3 = (time.time() - start) * 1000
    print(f"不同查询embedding生成: {time3:.2f}ms")
    
    return {
        'first_embedding_ms': time1,
        'cached_embedding_ms': time2,
        'different_query_ms': time3
    }


async def test_vector_search_performance():
    """测试向量搜索性能"""
    print("\n=== 向量搜索性能测试 ===")
    
    query = "Four of Cups tarot card meaning divinatory meaning"
    
    # 生成embedding
    start = time.time()
    embedding = await embedding_service.embed_query(query)
    embedding_time = (time.time() - start) * 1000
    print(f"Embedding生成: {embedding_time:.2f}ms")
    
    # 测试向量搜索
    start = time.time()
    results = await rag_db.vector_search(embedding, top_k=5, min_similarity=0.3)
    search_time = (time.time() - start) * 1000
    print(f"向量搜索: {search_time:.2f}ms")
    print(f"返回结果数: {len(results)}")
    
    # 测试平衡搜索
    start = time.time()
    balanced_results = await rag_service._balanced_vector_search(embedding, top_k=5, min_similarity=0.3)
    balanced_time = (time.time() - start) * 1000
    print(f"平衡向量搜索: {balanced_time:.2f}ms")
    print(f"返回结果数: {len(balanced_results)}")
    
    return {
        'embedding_ms': embedding_time,
        'vector_search_ms': search_time,
        'balanced_search_ms': balanced_time,
        'num_results': len(results)
    }


async def test_llm_generation_performance():
    """测试LLM生成性能"""
    print("\n=== LLM生成性能测试 ===")
    
    query = "Four of Cups tarot card meaning divinatory meaning"
    
    # 先获取context
    embedding = await embedding_service.embed_query(query)
    context_blocks = await rag_db.vector_search(embedding, top_k=5, min_similarity=0.3)
    
    # 准备context
    formatted_blocks = [
        {
            'chunk_id': r.get('chunk_id', ''),
            'text': r.get('text', ''),
            'source': r.get('source', ''),
            'similarity': r.get('similarity', 0.0),
            'metadata': r.get('metadata', {})
        }
        for r in context_blocks
    ]
    
    # 测试LLM生成
    start = time.time()
    answer = await chat_service.generate_answer(query, formatted_blocks)
    llm_time = (time.time() - start) * 1000
    print(f"LLM生成答案: {llm_time:.2f}ms")
    print(f"答案长度: {len(answer)} 字符")
    
    return {
        'llm_generation_ms': llm_time,
        'answer_length': len(answer)
    }


async def test_full_rag_query_performance():
    """测试完整RAG查询性能"""
    print("\n=== 完整RAG查询性能测试 ===")
    
    query = "Four of Cups tarot card meaning divinatory meaning"
    
    # 测试完整RAG查询
    start = time.time()
    result = await rag_service.answer_query(query, top_k=5)
    total_time = (time.time() - start) * 1000
    
    print(f"完整RAG查询总耗时: {total_time:.2f}ms")
    print(f"Debug信息: {result.get('debug', {})}")
    
    # 分解时间
    debug = result.get('debug', {})
    latency_ms = debug.get('latency_ms', 0)
    print(f"RAG服务报告的latency: {latency_ms}ms")
    
    return {
        'total_time_ms': total_time,
        'reported_latency_ms': latency_ms,
        'num_results': debug.get('num_results', 0)
    }


async def test_parallel_rag_queries():
    """测试并行RAG查询性能"""
    print("\n=== 并行RAG查询性能测试 ===")
    
    queries = [
        "Four of Cups tarot card meaning divinatory meaning",
        "Five of Swords tarot card meaning divinatory meaning",
        "King of Pentacles tarot card meaning divinatory meaning",
        "three_card spread tarot divination method how to use steps",
        "tarot card number patterns same numbers sequences in spread"
    ]
    
    # 串行执行
    print("串行执行:")
    start = time.time()
    serial_results = []
    for q in queries:
        result = await rag_service.answer_query(q, top_k=5)
        serial_results.append(result)
    serial_time = (time.time() - start) * 1000
    print(f"串行总耗时: {serial_time:.2f}ms")
    print(f"平均每个查询: {serial_time / len(queries):.2f}ms")
    
    # 并行执行
    print("\n并行执行:")
    start = time.time()
    parallel_tasks = [rag_service.answer_query(q, top_k=5) for q in queries]
    parallel_results = await asyncio.gather(*parallel_tasks)
    parallel_time = (time.time() - start) * 1000
    print(f"并行总耗时: {parallel_time:.2f}ms")
    print(f"平均每个查询: {parallel_time / len(queries):.2f}ms")
    print(f"性能提升: {(serial_time - parallel_time) / serial_time * 100:.1f}%")
    
    return {
        'serial_time_ms': serial_time,
        'parallel_time_ms': parallel_time,
        'speedup': serial_time / parallel_time if parallel_time > 0 else 0
    }


async def main():
    """主测试函数"""
    print("=" * 60)
    print("RAG性能分析测试")
    print("=" * 60)
    
    results = {}
    
    try:
        # 1. Embedding性能测试
        results['embedding'] = await test_embedding_performance()
        
        # 2. 向量搜索性能测试
        results['vector_search'] = await test_vector_search_performance()
        
        # 3. LLM生成性能测试
        results['llm'] = await test_llm_generation_performance()
        
        # 4. 完整RAG查询性能测试
        results['full_rag'] = await test_full_rag_query_performance()
        
        # 5. 并行RAG查询性能测试
        results['parallel'] = await test_parallel_rag_queries()
        
        # 保存结果
        output_file = Path(__file__).parent / "result" / f"rag_performance_{int(time.time())}.json"
        output_file.parent.mkdir(exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 60)
        print("测试完成！结果已保存到:", output_file)
        print("=" * 60)
        
        # 总结
        print("\n性能总结:")
        print(f"- Embedding生成（首次）: {results['embedding']['first_embedding_ms']:.2f}ms")
        print(f"- Embedding获取（缓存）: {results['embedding']['cached_embedding_ms']:.2f}ms")
        print(f"- 向量搜索: {results['vector_search']['vector_search_ms']:.2f}ms")
        print(f"- LLM生成: {results['llm']['llm_generation_ms']:.2f}ms")
        print(f"- 完整RAG查询: {results['full_rag']['total_time_ms']:.2f}ms")
        print(f"- 并行查询（5个）: {results['parallel']['parallel_time_ms']:.2f}ms")
        print(f"- 并行性能提升: {results['parallel']['speedup']:.2f}x")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())





