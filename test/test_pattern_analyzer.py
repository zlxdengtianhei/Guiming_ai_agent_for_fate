"""
测试牌型分析服务 - 比较直接LLM和RAG增强两种方式
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.tarot.pattern_analyzer import PatternAnalyzerService
from backend.app.services.tarot.card_selection import SelectedCard


async def test_pattern_analysis_direct():
    """测试直接LLM分析方式"""
    print("\n" + "="*80)
    print("测试 1: 直接LLM分析方式")
    print("="*80)
    
    # 创建测试牌阵（三牌占卜）
    test_cards = [
        SelectedCard(
            card_id="card1",
            card_name_en="The Fool",
            card_name_cn="愚者",
            suit="major",
            card_number=0,
            arcana="major",
            position="past",
            position_order=1,
            position_description="过去",
            is_reversed=False
        ),
        SelectedCard(
            card_id="card2",
            card_name_en="The Magician",
            card_name_cn="魔术师",
            suit="major",
            card_number=1,
            arcana="major",
            position="present",
            position_order=2,
            position_description="现在",
            is_reversed=False
        ),
        SelectedCard(
            card_id="card3",
            card_name_en="The World",
            card_name_cn="世界",
            suit="major",
            card_number=21,
            arcana="major",
            position="future",
            position_order=3,
            position_description="未来",
            is_reversed=True
        )
    ]
    
    analyzer = PatternAnalyzerService()
    
    import time
    start_time = time.time()
    
    try:
        result = await analyzer.analyze_spread_pattern_direct(
            selected_cards=test_cards,
            spread_type="three_card",
            question_domain="career"
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        print(f"\n✅ 直接LLM分析完成 ({elapsed_ms}ms)")
        print(f"\n分析方法: {result.get('analysis_method')}")
        print(f"使用模型: {result.get('model_used')}")
        print(f"\n位置关系:")
        print(f"  - 时间线: {result.get('position_relationships', {}).get('time_flow', 'N/A')}")
        print(f"  - 因果关系: {result.get('position_relationships', {}).get('causal_relationships', [])}")
        
        print(f"\n花色分布:")
        suit_dist = result.get('suit_distribution', {})
        print(f"  - 大阿卡纳: {suit_dist.get('major_count', 0)}")
        print(f"  - 解释: {suit_dist.get('interpretation', 'N/A')}")
        
        print(f"\n逆位模式:")
        reversed_info = result.get('reversed_patterns', {})
        print(f"  - 数量: {reversed_info.get('count', 0)}")
        print(f"  - 解释: {reversed_info.get('interpretation', 'N/A')}")
        
        print(f"\n特殊组合:")
        for combo in result.get('special_combinations', []):
            print(f"  - {combo}")
        
        return result, elapsed_ms
        
    except Exception as e:
        print(f"\n❌ 直接LLM分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None, 0


async def test_pattern_analysis_rag():
    """测试RAG增强分析方式"""
    print("\n" + "="*80)
    print("测试 2: RAG增强分析方式")
    print("="*80)
    
    # 创建相同的测试牌阵
    test_cards = [
        SelectedCard(
            card_id="card1",
            card_name_en="The Fool",
            card_name_cn="愚者",
            suit="major",
            card_number=0,
            arcana="major",
            position="past",
            position_order=1,
            position_description="过去",
            is_reversed=False
        ),
        SelectedCard(
            card_id="card2",
            card_name_en="The Magician",
            card_name_cn="魔术师",
            suit="major",
            card_number=1,
            arcana="major",
            position="present",
            position_order=2,
            position_description="现在",
            is_reversed=False
        ),
        SelectedCard(
            card_id="card3",
            card_name_en="The World",
            card_name_cn="世界",
            suit="major",
            card_number=21,
            arcana="major",
            position="future",
            position_order=3,
            position_description="未来",
            is_reversed=True
        )
    ]
    
    analyzer = PatternAnalyzerService()
    
    import time
    start_time = time.time()
    
    try:
        result = await analyzer.analyze_spread_pattern_rag(
            selected_cards=test_cards,
            spread_type="three_card",
            question_domain="career"
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        print(f"\n✅ RAG增强分析完成 ({elapsed_ms}ms)")
        print(f"\n分析方法: {result.get('analysis_method')}")
        print(f"使用模型: {result.get('model_used')}")
        print(f"\nRAG查询:")
        for query in result.get('rag_queries', []):
            print(f"  - {query}")
        
        print(f"\n位置关系:")
        print(f"  - 时间线: {result.get('position_relationships', {}).get('time_flow', 'N/A')}")
        print(f"  - 因果关系: {result.get('position_relationships', {}).get('causal_relationships', [])}")
        
        print(f"\n花色分布:")
        suit_dist = result.get('suit_distribution', {})
        print(f"  - 大阿卡纳: {suit_dist.get('major_count', 0)}")
        print(f"  - 解释: {suit_dist.get('interpretation', 'N/A')}")
        
        print(f"\n逆位模式:")
        reversed_info = result.get('reversed_patterns', {})
        print(f"  - 数量: {reversed_info.get('count', 0)}")
        print(f"  - 解释: {reversed_info.get('interpretation', 'N/A')}")
        
        print(f"\n特殊组合:")
        for combo in result.get('special_combinations', []):
            print(f"  - {combo}")
        
        return result, elapsed_ms
        
    except Exception as e:
        print(f"\n❌ RAG增强分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None, 0


async def compare_methods():
    """比较两种分析方式"""
    print("\n" + "="*80)
    print("比较测试: 直接LLM vs RAG增强")
    print("="*80)
    
    # 运行两种测试
    direct_result, direct_time = await test_pattern_analysis_direct()
    rag_result, rag_time = await test_pattern_analysis_rag()
    
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
        
        # 比较位置关系
        direct_time_flow = direct_result.get('position_relationships', {}).get('time_flow', '')
        rag_time_flow = rag_result.get('position_relationships', {}).get('time_flow', '')
        print(f"\n时间线关系:")
        print(f"  - 直接LLM: {direct_time_flow[:100]}...")
        print(f"  - RAG增强: {rag_time_flow[:100]}...")
        
        # 比较花色分布解释
        direct_suit_interp = direct_result.get('suit_distribution', {}).get('interpretation', '')
        rag_suit_interp = rag_result.get('suit_distribution', {}).get('interpretation', '')
        print(f"\n花色分布解释:")
        print(f"  - 直接LLM: {direct_suit_interp[:100]}...")
        print(f"  - RAG增强: {rag_suit_interp[:100]}...")
        
        # 比较特殊组合数量
        direct_combos = len(direct_result.get('special_combinations', []))
        rag_combos = len(rag_result.get('special_combinations', []))
        print(f"\n特殊组合数量:")
        print(f"  - 直接LLM: {direct_combos}")
        print(f"  - RAG增强: {rag_combos}")
        
        # 总结
        print(f"\n总结:")
        if rag_time > direct_time * 1.5:
            print(f"  ⚠️ RAG增强方式明显较慢（慢{rag_time - direct_time}ms）")
        else:
            print(f"  ✅ 两种方式性能相近")
        
        if len(rag_time_flow) > len(direct_time_flow) * 1.2:
            print(f"  ✅ RAG增强方式提供了更详细的分析")
        else:
            print(f"  ℹ️ 两种方式的分析详细程度相近")
        
        if rag_combos > direct_combos:
            print(f"  ✅ RAG增强方式识别了更多特殊组合")
        elif direct_combos > rag_combos:
            print(f"  ✅ 直接LLM方式识别了更多特殊组合")
        else:
            print(f"  ℹ️ 两种方式识别的特殊组合数量相同")


async def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("牌型分析服务测试")
    print("="*80)
    print("\n此测试将比较两种牌型分析方式:")
    print("  1. 直接LLM分析（快速，基于通用知识）")
    print("  2. RAG增强分析（较慢，基于传统文献）")
    print("\n请确保已配置环境变量（OPENROUTER_API_KEY或OPENAI_API_KEY）")
    print("="*80)
    
    try:
        await compare_methods()
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

