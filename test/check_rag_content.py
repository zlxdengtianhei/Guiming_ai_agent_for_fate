#!/usr/bin/env python3
"""
检查RAG数据库中的内容分布
"""

import asyncio
from app.services.rag_database import rag_db
from app.core.config import settings


async def check_content():
    """检查数据库内容"""
    print("\n" + "="*60)
    print("RAG数据库内容检查")
    print("="*60)
    
    # 获取统计信息
    stats = await rag_db.get_stats()
    print(f"\n📊 总体统计:")
    print(f"  - 总chunks数: {stats.get('total_chunks', 0)}")
    print(f"  - 唯一来源数: {stats.get('unique_sources', 0)}")
    
    # 获取数据库客户端
    client = rag_db.get_client(admin=True)
    
    # 查询所有唯一的sources
    print(f"\n📚 文档来源:")
    try:
        result = client.table('rag_chunks').select('source').execute()
        
        sources = {}
        for row in result.data:
            source = row.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
        
        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {source}: {count} chunks")
    
    except Exception as e:
        print(f"❌ 查询来源失败: {e}")
    
    # 查询一些示例chunks
    print(f"\n📄 示例内容（前5个chunks）:")
    try:
        result = client.table('rag_chunks').select('chunk_id, source, text').limit(5).execute()
        
        for i, chunk in enumerate(result.data, 1):
            chunk_id = chunk.get('chunk_id', 'N/A')
            source = chunk.get('source', 'N/A')
            text_preview = chunk.get('text', '')[:100] + "..."
            print(f"\n  {i}. Chunk ID: {chunk_id}")
            print(f"     来源: {source}")
            print(f"     内容预览: {text_preview}")
    
    except Exception as e:
        print(f"❌ 查询示例失败: {e}")
    
    # 检查是否有占卜方法相关内容
    print(f"\n🔍 搜索占卜方法相关内容:")
    try:
        # 搜索包含"divination"或"method"的chunks
        result = client.table('rag_chunks').select('chunk_id, source, text').execute()
        
        divination_chunks = []
        for chunk in result.data:
            text = chunk.get('text', '').lower()
            if any(keyword in text for keyword in ['divination', 'method', 'celtic', 'spread', 'layout']):
                divination_chunks.append(chunk)
        
        if divination_chunks:
            print(f"  ✅ 找到 {len(divination_chunks)} 个相关chunks")
            print(f"  示例:")
            for chunk in divination_chunks[:3]:
                print(f"    - {chunk.get('chunk_id', 'N/A')}: {chunk.get('text', '')[:80]}...")
        else:
            print(f"  ⚠️  没有找到占卜方法相关内容")
            print(f"  建议: 检查是否需要上传占卜方法部分的文档")
    
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(check_content())

