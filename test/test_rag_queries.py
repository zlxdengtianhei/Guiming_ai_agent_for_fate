#!/usr/bin/env python3
"""
测试不同类型的RAG查询
"""

import asyncio
import sys
from pathlib import Path

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.rag import rag_service


async def test_queries():
    """测试各种查询"""
    print("\n" + "="*60)
    print("RAG查询测试")
    print("="*60)
    
    test_cases = [
        # 中文查询
        ("中文查询 - The Fool", "The Fool这张牌的含义是什么？"),
        ("中文查询 - 占卜方法", "凯尔特占卜法如何使用？"),
        
        # 英文查询
        ("英文查询 - The Fool", "What is the meaning of The Fool card?"),
        ("英文查询 - Divination", "How to use Celtic method of divination?"),
        ("英文查询 - Spread", "What is the Celtic spread layout?"),
        
        # 混合查询
        ("混合查询 - 牌的含义", "The High Priestess在爱情中的含义"),
        ("混合查询 - 占卜", "How to read tarot cards using Celtic method?"),
    ]
    
    results = []
    
    for name, query in test_cases:
        print(f"\n{'='*60}")
        print(f"测试: {name}")
        print(f"查询: {query}")
        print("-"*60)
        
        try:
            result = await rag_service.answer_query(query, top_k=3)
            
            if result:
                answer = result.get('text', '')
                citations = result.get('citations', [])
                debug = result.get('debug', {})
                
                # 检查是否返回了有效答案
                has_info = "don't have enough information" not in answer.lower()
                
                if has_info:
                    print(f"✅ 查询成功 - 找到相关信息")
                    print(f"   答案长度: {len(answer)} 字符")
                    print(f"   引用数: {len(citations)}")
                    print(f"   延迟: {debug.get('latency_ms', 0)}ms")
                    
                    if citations:
                        print(f"   最高相似度: {citations[0].get('similarity', 0):.3f}")
                    
                    print(f"\n   答案预览:")
                    print(f"   {answer[:200]}...")
                    
                    results.append((name, True, "成功"))
                else:
                    print(f"⚠️  查询成功但未找到相关信息")
                    print(f"   返回了默认消息")
                    results.append((name, False, "未找到信息"))
            else:
                print(f"❌ 查询返回空结果")
                results.append((name, False, "空结果"))
                
        except Exception as e:
            print(f"❌ 查询失败: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False, f"错误: {str(e)}"))
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print("="*60)
    
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    
    for name, success, status in results:
        icon = "✅" if success else "❌"
        print(f"{icon} {name}: {status}")
    
    print(f"\n总计: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("\n🎉 所有查询测试通过！")
    else:
        print(f"\n⚠️  有 {total_count - success_count} 个查询需要改进")


if __name__ == "__main__":
    asyncio.run(test_queries())

