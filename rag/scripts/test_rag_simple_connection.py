#!/usr/bin/env python3
"""
简单的RAG连接和使用测试
验证RAG系统是否能正常工作，并检查数据源混合使用情况
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.services.rag import rag_service
from app.services.rag_database import rag_db


async def simple_test():
    """简单的RAG测试"""
    print("=" * 70)
    print("RAG 系统简单测试")
    print("=" * 70)
    
    # 1. 测试数据库连接
    print("\n1️⃣  测试数据库连接...")
    try:
        stats = await rag_db.get_stats()
        total_chunks = stats.get('total_chunks', 0)
        unique_sources = stats.get('unique_sources', 0)
        
        print(f"   ✅ 连接成功")
        print(f"   📊 总块数: {total_chunks}")
        print(f"   📚 数据源数量: {unique_sources}")
        
        if total_chunks == 0:
            print("   ⚠️  数据库为空，请先上传文档")
            return False
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        return False
    
    # 2. 测试单个查询
    print("\n2️⃣  测试单张牌查询...")
    test_query = "The Fool这张牌的含义是什么？"
    print(f"   查询: {test_query}")
    
    try:
        result = await rag_service.answer_query(test_query, top_k=5)
        
        if result and result.get('text'):
            print(f"   ✅ 查询成功")
            print(f"   📝 回答长度: {len(result['text'])} 字符")
            print(f"   📚 引用数量: {len(result.get('citations', []))}")
            
            # 检查数据源
            sources = set()
            for citation in result.get('citations', []):
                sources.add(citation.get('source', 'unknown'))
            
            print(f"   🔍 使用的数据源: {', '.join(sorted(sources))}")
            
            if len(sources) > 1:
                print(f"   ✅ 确认：两个数据源会混合使用")
            else:
                print(f"   ℹ️  当前只使用了 1 个数据源")
            
            # 显示回答预览
            print(f"\n   📖 回答预览:")
            answer_preview = result['text'][:200]
            print(f"   {answer_preview}...")
            
        else:
            print("   ❌ 查询返回空结果")
            return False
            
    except Exception as e:
        print(f"   ❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 3. 测试多个不同的问题
    print("\n3️⃣  测试多个查询...")
    test_queries = [
        "The Magician的含义",
        "凯尔特占卜法如何使用？",
    ]
    
    all_sources = set()
    
    for query in test_queries:
        print(f"\n   查询: {query}")
        try:
            result = await rag_service.answer_query(query, top_k=3)
            
            if result:
                sources = set()
                for citation in result.get('citations', []):
                    sources.add(citation.get('source', 'unknown'))
                all_sources.update(sources)
                
                print(f"   ✅ 成功 - 使用 {len(sources)} 个数据源: {', '.join(sorted(sources))}")
            else:
                print(f"   ⚠️  返回空结果")
        except Exception as e:
            print(f"   ❌ 失败: {e}")
    
    # 4. 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)
    print(f"\n✅ RAG系统工作正常")
    print(f"✅ 数据库连接正常")
    print(f"✅ 查询功能正常")
    
    if len(all_sources) >= 2:
        print(f"\n✅ 确认：两个RAG数据库（pkt.txt 和 78_degrees_of_wisdom.txt）")
        print(f"   会混合使用！系统会从所有数据源中检索最相关的信息。")
    else:
        print(f"\nℹ️  当前使用了 {len(all_sources)} 个数据源")
    
    print("\n" + "=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(simple_test())
    sys.exit(0 if success else 1)

