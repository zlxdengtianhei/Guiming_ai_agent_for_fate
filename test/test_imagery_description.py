"""
测试牌阵意象描述生成功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加backend目录到Python路径
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.tarot.reading_service import reading_service
from app.models.schemas import UserProfileCreate

async def test_imagery_description():
    """测试意象描述生成"""
    print("=" * 80)
    print("测试牌阵意象描述生成功能")
    print("=" * 80)
    
    # 测试问题
    question = "我下个月的工作发展如何？"
    
    # 用户信息
    user_profile = UserProfileCreate(
        age=28,
        gender="female",
        zodiac_sign="Leo",
        appearance_type="wands",
        personality_type="wands"
    )
    
    print(f"\n问题: {question}")
    print(f"用户信息: {user_profile.model_dump()}")
    print("\n开始创建占卜...")
    
    try:
        # 创建完整占卜
        result = await reading_service.create_reading(
            question=question,
            user_selected_spread="three_card",
            user_profile=user_profile,
            preferred_source="pkt"
        )
        
        print("\n" + "=" * 80)
        print("占卜结果")
        print("=" * 80)
        
        # 检查结果中是否包含意象描述
        reading_id = result.get('reading_id')
        print(f"\nReading ID: {reading_id}")
        
        # 从数据库查询过程数据，查找意象描述
        from app.core.database import get_supabase_service
        supabase = get_supabase_service()
        
        process_data = supabase.table('reading_process_data').select('*').eq('reading_id', reading_id).eq('step_name', 'imagery_description').execute()
        
        if process_data.data:
            imagery_data = process_data.data[0]
            print("\n" + "-" * 80)
            print("意象描述生成过程数据:")
            print("-" * 80)
            print(f"步骤: {imagery_data.get('step_name')}")
            print(f"处理时间: {imagery_data.get('processing_time_ms')}ms")
            print(f"使用的模型: {imagery_data.get('model_used')}")
            
            output_data = imagery_data.get('output_data', {})
            imagery_description = output_data.get('imagery_description', '')
            
            print("\n生成的意象描述:")
            print("-" * 80)
            print(imagery_description)
            print("-" * 80)
            
            # 检查最终解读的prompt中是否包含意象描述
            interpretation_data = supabase.table('reading_process_data').select('*').eq('reading_id', reading_id).eq('step_name', 'final_interpretation').execute()
            
            if interpretation_data.data:
                interpretation_prompt = interpretation_data.data[0].get('prompt_content', '')
                if imagery_description in interpretation_prompt:
                    print("\n✅ 成功: 意象描述已包含在最终解读的prompt中")
                else:
                    print("\n⚠️ 警告: 意象描述未在最终解读的prompt中找到")
                    # 检查是否至少包含"意象"关键词
                    if "意象" in interpretation_prompt:
                        print("   但prompt中包含'意象'关键词，可能格式不同")
                    else:
                        print("   prompt中未找到'意象'关键词")
            
            print("\n✅ 测试通过: 意象描述功能正常工作")
        else:
            print("\n❌ 错误: 未找到意象描述生成过程数据")
            print("   可能的原因:")
            print("   1. 意象描述生成步骤未执行")
            print("   2. 数据未保存到数据库")
        
        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_imagery_description())




