"""
测试完整占卜流程 - 包括问题分析、选牌、牌型分析、RAG检索和最终解读
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.tarot.reading_service import ReadingService
from backend.app.models.schemas import UserProfileCreate


async def test_full_reading_direct_llm():
    """测试完整占卜流程（使用直接LLM进行牌型分析）"""
    print("\n" + "="*80)
    print("测试 1: 完整占卜流程（直接LLM牌型分析）")
    print("="*80)
    
    service = ReadingService()
    
    # 创建测试用户信息
    user_profile = UserProfileCreate(
        age=28,
        gender="female",
        zodiac_sign="Leo",
        appearance_type="wands",
        personality_type="wands",
        preferred_source="pkt"
    )
    
    question = "我未来三个月的工作发展如何？"
    
    import time
    start_time = time.time()
    
    try:
        result = await service.create_reading(
            question=question,
            user_id=None,  # 测试时可以不提供user_id
            user_selected_spread=None,  # 让系统自动选择
            user_profile=user_profile,
            use_rag_for_pattern=False,  # 使用直接LLM
            preferred_source="pkt"
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        print(f"\n✅ 完整占卜流程完成 ({elapsed_ms}ms)")
        print(f"\n问题: {result['question']}")
        print(f"\n问题分析:")
        qa = result['question_analysis']
        print(f"  - 领域: {qa.get('question_domain')}")
        print(f"  - 复杂度: {qa.get('complexity', 'N/A')}")
        print(f"  - 推荐占卜方式: {qa.get('recommended_spread', 'N/A')}")
        
        print(f"\n占卜方式: {result['spread_type']}")
        
        if result.get('significator'):
            print(f"\n代表牌:")
            sig = result['significator']
            print(f"  - {sig.get('card_name_en')} ({sig.get('card_name_cn', 'N/A')})")
            print(f"  - 选择原因: {sig.get('selection_reason', 'N/A')}")
        
        print(f"\n选中的牌 ({len(result['cards'])}张):")
        for card in result['cards']:
            card_str = f"  {card['position_order']}. {card['position']}: {card['card_name_en']}"
            if card['card_name_cn']:
                card_str += f" ({card['card_name_cn']})"
            if card['is_reversed']:
                card_str += " [逆位]"
            print(card_str)
        
        print(f"\n牌型分析:")
        pa = result['pattern_analysis']
        print(f"  - 分析方法: {pa.get('analysis_method')}")
        print(f"  - 时间线: {pa.get('position_relationships', {}).get('time_flow', 'N/A')[:100]}...")
        print(f"  - 花色分布: {pa.get('suit_distribution', {}).get('interpretation', 'N/A')[:100]}...")
        
        print(f"\n解读摘要:")
        interp = result['interpretation']
        print(f"  - 整体解读: {interp.get('overall_summary', 'N/A')[:200]}...")
        print(f"  - 位置解读数量: {len(interp.get('position_interpretations', []))}")
        print(f"  - 引用来源数量: {len(interp.get('references', []))}")
        
        print(f"\n元数据:")
        meta = result['metadata']
        print(f"  - 总处理时间: {meta.get('processing_time_ms')}ms")
        print(f"  - 牌型分析方法: {meta.get('pattern_analysis_method')}")
        
        return result, elapsed_ms
        
    except Exception as e:
        print(f"\n❌ 完整占卜流程失败: {e}")
        import traceback
        traceback.print_exc()
        return None, 0


async def test_full_reading_rag():
    """测试完整占卜流程（使用RAG增强进行牌型分析）"""
    print("\n" + "="*80)
    print("测试 2: 完整占卜流程（RAG增强牌型分析）")
    print("="*80)
    
    service = ReadingService()
    
    # 创建测试用户信息
    user_profile = UserProfileCreate(
        age=28,
        gender="female",
        zodiac_sign="Leo",
        appearance_type="wands",
        personality_type="wands",
        preferred_source="pkt"
    )
    
    question = "我未来三个月的工作发展如何？"
    
    import time
    start_time = time.time()
    
    try:
        result = await service.create_reading(
            question=question,
            user_id=None,
            user_selected_spread=None,
            user_profile=user_profile,
            use_rag_for_pattern=True,  # 使用RAG增强
            preferred_source="pkt"
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        print(f"\n✅ 完整占卜流程完成 ({elapsed_ms}ms)")
        print(f"\n问题: {result['question']}")
        print(f"\n占卜方式: {result['spread_type']}")
        
        print(f"\n牌型分析:")
        pa = result['pattern_analysis']
        print(f"  - 分析方法: {pa.get('analysis_method')}")
        print(f"  - RAG查询: {pa.get('rag_queries', [])}")
        print(f"  - 时间线: {pa.get('position_relationships', {}).get('time_flow', 'N/A')[:100]}...")
        
        print(f"\n解读摘要:")
        interp = result['interpretation']
        print(f"  - 整体解读: {interp.get('overall_summary', 'N/A')[:200]}...")
        
        print(f"\n元数据:")
        meta = result['metadata']
        print(f"  - 总处理时间: {meta.get('processing_time_ms')}ms")
        
        return result, elapsed_ms
        
    except Exception as e:
        print(f"\n❌ 完整占卜流程失败: {e}")
        import traceback
        traceback.print_exc()
        return None, 0


async def compare_full_readings():
    """比较两种完整占卜流程"""
    print("\n" + "="*80)
    print("比较测试: 直接LLM vs RAG增强（完整流程）")
    print("="*80)
    
    # 运行两种测试
    direct_result, direct_time = await test_full_reading_direct_llm()
    rag_result, rag_time = await test_full_reading_rag()
    
    # 比较结果
    print("\n" + "="*80)
    print("比较结果")
    print("="*80)
    
    print(f"\n性能比较:")
    print(f"  - 直接LLM: {direct_time}ms")
    print(f"  - RAG增强: {rag_time}ms")
    print(f"  - 时间差: {abs(rag_time - direct_time)}ms ({'RAG较慢' if rag_time > direct_time else 'RAG较快'})")
    
    if direct_result and rag_result:
        print(f"\n结果质量比较:")
        
        # 比较牌型分析
        direct_pa = direct_result.get('pattern_analysis', {})
        rag_pa = rag_result.get('pattern_analysis', {})
        
        direct_time_flow = direct_pa.get('position_relationships', {}).get('time_flow', '')
        rag_time_flow = rag_pa.get('position_relationships', {}).get('time_flow', '')
        
        print(f"\n时间线关系详细程度:")
        print(f"  - 直接LLM: {len(direct_time_flow)} 字符")
        print(f"  - RAG增强: {len(rag_time_flow)} 字符")
        
        # 比较解读质量
        direct_interp = direct_result.get('interpretation', {}).get('overall_summary', '')
        rag_interp = rag_result.get('interpretation', {}).get('overall_summary', '')
        
        print(f"\n整体解读详细程度:")
        print(f"  - 直接LLM: {len(direct_interp)} 字符")
        print(f"  - RAG增强: {len(rag_interp)} 字符")
        
        # 比较引用来源
        direct_refs = len(direct_result.get('interpretation', {}).get('references', []))
        rag_refs = len(rag_result.get('interpretation', {}).get('references', []))
        
        print(f"\n引用来源数量:")
        print(f"  - 直接LLM: {direct_refs}")
        print(f"  - RAG增强: {rag_refs}")
        
        # 总结
        print(f"\n总结:")
        if rag_time > direct_time * 1.3:
            print(f"  ⚠️ RAG增强方式明显较慢（慢{rag_time - direct_time}ms，约{int((rag_time/direct_time - 1)*100)}%）")
        else:
            print(f"  ✅ 两种方式性能相近")
        
        if len(rag_time_flow) > len(direct_time_flow) * 1.2:
            print(f"  ✅ RAG增强方式提供了更详细的牌型分析")
        else:
            print(f"  ℹ️ 两种方式的牌型分析详细程度相近")
        
        if rag_refs > direct_refs:
            print(f"  ✅ RAG增强方式提供了更多引用来源")
        else:
            print(f"  ℹ️ 两种方式的引用来源数量相近")


async def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("完整占卜流程测试")
    print("="*80)
    print("\n此测试将比较两种完整占卜流程:")
    print("  1. 直接LLM牌型分析（快速，基于通用知识）")
    print("  2. RAG增强牌型分析（较慢，基于传统文献）")
    print("\n请确保已配置环境变量（OPENROUTER_API_KEY或OPENAI_API_KEY）")
    print("请确保已配置Supabase连接（SUPABASE_URL和SUPABASE_SERVICE_ROLE_KEY）")
    print("="*80)
    
    try:
        await compare_full_readings()
        print("\n" + "="*80)
        print("✅ 所有测试完成")
        print("="*80)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

