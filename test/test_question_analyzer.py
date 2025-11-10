"""
测试问题分析功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.tarot.question_analyzer import QuestionAnalyzerService
from app.models.schemas import UserProfileCreate


async def test_question_analysis_auto():
    """测试自动分析问题（系统自动选择占卜方式）"""
    print("=" * 60)
    print("测试1: 自动分析问题（系统自动选择占卜方式）")
    print("=" * 60)
    
    service = QuestionAnalyzerService()
    
    test_cases = [
        {
            "question": "我未来三个月的工作发展如何？",
            "description": "职业问题 - 应该推荐celtic_cross"
        },
        {
            "question": "我们这段关系会如何发展？",
            "description": "爱情问题 - 应该推荐three_card或celtic_cross"
        },
        {
            "question": "我应该选择哪个工作机会？",
            "description": "选择问题 - 应该推荐celtic_cross"
        },
        {
            "question": "我今天的运势如何？",
            "description": "简单问题 - 应该推荐three_card"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i}: {test_case['description']} ---")
        print(f"问题: {test_case['question']}")
        
        try:
            result = await service.analyze_question(
                question=test_case['question'],
                user_selected_spread=None  # 系统自动选择
            )
            
            print(f"✅ 分析成功")
            print(f"   问题领域: {result.question_domain}")
            print(f"   复杂度: {result.complexity}")
            print(f"   提问类型: {result.question_type}")
            print(f"   推荐占卜方式: {result.recommended_spread}")
            print(f"   自动选择: {result.auto_selected_spread}")
            print(f"   理由: {result.reasoning}")
            print(f"   问题摘要: {result.question_summary}")
            
            # 验证结果
            assert result.question_domain in ['love', 'career', 'health', 'finance', 'personal_growth', 'general'], \
                f"无效的问题领域: {result.question_domain}"
            assert result.complexity in ['simple', 'moderate', 'complex'], \
                f"无效的复杂度: {result.complexity}"
            assert result.recommended_spread in ['three_card', 'celtic_cross', 'work_cycle', 'other'], \
                f"无效的推荐占卜方式: {result.recommended_spread}"
            assert result.auto_selected_spread == True, \
                "应该自动选择占卜方式"
            
            print(f"   ✅ 验证通过")
            
        except Exception as e:
            print(f"   ❌ 测试失败: {e}")
            raise


async def test_question_analysis_user_selected():
    """测试用户指定占卜方式的情况"""
    print("\n" + "=" * 60)
    print("测试2: 用户指定占卜方式")
    print("=" * 60)
    
    service = QuestionAnalyzerService()
    
    test_cases = [
        {
            "question": "我未来三个月的工作发展如何？",
            "user_selected_spread": "three_card",
            "description": "用户指定三牌占卜 - 不应该分析复杂度"
        },
        {
            "question": "我们这段关系会如何发展？",
            "user_selected_spread": "celtic_cross",
            "description": "用户指定凯尔特十字 - 不应该分析复杂度"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i}: {test_case['description']} ---")
        print(f"问题: {test_case['question']}")
        print(f"用户指定占卜方式: {test_case['user_selected_spread']}")
        
        try:
            result = await service.analyze_question(
                question=test_case['question'],
                user_selected_spread=test_case['user_selected_spread']
            )
            
            print(f"✅ 分析成功")
            print(f"   问题领域: {result.question_domain}")
            print(f"   复杂度: {result.complexity} (应该为None)")
            print(f"   提问类型: {result.question_type}")
            print(f"   推荐占卜方式: {result.recommended_spread} (应该为None)")
            print(f"   自动选择: {result.auto_selected_spread}")
            print(f"   理由: {result.reasoning}")
            print(f"   问题摘要: {result.question_summary}")
            
            # 验证结果
            assert result.question_domain in ['love', 'career', 'health', 'finance', 'personal_growth', 'general'], \
                f"无效的问题领域: {result.question_domain}"
            assert result.complexity is None, \
                "用户指定占卜方式时不应该分析复杂度"
            assert result.recommended_spread is None, \
                "用户指定占卜方式时不应该推荐占卜方式"
            assert result.auto_selected_spread == False, \
                "不应该自动选择占卜方式"
            
            print(f"   ✅ 验证通过")
            
        except Exception as e:
            print(f"   ❌ 测试失败: {e}")
            raise


async def test_question_analysis_with_user_profile():
    """测试带用户信息的问题分析"""
    print("\n" + "=" * 60)
    print("测试3: 带用户信息的问题分析")
    print("=" * 60)
    
    service = QuestionAnalyzerService()
    
    user_profile = UserProfileCreate(
        age=28,
        gender="female",
        zodiac_sign="Leo",
        personality_type="wands"
    )
    
    question = "我未来三个月的工作发展如何？"
    
    print(f"问题: {question}")
    print(f"用户信息: 年龄={user_profile.age}, 性别={user_profile.gender}, "
          f"星座={user_profile.zodiac_sign}, 性格={user_profile.personality_type}")
    
    try:
        result = await service.analyze_question(
            question=question,
            user_profile=user_profile,
            user_selected_spread=None  # 系统自动选择
        )
        
        print(f"✅ 分析成功")
        print(f"   问题领域: {result.question_domain}")
        print(f"   复杂度: {result.complexity}")
        print(f"   推荐占卜方式: {result.recommended_spread}")
        print(f"   理由: {result.reasoning}")
        
        # 验证结果
        assert result.question_domain in ['love', 'career', 'health', 'finance', 'personal_growth', 'general'], \
            f"无效的问题领域: {result.question_domain}"
        assert result.complexity in ['simple', 'moderate', 'complex'], \
            f"无效的复杂度: {result.complexity}"
        
        print(f"   ✅ 验证通过")
        
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        raise


async def test_question_domains():
    """测试不同问题领域的识别"""
    print("\n" + "=" * 60)
    print("测试4: 不同问题领域的识别")
    print("=" * 60)
    
    service = QuestionAnalyzerService()
    
    test_cases = [
        {
            "question": "我们这段关系会如何发展？",
            "expected_domain": "love",
            "description": "爱情问题"
        },
        {
            "question": "我未来三个月的工作发展如何？",
            "expected_domain": "career",
            "description": "职业问题"
        },
        {
            "question": "我的健康状况如何？",
            "expected_domain": "health",
            "description": "健康问题"
        },
        {
            "question": "我的财务状况会改善吗？",
            "expected_domain": "finance",
            "description": "财务问题"
        },
        {
            "question": "我应该如何提升自己？",
            "expected_domain": "personal_growth",
            "description": "个人成长问题"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- 测试用例 {i}: {test_case['description']} ---")
        print(f"问题: {test_case['question']}")
        print(f"期望领域: {test_case['expected_domain']}")
        
        try:
            result = await service.analyze_question(
                question=test_case['question'],
                user_selected_spread=None
            )
            
            print(f"实际领域: {result.question_domain}")
            
            # 验证结果（允许一定灵活性，因为LLM可能理解不同）
            if result.question_domain == test_case['expected_domain']:
                print(f"   ✅ 领域识别正确")
            else:
                print(f"   ⚠️ 领域识别不完全匹配（期望: {test_case['expected_domain']}, 实际: {result.question_domain}）")
                # 不强制失败，因为LLM的理解可能有差异
            
        except Exception as e:
            print(f"   ❌ 测试失败: {e}")
            raise


async def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("问题分析功能测试")
    print("=" * 60)
    
    try:
        # 测试1: 自动分析问题
        await test_question_analysis_auto()
        
        # 测试2: 用户指定占卜方式
        await test_question_analysis_user_selected()
        
        # 测试3: 带用户信息的问题分析
        await test_question_analysis_with_user_profile()
        
        # 测试4: 不同问题领域的识别
        await test_question_domains()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ 测试失败: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

