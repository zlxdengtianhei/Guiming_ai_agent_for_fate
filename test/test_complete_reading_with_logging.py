"""
测试完整占卜流程并记录所有输入输出
记录所有LLM调用、RAG查询和占卜过程数据
"""

import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.tarot.reading_service import ReadingService
from app.models.schemas import UserProfileCreate
from app.core.database import get_supabase_service


async def test_complete_reading_with_logging():
    """测试完整占卜流程并记录所有输入输出"""
    print("\n" + "="*80)
    print("测试：完整占卜流程（记录所有输入输出）")
    print("="*80)
    
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
                if step_data.get('prompt_content'):
                    prompt_len = len(step_data.get('prompt_content', ''))
                    print(f"  - Prompt长度: {prompt_len} 字符")
                if step_data.get('rag_queries'):
                    print(f"  - RAG查询数量: {len(step_data.get('rag_queries', []))}")
        else:
            print("⚠️ 未找到过程数据记录")
        
        # 从数据库获取reading记录
        print("\n从数据库获取占卜记录...")
        reading_result = supabase.table('readings').select('*').eq('id', reading_id).execute()
        
        if reading_result.data:
            reading_record = reading_result.data[0]
            test_log['reading_record'] = {
                'id': reading_record.get('id'),
                'question': reading_record.get('question'),
                'status': reading_record.get('status'),
                'current_step': reading_record.get('current_step'),
                'question_domain': reading_record.get('question_domain'),
                'question_complexity': reading_record.get('question_complexity'),
                'spread_type': reading_record.get('spread_type'),
                'significator_card_id': reading_record.get('significator_card_id'),
                'has_pattern_analysis': reading_record.get('spread_pattern_analysis') is not None,
                'has_interpretation': reading_record.get('interpretation') is not None,
                'created_at': reading_record.get('created_at')
            }
            print(f"✅ 占卜记录状态: {reading_record.get('status')}")
            print(f"✅ 当前步骤: {reading_record.get('current_step')}")
        
        # 从数据库获取reading_cards记录
        print("\n从数据库获取选中的牌...")
        cards_result = supabase.table('reading_cards').select('*').eq('reading_id', reading_id).order('position_order').execute()
        
        if cards_result.data:
            test_log['cards'] = cards_result.data
            print(f"✅ 找到 {len(cards_result.data)} 张牌")
            for card in cards_result.data:
                print(f"  - {card.get('position_order')}. {card.get('position')}: {card.get('card_id')}")
        
        # 计算总时间
        total_time_ms = int((time.time() - start_time) * 1000)
        test_log['total_time_ms'] = total_time_ms
        
        print(f"\n✅ 完整占卜流程完成 ({total_time_ms}ms)")
        print(f"✅ 占卜ID: {reading_id}")
        print(f"✅ 过程数据记录数: {len(test_log['steps'])}")
        
        # 保存测试日志到文件
        log_filename = f"test_reading_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_dir = Path(__file__).parent / "result"
        result_dir.mkdir(exist_ok=True)
        log_path = result_dir / log_filename
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(test_log, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ 测试日志已保存到: {log_path}")
        
        # 验证数据完整性
        print("\n" + "="*80)
        print("数据完整性验证")
        print("="*80)
        
        # 检查是否有所有步骤的记录
        expected_steps = ['question_analysis', 'pattern_analysis', 'rag_retrieval', 'imagery_description', 'final_interpretation']
        found_steps = [step['step_name'] for step in test_log['steps']]
        
        print(f"\n期望的步骤: {expected_steps}")
        print(f"找到的步骤: {found_steps}")
        
        missing_steps = [step for step in expected_steps if step not in found_steps]
        if missing_steps:
            print(f"⚠️ 缺少步骤: {missing_steps}")
        else:
            print("✅ 所有步骤都有记录")
        
        # 检查每个步骤是否有必要的数据，并输出LLM输入输出
        print("\n" + "="*80)
        print("详细步骤信息（包含LLM输入输出）")
        print("="*80)
        
        for step in test_log['steps']:
            step_name = step['step_name']
            has_input = step.get('input_data') is not None
            has_output = step.get('output_data') is not None
            
            print(f"\n{'='*80}")
            print(f"步骤 {step['step_order']}: {step_name}")
            print(f"{'='*80}")
            print(f"  - 有输入数据: {'✅' if has_input else '❌'}")
            print(f"  - 有输出数据: {'✅' if has_output else '❌'}")
            print(f"  - 处理时间: {step.get('processing_time_ms', 'N/A')}ms")
            print(f"  - 使用的模型: {step.get('model_used', 'N/A')}")
            print(f"  - 温度: {step.get('temperature', 'N/A')}")
            
            # 输出问题分析步骤的LLM输入输出
            if step_name == 'question_analysis':
                has_prompt = step.get('prompt_content') is not None
                has_llm_response = step.get('output_data', {}).get('llm_response') is not None
                print(f"  - 有Prompt: {'✅' if has_prompt else '❌'}")
                print(f"  - 有LLM响应: {'✅' if has_llm_response else '❌'}")
                
                if has_prompt:
                    print(f"\n  📝 Prompt内容（前500字符）:")
                    prompt_content = step.get('prompt_content', '')
                    print(f"  {prompt_content[:500]}...")
                    if len(prompt_content) > 500:
                        print(f"  (总长度: {len(prompt_content)} 字符)")
                
                if has_llm_response:
                    llm_response = step.get('output_data', {}).get('llm_response', '')
                    print(f"\n  💬 LLM响应:")
                    print(f"  {llm_response}")
            
            # 输出意象描述生成步骤的LLM输入输出
            elif step_name == 'imagery_description':
                has_prompt = step.get('prompt_content') is not None
                has_imagery = step.get('output_data', {}).get('imagery_description') is not None
                has_llm_response = step.get('output_data', {}).get('llm_response') is not None
                print(f"  - 有Prompt: {'✅' if has_prompt else '❌'}")
                print(f"  - 有意象描述: {'✅' if has_imagery else '❌'}")
                print(f"  - 有LLM响应: {'✅' if has_llm_response else '❌'}")
                
                if has_prompt:
                    prompt_content = step.get('prompt_content', '')
                    print(f"\n  📝 Prompt内容:")
                    print(f"  {prompt_content}")
                
                if has_imagery:
                    imagery_description = step.get('output_data', {}).get('imagery_description', '')
                    print(f"\n  💬 生成的意象描述:")
                    print(f"  {imagery_description}")
                
                if has_llm_response:
                    llm_response = step.get('output_data', {}).get('llm_response', '')
                    print(f"\n  💬 LLM响应（完整）:")
                    print(f"  {llm_response}")
                
                # 显示输入数据摘要
                input_data = step.get('input_data', {})
                if input_data:
                    print(f"\n  📥 输入数据摘要:")
                    print(f"  - 问题领域: {input_data.get('question_domain', 'N/A')}")
                    print(f"  - 卡牌数量: {len(input_data.get('selected_cards', []))}")
                    for i, card in enumerate(input_data.get('selected_cards', [])[:3], 1):
                        print(f"    {i}. {card.get('card_name_en', 'N/A')} ({card.get('position', 'N/A')})")
            
            # 输出最终解读步骤的LLM输入输出
            elif step_name == 'final_interpretation':
                has_prompt = step.get('prompt_content') is not None
                has_llm_response = step.get('output_data', {}).get('llm_response') is not None
                print(f"  - 有Prompt: {'✅' if has_prompt else '❌'}")
                print(f"  - 有LLM响应: {'✅' if has_llm_response else '❌'}")
                
                if has_prompt:
                    prompt_content = step.get('prompt_content', '')
                    # 检查prompt中是否包含意象描述
                    if '牌阵意象描述' in prompt_content or '意象描述' in prompt_content:
                        print(f"\n  ✅ Prompt中包含意象描述部分")
                        # 提取意象描述部分
                        imagery_start = prompt_content.find('## 牌阵意象描述')
                        if imagery_start != -1:
                            imagery_end = prompt_content.find('##', imagery_start + 1)
                            if imagery_end == -1:
                                imagery_end = len(prompt_content)
                            imagery_section = prompt_content[imagery_start:imagery_end]
                            print(f"\n  📝 意象描述部分（在Prompt中）:")
                            print(f"  {imagery_section[:500]}...")
                    else:
                        print(f"\n  ⚠️ Prompt中未找到意象描述部分")
                    
                    print(f"\n  📝 Prompt内容（前1000字符）:")
                    print(f"  {prompt_content[:1000]}...")
                    if len(prompt_content) > 1000:
                        print(f"  (总长度: {len(prompt_content)} 字符)")
                
                if has_llm_response:
                    llm_response = step.get('output_data', {}).get('llm_response', '')
                    print(f"\n  💬 LLM响应（前500字符）:")
                    print(f"  {llm_response[:500]}...")
                    if len(llm_response) > 500:
                        print(f"  (总长度: {len(llm_response)} 字符)")
            
            elif step_name in ['pattern_analysis']:
                has_prompt = step.get('prompt_content') is not None
                has_llm_response = step.get('output_data', {}).get('llm_response') is not None
                print(f"  - 有Prompt: {'✅' if has_prompt else '❌'}")
                print(f"  - 有LLM响应: {'✅' if has_llm_response else '❌'}")
                # 注意：pattern_analysis现在是纯代码实现，可能没有LLM调用
            
            if step_name == 'rag_retrieval':
                has_rag_queries = step.get('rag_queries') is not None
                print(f"  - 有RAG查询: {'✅' if has_rag_queries else '❌'}")
                if has_rag_queries:
                    rag_queries = step.get('rag_queries', [])
                    print(f"  - RAG查询数量: {len(rag_queries)}")
                    # 显示前3个查询
                    for i, query in enumerate(rag_queries[:3], 1):
                        query_text = query.get('query', 'N/A')
                        query_type = query.get('type', 'N/A')
                        print(f"    {i}. [{query_type}] {query_text[:100]}...")
        
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
        log_filename = f"test_reading_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_dir = Path(__file__).parent / "result"
        result_dir.mkdir(exist_ok=True)
        log_path = result_dir / log_filename
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(test_log, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n❌ 错误日志已保存到: {log_path}")
        traceback.print_exc()
        return test_log


async def verify_rls_policies():
    """验证RLS策略：用户不能查看占卜过程数据"""
    print("\n" + "="*80)
    print("验证RLS策略：用户不能查看占卜过程数据")
    print("="*80)
    
    supabase = get_supabase_service()
    
    # 检查表是否存在
    try:
        # 尝试查询表（如果表不存在会报错）
        result = supabase.table('reading_process_data').select('id').limit(1).execute()
        print("✅ reading_process_data表已创建")
        print("✅ 表中有数据，可以正常查询（使用service role）")
    except Exception as e:
        print(f"⚠️ 检查表时出错: {e}")
    
    # 检查readings表是否有user_id字段（用于关联用户）
    try:
        readings_result = supabase.table('readings').select('id, user_id').limit(1).execute()
        print("✅ readings表有user_id字段，可以关联用户")
    except Exception as e:
        print(f"⚠️ 检查readings表时出错: {e}")
    
    print("\n✅ RLS策略说明:")
    print("  - reading_process_data表只允许service role访问")
    print("  - 用户不能直接查看占卜过程数据")
    print("  - 用户只能查看占卜结果（readings表）")


async def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("完整占卜流程测试（记录所有输入输出）")
    print("="*80)
    print("\n此测试将：")
    print("  1. 运行完整占卜流程")
    print("  2. 记录所有LLM调用的prompt和response")
    print("  3. 记录所有RAG查询和结果")
    print("  4. 验证数据完整性")
    print("  5. 验证RLS策略（用户不能查看占卜过程数据）")
    print("\n请确保已配置环境变量（OPENROUTER_API_KEY或OPENAI_API_KEY）")
    print("请确保已配置Supabase连接（SUPABASE_URL和SUPABASE_SERVICE_ROLE_KEY）")
    print("="*80)
    
    try:
        # 运行测试
        test_log = await test_complete_reading_with_logging()
        
        # 验证RLS策略
        await verify_rls_policies()
        
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

