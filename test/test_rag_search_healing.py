#!/usr/bin/env python3
"""
RAG搜索测试脚本 - 搜索塔罗牌心理疗愈与冥想相关内容
运行: python3 test/test_rag_search_healing.py
"""

import asyncio
import sys
import json
from datetime import datetime
from pathlib import Path

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.rag import rag_service
from app.services.rag_database import rag_db
from app.core.config import settings


async def search_healing_meditation():
    """搜索塔罗牌心理疗愈与冥想相关内容"""
    print("\n" + "="*80)
    print("RAG搜索: 使用塔罗牌进行心理疗愈与冥想的步骤")
    print("="*80)
    
    # 1. 测试数据库连接
    print("\n1. 检查数据库连接...")
    try:
        health = await rag_db.health_check()
        if not health:
            print("❌ 数据库连接失败")
            return
        print("✅ 数据库连接成功")
    except Exception as e:
        print(f"❌ 数据库连接错误: {e}")
        return
    
    # 2. 检查数据库统计
    print("\n2. 检查数据库内容...")
    try:
        stats = await rag_service.get_stats()
        if stats:
            total_chunks = stats.get('total_chunks', 0)
            print(f"📊 数据库中有 {total_chunks} 个chunks")
            if total_chunks == 0:
                print("⚠️  警告: 数据库为空，需要先上传文档")
                return
        else:
            print("⚠️  无法获取统计信息")
    except Exception as e:
        print(f"❌ 获取统计信息失败: {e}")
        return
    
    # 3. 执行搜索
    print("\n3. 执行RAG搜索...")
    query = "steps for using tarot cards for psychological healing and meditation"
    print(f"查询: {query}")
    print("-" * 80)
    
    try:
        # 使用 search_only 方法，只返回相关文档，不生成答案
        result = await rag_service.search_only(
            query=query,
            top_k=10,  # 获取更多结果
            balance_sources=True,
            min_similarity=0.25  # 降低相似度阈值以获取更多相关结果
        )
        
        if not result:
            print("❌ 搜索返回空结果")
            return
        
        chunks = result.get('chunks', [])
        citations = result.get('citations', [])
        debug = result.get('debug', {})
        
        print(f"\n✅ 搜索成功！")
        print(f"📊 找到 {len(chunks)} 个相关文档块")
        print(f"⏱️  搜索延迟: {debug.get('latency_ms', 0)}ms")
        
        if not chunks:
            print("\n⚠️  未找到相关文档，可能的原因：")
            print("   - 数据库中不包含心理疗愈或冥想相关的内容")
            print("   - 尝试降低相似度阈值或使用不同的关键词")
            return
        
        # 4. 显示搜索结果
        print("\n" + "="*80)
        print("搜索结果详情:")
        print("="*80)
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n【结果 {i}】")
            print(f"来源: {chunk.get('source', 'unknown')}")
            print(f"相似度: {chunk.get('similarity', 0):.4f}")
            print(f"Chunk ID: {chunk.get('chunk_id', 'N/A')}")
            print(f"\n内容:")
            print("-" * 80)
            text = chunk.get('text', '')
            # 显示前500个字符，如果内容更长则截断
            if len(text) > 500:
                print(text[:500] + "...")
                print(f"\n[内容已截断，完整长度: {len(text)} 字符]")
            else:
                print(text)
            print("-" * 80)
        
        # 5. 按来源分组统计
        print("\n" + "="*80)
        print("按来源统计:")
        print("="*80)
        sources = {}
        for chunk in chunks:
            source = chunk.get('source', 'unknown')
            if source not in sources:
                sources[source] = []
            sources[source].append(chunk)
        
        for source, source_chunks in sources.items():
            avg_similarity = sum(c.get('similarity', 0) for c in source_chunks) / len(source_chunks)
            print(f"\n{source}:")
            print(f"  - 结果数: {len(source_chunks)}")
            print(f"  - 平均相似度: {avg_similarity:.4f}")
        
        # 6. 保存结果到文件
        result_dir = project_root / "test" / "result"
        result_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = int(datetime.now().timestamp())
        output_file = result_dir / f"rag_search_healing_{timestamp}.json"
        
        # 准备保存的数据
        save_data = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "search_stats": {
                "total_chunks": len(chunks),
                "latency_ms": debug.get('latency_ms', 0),
                "sources": {
                    source: {
                        "count": len(source_chunks),
                        "avg_similarity": sum(c.get('similarity', 0) for c in source_chunks) / len(source_chunks)
                    }
                    for source, source_chunks in sources.items()
                }
            },
            "chunks": [
                {
                    "index": i + 1,
                    "source": chunk.get('source', 'unknown'),
                    "chunk_id": chunk.get('chunk_id', 'N/A'),
                    "similarity": chunk.get('similarity', 0),
                    "text": chunk.get('text', ''),
                    "metadata": chunk.get('metadata', {})
                }
                for i, chunk in enumerate(chunks)
            ],
            "citations": citations,
            "debug": debug
        }
        
        # 保存到JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*80)
        print("✅ 搜索完成！")
        print(f"📁 结果已保存到: {output_file}")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n配置信息:")
    print(f"  - Supabase URL: {settings.supabase_url[:50] if settings.supabase_url else 'Not set'}...")
    print(f"  - 使用 OpenRouter: {settings.use_openrouter}")
    print(f"  - RAG Top K: {settings.rag_top_k}")
    
    asyncio.run(search_healing_meditation())

