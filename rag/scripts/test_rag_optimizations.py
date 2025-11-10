#!/usr/bin/env python3
"""
测试优化后的RAG系统：延迟优化和数据源平衡
"""

import asyncio
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.services.rag import rag_service


async def test_optimizations():
    """测试优化效果"""
    print("=" * 80)
    print("RAG 优化测试")
    print("=" * 80)
    
    test_queries = [
        "The Fool这张牌的含义是什么？",
        "The Magician的含义",
        "The Star在爱情中的含义",
    ]
    
    print("\n📊 测试1: 延迟优化（Embedding缓存）")
    print("-" * 80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n查询 {i}: {query}")
        
        # 第一次查询（无缓存）
        start = time.time()
        result1 = await rag_service.answer_query(query, balance_sources=True)
        time1 = (time.time() - start) * 1000
        
        # 第二次查询（有缓存）
        start = time.time()
        result2 = await rag_service.answer_query(query, balance_sources=True)
        time2 = (time.time() - start) * 1000
        
        print(f"  第一次（无缓存）: {time1:.0f}ms")
        print(f"  第二次（有缓存）: {time2:.0f}ms")
        print(f"  速度提升: {time1 - time2:.0f}ms ({(time1/time2 - 1) * 100:.0f}%)")
        
        # 检查数据源
        sources = set()
        for citation in result1.get('citations', []):
            sources.add(citation.get('source', 'unknown'))
        
        print(f"  使用的数据源: {', '.join(sorted(sources))}")
        print(f"  数据源数量: {len(sources)}")
    
    print("\n📊 测试2: 数据源平衡")
    print("-" * 80)
    
    query = "The Fool这张牌的含义是什么？"
    
    # 测试不带平衡的搜索
    print("\n🔍 不带平衡搜索:")
    result_unbalanced = await rag_service.answer_query(
        query, 
        balance_sources=False,
        top_k=6
    )
    sources_unbalanced = {}
    for citation in result_unbalanced.get('citations', []):
        source = citation.get('source', 'unknown')
        sources_unbalanced[source] = sources_unbalanced.get(source, 0) + 1
    
    print(f"  数据源分布:")
    for source, count in sources_unbalanced.items():
        print(f"    {source}: {count} 个结果")
    
    # 测试带平衡的搜索
    print("\n🔍 带平衡搜索:")
    result_balanced = await rag_service.answer_query(
        query, 
        balance_sources=True,
        top_k=6
    )
    sources_balanced = {}
    for citation in result_balanced.get('citations', []):
        source = citation.get('source', 'unknown')
        sources_balanced[source] = sources_balanced.get(source, 0) + 1
    
    print(f"  数据源分布:")
    for source, count in sources_balanced.items():
        print(f"    {source}: {count} 个结果")
    
    if len(sources_balanced) > len(sources_unbalanced):
        print(f"  ✅ 平衡搜索成功使用了 {len(sources_balanced)} 个数据源")
    elif len(sources_balanced) == len(sources_unbalanced):
        print(f"  ℹ️  两个搜索都使用了 {len(sources_balanced)} 个数据源")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_optimizations())

