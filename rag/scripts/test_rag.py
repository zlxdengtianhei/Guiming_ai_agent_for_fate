#!/usr/bin/env python3
"""
测试 RAG 系统是否正常工作
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
# 脚本位于 rag/scripts/，需要向上两级到达项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.services.rag import rag_service

async def test_rag():
    """测试 RAG 查询功能"""
    print("=" * 60)
    print("RAG 系统测试")
    print("=" * 60)
    
    # 测试查询
    test_queries = [
        "The Fool 这张牌的含义是什么？",
        "What is the meaning of The Magician?",
        "塔罗牌中的大阿卡纳是什么？",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. 测试查询: {query}")
        print("-" * 60)
        
        try:
            result = await rag_service.answer_query(query, top_k=3)
            
            print(f"✅ 查询成功")
            print(f"\n📝 回答:")
            print(f"   {result['text'][:300]}...")
            
            print(f"\n📚 引用 ({len(result['citations'])} 个):")
            for j, citation in enumerate(result['citations'][:3], 1):
                print(f"   {j}. {citation['chunk_id']} (相似度: {citation['similarity']:.4f})")
                print(f"      来源: {citation['source']}")
            
            print(f"\n🔍 调试信息:")
            print(f"   处理时间: {result['debug']['latency_ms']}ms")
            print(f"   检索到的块数: {result['debug']['num_results']}")
            print(f"   前几个文档 ID: {result['debug']['top_doc_ids'][:3]}")
            
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_rag())

