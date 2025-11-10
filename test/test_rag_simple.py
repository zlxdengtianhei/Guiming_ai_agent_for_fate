#!/usr/bin/env python3
"""
简单的RAG系统测试脚本
在test目录下运行: python3 test_rag_simple.py
"""

import asyncio
import sys
from pathlib import Path

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.rag import rag_service
from app.services.rag_database import rag_db
from app.services.embedding import embedding_service
from app.core.config import settings


async def test_basic():
    """基础测试"""
    print("\n" + "="*60)
    print("RAG系统基础测试")
    print("="*60)
    
    # 1. 测试数据库连接
    print("\n1. 测试数据库连接...")
    try:
        health = await rag_db.health_check()
        if health:
            print("✅ 数据库连接成功")
        else:
            print("❌ 数据库连接失败")
            return
    except Exception as e:
        print(f"❌ 数据库连接错误: {e}")
        return
    
    # 2. 测试数据库统计
    print("\n2. 检查数据库内容...")
    try:
        stats = await rag_service.get_stats()
        if stats:
            total_chunks = stats.get('total_chunks', 0)
            print(f"📊 数据库中有 {total_chunks} 个chunks")
            if total_chunks == 0:
                print("⚠️  警告: 数据库为空，需要先上传文档")
                print("   运行: python3 rag/scripts/upload_to_supabase.py")
                return
        else:
            print("⚠️  无法获取统计信息")
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")
        return
    
    # 3. 测试嵌入服务
    print("\n3. 测试嵌入服务...")
    try:
        test_text = "The Fool is the first card"
        embedding = await embedding_service.embed_query(test_text)
        if embedding and len(embedding) == 1536:
            print(f"✅ 嵌入生成成功 (维度: {len(embedding)})")
        else:
            print(f"❌ 嵌入维度错误")
            return
    except Exception as e:
        print(f"❌ 嵌入生成失败: {e}")
        print(f"   检查配置:")
        print(f"   - USE_OPENROUTER: {settings.use_openrouter}")
        print(f"   - OPENROUTER_API_KEY: {'已设置' if settings.openrouter_api_key else '未设置'}")
        print(f"   - OPENAI_API_KEY: {'已设置' if settings.openai_api_key else '未设置'}")
        return
    
    # 4. 测试RAG查询
    print("\n4. 测试RAG查询...")
    test_queries = [
        "The Fool这张牌的含义是什么？",
        "凯尔特占卜法如何使用？",
    ]
    
    for query in test_queries:
        print(f"\n查询: {query}")
        try:
            result = await rag_service.answer_query(query, top_k=3)
            
            if result:
                answer = result.get('text', '')
                citations = result.get('citations', [])
                debug = result.get('debug', {})
                
                print(f"✅ 查询成功")
                print(f"  答案预览: {answer[:150]}...")
                print(f"  引用数: {len(citations)}")
                print(f"  延迟: {debug.get('latency_ms', 0)}ms")
                
                if citations:
                    print(f"  相似度: {citations[0].get('similarity', 0):.3f}")
            else:
                print("❌ 查询返回空结果")
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ 测试完成！")
    print("="*60)


if __name__ == "__main__":
    print("\n配置信息:")
    print(f"  - Supabase URL: {settings.supabase_url[:30] if settings.supabase_url else 'Not set'}...")
    print(f"  - 使用 OpenRouter: {settings.use_openrouter}")
    print(f"  - 嵌入模型: {settings.openai_embed_model}")
    print(f"  - Chat模型: {settings.openai_chat_model}")
    
    asyncio.run(test_basic())

