"""
测试不同模型组合的完整占卜流程
依次测试三种模型组合：
1. GPT-5 (意象+解读) + GPT-4o-mini (问题分析)
2. DeepSeek R1 (意象+解读) + DeepSeek v3 (问题分析)
3. Gemini 2.5 Pro (意象+解读) + Gemini 1.5 (问题分析)
"""

import asyncio
import sys
import json
import time
import os
from pathlib import Path
from datetime import datetime

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.tarot.reading_service import ReadingService
from app.models.schemas import UserProfileCreate
from app.core.database import get_supabase_service
from app.core.model_config import ModelPreset, set_model_config, reset_model_config


async def test_model_preset(preset: ModelPreset, preset_name: str):
    """测试指定的模型预设"""
    print("\n" + "="*80)
    print(f"测试模型组合: {preset_name}")
    print(f"预设: {preset.value}")
    print("="*80)
    
    # 设置模型配置
    set_model_config(preset)
    
    # 创建服务实例
    service = ReadingService()
    supabase = get_supabase_service()
    
    # 创建测试用户信息
    user_profile = UserProfileCreate(
        age=28,
        gender="female",
        zodiac_sign="Leo",
        appearance_type="wands",
        personality_type="wands",
        preferred_source="pkt"
    )
    
    question = "算一下我朋友的人生走势，什么时候发财，什么时候结婚，难度是high"
    
    # 记录开始时间
    start_time = time.time()
    
    # 记录所有步骤的数据
    test_log = {
        "test_timestamp": datetime.now().isoformat(),
        "model_preset": preset.value,
        "preset_name": preset_name,
        "question": question,
        "user_profile": user_profile.model_dump(),
        "steps": [],
        "reading_id": None,
        "final_result": None,
        "total_time_ms": 0,
        "errors": []
    }
    
    try:
        print(f"\n问题: {question}")
        print(f"用户信息: {user_profile.model_dump()}")
        
        # 调用占卜服务
        result = await service.create_reading(
            question=question,
            user_id=None,  # 测试时不提供user_id
            user_selected_spread=None,  # 让系统自动选择
            user_profile=user_profile,
            preferred_source="pkt"
        )
        
        reading_id = result.get('reading_id')
        test_log['reading_id'] = reading_id
        
        # 记录最终结果
        test_log['final_result'] = {
            'reading_id': reading_id,
            'question': result.get('question'),
            'spread_type': result.get('spread_type'),
            'significator': result.get('significator'),
            'cards_count': len(result.get('cards', [])),
            'pattern_analysis_method': result.get('pattern_analysis', {}).get('analysis_method'),
            'interpretation_summary': result.get('interpretation', {}).get('overall_summary', '')[:200] if result.get('interpretation') else None,
            'metadata': result.get('metadata')
        }
        
        # 从数据库获取所有过程数据
        print("\n从数据库获取占卜过程数据...")
        process_data_result = supabase.table('reading_process_data').select('*').eq('reading_id', reading_id).order('step_order').execute()
        
        if process_data_result.data:
            print(f"找到 {len(process_data_result.data)} 条过程数据记录")
            
            for step_data in process_data_result.data:
                step_log = {
                    'step_name': step_data.get('step_name'),
                    'step_order': step_data.get('step_order'),
                    'input_data': step_data.get('input_data'),
                    'output_data': step_data.get('output_data'),
                    'prompt_type': step_data.get('prompt_type'),
                    'prompt_content': step_data.get('prompt_content'),
                    'rag_queries': step_data.get('rag_queries'),
                    'model_used': step_data.get('model_used'),
                    'temperature': step_data.get('temperature'),
                    'processing_time_ms': step_data.get('processing_time_ms'),
                    'tokens_used': step_data.get('tokens_used'),
                    'created_at': step_data.get('created_at')
                }
                test_log['steps'].append(step_log)
                
                # 打印步骤摘要
                print(f"\n步骤 {step_data.get('step_order')}: {step_data.get('step_name')}")
                print(f"  - 处理时间: {step_data.get('processing_time_ms')}ms")
                print(f"  - 模型: {step_data.get('model_used', 'N/A')}")
        else:
            print("⚠️ 未找到过程数据记录")
        
        # 计算总时间
        total_time_ms = int((time.time() - start_time) * 1000)
        test_log['total_time_ms'] = total_time_ms
        
        print(f"\n✅ 完整占卜流程完成 ({total_time_ms}ms)")
        print(f"✅ 占卜ID: {reading_id}")
        print(f"✅ 过程数据记录数: {len(test_log['steps'])}")
        
        # 保存测试日志到文件
        log_filename = f"test_reading_{preset.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_dir = Path(__file__).parent / "result"
        result_dir.mkdir(exist_ok=True)
        log_path = result_dir / log_filename
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(test_log, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ 测试日志已保存到: {log_path}")
        
        return test_log
        
    except Exception as e:
        print(f"\n❌ 完整占卜流程失败: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        test_log['errors'].append({
            'error': str(e),
            'traceback': error_traceback
        })
        
        # 保存错误日志
        log_filename = f"test_reading_error_{preset.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_dir = Path(__file__).parent / "result"
        result_dir.mkdir(exist_ok=True)
        log_path = result_dir / log_filename
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(test_log, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n❌ 错误日志已保存到: {log_path}")
        traceback.print_exc()
        return test_log
    finally:
        # 重置模型配置
        reset_model_config()


async def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("不同模型组合的完整占卜流程测试")
    print("="*80)
    print("\n此测试将依次运行三种模型组合：")
    print("  1. GPT-5 (意象+解读) + GPT-4o-mini (问题分析)")
    print("  2. DeepSeek R1 (意象+解读) + DeepSeek v3 (问题分析)")
    print("  3. Gemini 2.5 Pro (意象+解读) + Gemini 1.5 (问题分析)")
    print("\n请确保已配置环境变量（OPENROUTER_API_KEY）")
    print("请确保已配置Supabase连接（SUPABASE_URL和SUPABASE_SERVICE_ROLE_KEY）")
    print("="*80)
    
    # 检查是否使用OpenRouter
    use_openrouter = os.getenv('USE_OPENROUTER', 'false').lower() == 'true'
    if not use_openrouter:
        print("\n⚠️ 警告: USE_OPENROUTER未设置为true，某些模型可能无法使用")
        print("建议设置 USE_OPENROUTER=true 以使用OpenRouter访问所有模型")
        print("注意: DeepSeek和Gemini模型必须通过OpenRouter访问")
        # 尝试设置环境变量
        os.environ['USE_OPENROUTER'] = 'true'
        print("已自动设置 USE_OPENROUTER=true")
        # 重新加载settings
        from app.core.config import settings
        settings.use_openrouter = True
    
    results = {}
    
    try:
        # 测试1: GPT-5 + GPT-4o-mini
        print("\n" + "="*80)
        print("开始测试 1/3: GPT-5 + GPT-4o-mini")
        print("="*80)
        results['gpt5_4omini'] = await test_model_preset(
            ModelPreset.GPT5_4OMINI,
            "GPT-5 (意象+解读) + GPT-4o-mini (问题分析)"
        )
        
        # 等待一段时间避免API限流
        print("\n等待10秒以避免API限流...")
        await asyncio.sleep(10)
        
        # 测试2: DeepSeek R1 + DeepSeek v3
        print("\n" + "="*80)
        print("开始测试 2/3: DeepSeek R1 + DeepSeek v3")
        print("="*80)
        results['deepseek_r1_v3'] = await test_model_preset(
            ModelPreset.DEEPSEEK_R1_V3,
            "DeepSeek R1 (意象+解读) + DeepSeek v3 (问题分析)"
        )
        
        # 等待一段时间避免API限流
        print("\n等待10秒以避免API限流...")
        await asyncio.sleep(10)
        
        # 测试3: Gemini 2.5 Pro + Gemini 1.5
        print("\n" + "="*80)
        print("开始测试 3/3: Gemini 2.5 Pro + Gemini 1.5")
        print("="*80)
        results['gemini_25pro_15'] = await test_model_preset(
            ModelPreset.GEMINI_25PRO_15,
            "Gemini 2.5 Pro (意象+解读) + Gemini 1.5 (问题分析)"
        )
        
        # 打印总结
        print("\n" + "="*80)
        print("所有测试完成 - 总结")
        print("="*80)
        
        for preset_name, result in results.items():
            if result.get('errors'):
                print(f"\n❌ {preset_name}: 失败")
                for error in result['errors']:
                    print(f"  错误: {error.get('error', 'Unknown error')}")
            else:
                total_time = result.get('total_time_ms', 0)
                steps_count = len(result.get('steps', []))
                print(f"\n✅ {preset_name}:")
                print(f"  总时间: {total_time}ms")
                print(f"  步骤数: {steps_count}")
                print(f"  占卜ID: {result.get('reading_id', 'N/A')}")
                
                # 显示使用的模型
                models_used = set()
                for step in result.get('steps', []):
                    model = step.get('model_used')
                    if model:
                        models_used.add(model)
                if models_used:
                    print(f"  使用的模型: {', '.join(sorted(models_used))}")
        
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

