#!/usr/bin/env python3
"""
全面的RAG系统测试脚本
测试RAG系统的各个组件和功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加backend目录到路径
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.services.rag import rag_service
from app.services.rag_database import rag_db
from app.services.embedding import embedding_service
from app.core.config import settings


async def test_database_connection():
    """测试1: 数据库连接"""
    print("\n" + "="*60)
    print("测试 1: 数据库连接")
    print("="*60)
    
    try:
        health = await rag_db.health_check()
        if health:
            print("✅ 数据库连接成功")
            return True
        else:
            print("❌ 数据库连接失败")
            return False
    except Exception as e:
        print(f"❌ 数据库连接错误: {e}")
        return False


async def test_database_stats():
    """测试2: 数据库统计信息"""
    print("\n" + "="*60)
    print("测试 2: 数据库统计信息")
    print("="*60)
    
    try:
        stats = await rag_service.get_stats()
        if stats:
            print(f"📊 数据库统计:")
            print(f"  - 总chunks数: {stats.get('total_chunks', 0)}")
            print(f"  - 唯一来源数: {stats.get('unique_sources', 0)}")
            print(f"  - 最新chunk: {stats.get('latest_chunk', 'N/A')}")
            
            if stats.get('total_chunks', 0) == 0:
                print("⚠️  警告: 数据库中没有任何chunks，需要先上传文档")
                return False
            return True
        else:
            print("⚠️  无法获取统计信息")
            return False
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")
        return False


async def test_embedding_service():
    """测试3: 嵌入服务"""
    print("\n" + "="*60)
    print("测试 3: 嵌入服务")
    print("="*60)
    
    try:
        test_text = "The Fool is the first card in the Major Arcana."
        print(f"测试文本: {test_text}")
        
        embedding = await embedding_service.embed_query(test_text)
        
        if embedding and len(embedding) == 1536:
            print(f"✅ 嵌入生成成功")
            print(f"  - 维度: {len(embedding)}")
            print(f"  - 前5个值: {embedding[:5]}")
            return True
        else:
            print(f"❌ 嵌入维度错误: 期望1536，实际{len(embedding) if embedding else 0}")
            return False
    except Exception as e:
        print(f"❌ 嵌入生成失败: {e}")
        print(f"   检查配置:")
        print(f"   - USE_OPENROUTER: {settings.use_openrouter}")
        print(f"   - 模型: {settings.openai_embed_model}")
        return False


async def test_vector_search():
    """测试4: 向量搜索"""
    print("\n" + "="*60)
    print("测试 4: 向量搜索")
    print("="*60)
    
    try:
        # 生成查询嵌入
        query = "The Fool card meaning"
        print(f"查询: {query}")
        
        query_embedding = await embedding_service.embed_query(query)
        print(f"✅ 查询嵌入生成成功")
        
        # 执行向量搜索
        results = await rag_db.vector_search(
            query_embedding,
            top_k=3,
            min_similarity=0.3
        )
        
        if results:
            print(f"✅ 找到 {len(results)} 个相关结果:")
            for i, result in enumerate(results, 1):
                similarity = result.get('similarity', 0)
                chunk_id = result.get('chunk_id', 'N/A')
                text_preview = result.get('text', '')[:100] + "..."
                print(f"\n  结果 {i}:")
                print(f"    - 相似度: {similarity:.3f}")
                print(f"    - Chunk ID: {chunk_id}")
                print(f"    - 文本预览: {text_preview}")
            return True
        else:
            print("⚠️  没有找到相关结果")
            print("   可能原因:")
            print("   1. 数据库中没有数据")
            print("   2. 相似度阈值过高")
            print("   3. 查询与现有内容不匹配")
            return False
            
    except Exception as e:
        print(f"❌ 向量搜索失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_rag_query():
    """测试5: 完整的RAG查询"""
    print("\n" + "="*60)
    print("测试 5: 完整的RAG查询")
    print("="*60)
    
    test_queries = [
        "The Fool这张牌的含义是什么？",
        "凯尔特占卜法如何使用？",
        "权杖国王（King of Wands）的含义",
        "The High Priestess在爱情中的含义"
    ]
    
    results = []
    
    for query in test_queries:
        print(f"\n查询: {query}")
        try:
            result = await rag_service.answer_query(query, top_k=3)
            
            if result:
                answer = result.get('text', '')
                citations = result.get('citations', [])
                debug = result.get('debug', {})
                
                print(f"✅ 查询成功")
                print(f"  答案长度: {len(answer)} 字符")
                print(f"  引用数: {len(citations)}")
                print(f"  延迟: {debug.get('latency_ms', 0)}ms")
                print(f"\n  答案预览:")
                print(f"  {answer[:200]}...")
                
                if citations:
                    print(f"\n  引用:")
                    for i, cite in enumerate(citations[:2], 1):
                        print(f"    {i}. {cite.get('source', 'N/A')} (相似度: {cite.get('similarity', 0):.3f})")
                
                results.append(True)
            else:
                print("❌ 查询返回空结果")
                results.append(False)
                
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            results.append(False)
    
    success_count = sum(results)
    print(f"\n📊 测试结果: {success_count}/{len(test_queries)} 成功")
    
    return success_count == len(test_queries)


async def test_edge_cases():
    """测试6: 边界情况"""
    print("\n" + "="*60)
    print("测试 6: 边界情况")
    print("="*60)
    
    edge_cases = [
        ("空查询", ""),
        ("非常长的查询", "The " * 1000),
        ("不相关查询", "今天天气怎么样？"),
        ("英文查询", "What is the meaning of The Fool card?"),
    ]
    
    results = []
    
    for name, query in edge_cases:
        print(f"\n测试: {name}")
        try:
            result = await rag_service.answer_query(query, top_k=3)
            
            if result:
                answer = result.get('text', '')
                if answer and "don't have enough information" not in answer.lower():
                    print(f"✅ 处理成功")
                    results.append(True)
                else:
                    print(f"⚠️  返回了默认消息（可能没有相关信息）")
                    results.append(True)  # 这也是合理的响应
            else:
                print(f"❌ 返回空结果")
                results.append(False)
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            results.append(False)
    
    success_count = sum(results)
    print(f"\n📊 边界测试结果: {success_count}/{len(edge_cases)} 成功")
    
    return success_count == len(edge_cases)


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("RAG系统全面测试")
    print("="*60)
    print(f"\n配置信息:")
    print(f"  - Supabase URL: {settings.supabase_url[:30]}...")
    print(f"  - 使用 OpenRouter: {settings.use_openrouter}")
    print(f"  - 嵌入模型: {settings.openai_embed_model}")
    print(f"  - Chat模型: {settings.openai_chat_model}")
    print(f"  - RAG Top K: {settings.rag_top_k}")
    
    # 运行所有测试
    tests = [
        ("数据库连接", test_database_connection),
        ("数据库统计", test_database_stats),
        ("嵌入服务", test_embedding_service),
        ("向量搜索", test_vector_search),
        ("RAG查询", test_rag_query),
        ("边界情况", test_edge_cases),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n❌ 测试 '{test_name}' 出现异常: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\n总计: {passed_tests}/{total_tests} 测试通过")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！RAG系统运行正常。")
        return 0
    else:
        print(f"\n⚠️  有 {total_tests - passed_tests} 个测试失败，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

