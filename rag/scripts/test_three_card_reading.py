#!/usr/bin/env python3
"""
测试三张牌占卜的RAG查询功能
模拟一个真实的占卜场景并检查RAG系统是否能正确回答
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.services.rag import rag_service
from app.services.rag_database import rag_db


async def test_three_card_reading():
    """测试三张牌占卜场景"""
    print("=" * 80)
    print("三张牌占卜 RAG 测试")
    print("=" * 80)
    
    # 模拟三张牌占卜
    question = "我最近的工作发展会如何？"
    cards = [
        {"name": "The Fool", "position": "过去", "is_reversed": False},
        {"name": "The Magician", "position": "现在", "is_reversed": False},
        {"name": "The Star", "position": "未来", "is_reversed": False},
    ]
    
    print(f"\n📋 占卜问题: {question}")
    print(f"\n🎴 三张牌:")
    for i, card in enumerate(cards, 1):
        print(f"   {i}. {card['name']} - {card['position']} (正位)" if not card['is_reversed'] else f"   {i}. {card['name']} - {card['position']} (逆位)")
    
    print("\n" + "-" * 80)
    print("开始查询每张牌的含义...")
    print("-" * 80)
    
    interpretations = []
    sources_used = set()
    
    for i, card in enumerate(cards, 1):
        print(f"\n🔍 查询 {i}/3: {card['name']}")
        print("-" * 60)
        
        # 构建查询：针对每张牌的含义
        query = f"{card['name']}这张牌的含义是什么？{'如果是逆位' if card['is_reversed'] else '如果是正位'}，它在{card['position']}位置时代表什么？"
        
        try:
            result = await rag_service.answer_query(query, top_k=5)
            
            if result:
                answer = result.get('text', '')
                citations = result.get('citations', [])
                debug = result.get('debug', {})
                
                # 收集来源信息
                for citation in citations:
                    sources_used.add(citation.get('source', 'unknown'))
                
                print(f"✅ 查询成功")
                print(f"\n📝 回答预览:")
                print(f"   {answer[:200]}...")
                
                print(f"\n📚 引用信息 ({len(citations)} 个):")
                for j, citation in enumerate(citations[:3], 1):
                    source = citation.get('source', 'unknown')
                    similarity = citation.get('similarity', 0.0)
                    print(f"   {j}. 来源: {source}")
                    print(f"      相似度: {similarity:.4f}")
                    print(f"      Chunk ID: {citation.get('chunk_id', 'N/A')[:50]}...")
                
                print(f"\n🔍 调试信息:")
                print(f"   处理时间: {debug.get('latency_ms', 0)}ms")
                print(f"   检索到的块数: {debug.get('num_results', 0)}")
                
                interpretations.append({
                    'card': card['name'],
                    'position': card['position'],
                    'interpretation': answer,
                    'citations': citations
                })
            else:
                print("❌ 查询返回空结果")
                interpretations.append({
                    'card': card['name'],
                    'position': card['position'],
                    'interpretation': "无法获取解释",
                    'citations': []
                })
                
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()
            interpretations.append({
                'card': card['name'],
                'position': card['position'],
                'interpretation': f"查询失败: {str(e)}",
                'citations': []
            })
    
    # 测试整体解读
    print("\n" + "=" * 80)
    print("生成整体解读...")
    print("=" * 80)
    
    overall_query = f"关于'{question}'这个问题，这三张牌（{', '.join([c['name'] for c in cards])}）组合在一起的含义是什么？"
    print(f"\n🔍 整体查询: {overall_query}")
    
    try:
        overall_result = await rag_service.answer_query(overall_query, top_k=6)
        
        if overall_result:
            print(f"\n✅ 整体解读成功")
            print(f"\n📝 解读:")
            print(f"   {overall_result['text']}")
            
            print(f"\n📚 引用来源 ({len(overall_result['citations'])} 个):")
            overall_sources = set()
            for citation in overall_result['citations']:
                source = citation.get('source', 'unknown')
                overall_sources.add(source)
                print(f"   - {source} (相似度: {citation.get('similarity', 0):.4f})")
            
            sources_used.update(overall_sources)
        else:
            print("❌ 整体解读返回空结果")
            
    except Exception as e:
        print(f"❌ 整体解读失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"\n📊 使用的数据源:")
    for source in sorted(sources_used):
        print(f"   - {source}")
    
    print(f"\n✅ 数据源混合使用:")
    if len(sources_used) > 1:
        print(f"   是！RAG系统成功从 {len(sources_used)} 个数据源检索信息")
    elif len(sources_used) == 1:
        print(f"   当前只使用了 1 个数据源")
    else:
        print(f"   ⚠️  没有找到任何数据源")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)
    
    return interpretations


async def test_data_source_separation():
    """测试数据源分离功能（可选）"""
    print("\n" + "=" * 80)
    print("数据源分离测试")
    print("=" * 80)
    
    query = "The Fool这张牌的含义是什么？"
    
    print(f"\n查询: {query}")
    print("-" * 60)
    
    # 测试不指定source（应该返回所有来源）
    print("\n1. 查询所有来源（默认）:")
    try:
        result_all = await rag_service.answer_query(query, top_k=10)
        sources_found = set()
        for citation in result_all.get('citations', []):
            sources_found.add(citation.get('source', 'unknown'))
        
        print(f"   ✅ 找到 {len(result_all.get('citations', []))} 个相关块")
        print(f"   📚 数据源: {', '.join(sorted(sources_found))}")
    except Exception as e:
        print(f"   ❌ 查询失败: {e}")
    
    # 查看数据库统计
    print("\n2. 数据库统计信息:")
    try:
        stats = await rag_db.get_stats()
        print(f"   ✅ 总块数: {stats.get('total_chunks', 0)}")
        print(f"   ✅ 唯一来源数: {stats.get('unique_sources', 0)}")
    except Exception as e:
        print(f"   ❌ 获取统计失败: {e}")


async def main():
    """主函数"""
    print("\n🔮 开始三张牌占卜 RAG 测试\n")
    
    # 测试数据库连接
    print("1. 检查数据库连接...")
    try:
        stats = await rag_db.get_stats()
        print(f"   ✅ 数据库连接正常")
        print(f"   📊 总块数: {stats.get('total_chunks', 0)}")
        print(f"   📚 唯一来源: {stats.get('unique_sources', 0)}")
    except Exception as e:
        print(f"   ❌ 数据库连接失败: {e}")
        return
    
    # 运行三张牌占卜测试
    print("\n2. 运行三张牌占卜测试...")
    await test_three_card_reading()
    
    # 测试数据源分离
    print("\n3. 测试数据源信息...")
    await test_data_source_separation()


if __name__ == "__main__":
    asyncio.run(main())

