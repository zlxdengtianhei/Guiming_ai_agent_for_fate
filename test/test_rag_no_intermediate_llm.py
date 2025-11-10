"""
测试修改后的RAG流程：不使用中间LLM调用，直接使用原始chunks
记录所有RAG查询、chunks收集和去重过程
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


async def test_rag_no_intermediate_llm():
    """测试修改后的RAG流程：不使用中间LLM调用"""
    print("\n" + "="*80)
    print("测试：RAG流程优化（不使用中间LLM调用）")
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
    
    question = "我下个月运势如何"
    
    # 记录开始时间
    start_time = time.time()
    
    # 记录所有步骤的数据
    test_log = {
        "test_timestamp": datetime.now().isoformat(),
        "test_type": "rag_no_intermediate_llm",
        "question": question,
        "user_profile": user_profile.model_dump(),
        "steps": [],
        "reading_id": None,
        "final_result": None,
        "rag_analysis": {
            "total_queries": 0,
            "total_chunks_before_dedup": 0,
            "total_chunks_after_dedup": 0,
            "deduplication_rate": 0.0,
            "chunks_by_source": {},
            "chunks_by_query_type": {}
        },
        "total_time_ms": 0,
        "errors": []
    }
    
    try:
        print(f"\n问题: {question}")
        print(f"用户信息: {user_profile.model_dump()}")
        print("\n开始占卜流程...")
        
        # 调用占卜服务
        result = await service.create_reading(
            question=question,
            user_id=None,
            user_selected_spread=None,
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
            'cards_count': len(result.get('cards', [])),
            'interpretation_summary': result.get('interpretation', {}).get('overall_summary', '')[:300] if result.get('interpretation') else None,
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
                    'processing_time_ms': step_data.get('processing_time_ms'),
                    'created_at': step_data.get('created_at')
                }
                test_log['steps'].append(step_log)
                
                # 分析RAG检索步骤
                if step_data.get('step_name') == 'rag_retrieval':
                    output_data = step_data.get('output_data', {})
                    total_before = output_data.get('total_chunks_before_dedup', 0)
                    total_after = output_data.get('total_chunks_after_dedup', 0)
                    
                    test_log['rag_analysis']['total_chunks_before_dedup'] = total_before
                    test_log['rag_analysis']['total_chunks_after_dedup'] = total_after
                    
                    if total_before > 0:
                        dedup_rate = (1 - total_after / total_before) * 100
                        test_log['rag_analysis']['deduplication_rate'] = dedup_rate
                    
                    # 统计RAG查询
                    rag_queries = step_data.get('rag_queries', [])
                    test_log['rag_analysis']['total_queries'] = len(rag_queries)
                    
                    # 统计chunks按来源分布
                    card_info = output_data.get('card_information', {})
                    spread_method = output_data.get('spread_method', {})
                    card_relationships = output_data.get('card_relationships', {})
                    
                    chunks_by_source = {}
                    chunks_by_query_type = {}
                    
                    # 从卡牌信息中统计
                    for card_id, card_data in card_info.items():
                        chunks = card_data.get('chunks', [])
                        for chunk in chunks:
                            source = chunk.get('source', 'unknown')
                            chunks_by_source[source] = chunks_by_source.get(source, 0) + 1
                    
                    # 从占卜方法中统计
                    spread_chunks = spread_method.get('chunks', [])
                    for chunk in spread_chunks:
                        source = chunk.get('source', 'unknown')
                        chunks_by_source[source] = chunks_by_source.get(source, 0) + 1
                    
                    # 从牌之间的关系中统计
                    relationship_chunks = card_relationships.get('chunks', [])
                    for chunk in relationship_chunks:
                        source = chunk.get('source', 'unknown')
                        chunks_by_source[source] = chunks_by_source.get(source, 0) + 1
                    
                    test_log['rag_analysis']['chunks_by_source'] = chunks_by_source
                    
                    # 按查询类型统计
                    for query in rag_queries:
                        query_type = query.get('type', 'unknown')
                        chunks_by_query_type[query_type] = chunks_by_query_type.get(query_type, 0) + 1
                    
                    test_log['rag_analysis']['chunks_by_query_type'] = chunks_by_query_type
                    
                    print(f"\n📊 RAG检索分析:")
                    print(f"  - 总查询数: {len(rag_queries)}")
                    print(f"  - 去重前chunks数: {total_before}")
                    print(f"  - 去重后chunks数: {total_after}")
                    if total_before > 0:
                        print(f"  - 去重率: {dedup_rate:.2f}%")
                    print(f"  - 按来源分布: {chunks_by_source}")
                
                # 打印步骤摘要
                print(f"\n步骤 {step_data.get('step_order')}: {step_data.get('step_name')}")
                print(f"  - 处理时间: {step_data.get('processing_time_ms')}ms")
                if step_data.get('model_used'):
                    print(f"  - 模型: {step_data.get('model_used')}")
                if step_data.get('rag_queries'):
                    print(f"  - RAG查询数量: {len(step_data.get('rag_queries', []))}")
        
        # 计算总时间
        total_time_ms = int((time.time() - start_time) * 1000)
        test_log['total_time_ms'] = total_time_ms
        
        print(f"\n✅ 完整占卜流程完成 ({total_time_ms}ms)")
        print(f"✅ 占卜ID: {reading_id}")
        
        # 保存测试日志到文件
        log_filename = f"rag_no_intermediate_llm_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_dir = Path(__file__).parent / "result"
        result_dir.mkdir(exist_ok=True)
        log_path = result_dir / log_filename
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(test_log, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n✅ 测试日志已保存到: {log_path}")
        
        # 分析结果
        print("\n" + "="*80)
        print("RAG流程优化分析")
        print("="*80)
        
        rag_analysis = test_log['rag_analysis']
        print(f"\n📊 RAG检索统计:")
        print(f"  - 总查询数: {rag_analysis['total_queries']}")
        print(f"  - 去重前chunks数: {rag_analysis['total_chunks_before_dedup']}")
        print(f"  - 去重后chunks数: {rag_analysis['total_chunks_after_dedup']}")
        print(f"  - 去重率: {rag_analysis['deduplication_rate']:.2f}%")
        print(f"  - 按来源分布: {rag_analysis['chunks_by_source']}")
        print(f"  - 按查询类型分布: {rag_analysis['chunks_by_query_type']}")
        
        # 检查是否使用了中间LLM调用
        print(f"\n🔍 检查中间LLM调用:")
        rag_step = next((s for s in test_log['steps'] if s['step_name'] == 'rag_retrieval'), None)
        if rag_step:
            output_data = rag_step.get('output_data', {})
            card_info = output_data.get('card_information', {})
            
            has_rag_text = False
            has_chunks = False
            
            for card_id, card_data in card_info.items():
                if card_data.get('rag_text'):
                    has_rag_text = True
                if card_data.get('chunks'):
                    has_chunks = True
            
            if has_rag_text:
                print("  ⚠️ 发现rag_text字段（可能仍在使用中间LLM调用）")
            else:
                print("  ✅ 未发现rag_text字段（未使用中间LLM调用）")
            
            if has_chunks:
                print("  ✅ 发现chunks字段（使用原始chunks）")
            else:
                print("  ⚠️ 未发现chunks字段")
        
        # 检查最终解读prompt
        print(f"\n🔍 检查最终解读prompt:")
        interpretation_step = next((s for s in test_log['steps'] if s['step_name'] == 'final_interpretation'), None)
        if interpretation_step:
            prompt_content = interpretation_step.get('prompt_content', '')
            if 'RAG检索到的相关信息（原始文档片段）' in prompt_content:
                print("  ✅ Prompt包含原始文档片段")
            else:
                print("  ⚠️ Prompt可能不包含原始文档片段")
            
            # 统计prompt中的chunks数量
            chunk_count = prompt_content.count('[1]') + prompt_content.count('[2]') + prompt_content.count('[3]')
            print(f"  - Prompt中chunks数量（估算）: {chunk_count}")
        
        return test_log
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        error_traceback = traceback.format_exc()
        test_log['errors'].append({
            'error': str(e),
            'traceback': error_traceback
        })
        
        # 保存错误日志
        log_filename = f"rag_no_intermediate_llm_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        result_dir = Path(__file__).parent / "result"
        result_dir.mkdir(exist_ok=True)
        log_path = result_dir / log_filename
        
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(test_log, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"\n❌ 错误日志已保存到: {log_path}")
        traceback.print_exc()
        return test_log


async def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("RAG流程优化测试（不使用中间LLM调用）")
    print("="*80)
    print("\n此测试将验证：")
    print("  1. RAG检索不再调用中间LLM（只返回原始chunks）")
    print("  2. 所有chunks在最后统一去重")
    print("  3. 最终解读prompt使用原始chunks而不是LLM生成的答案")
    print("  4. 记录chunks收集和去重统计")
    print("\n请确保已配置环境变量（OPENROUTER_API_KEY或OPENAI_API_KEY）")
    print("请确保已配置Supabase连接（SUPABASE_URL和SUPABASE_SERVICE_ROLE_KEY）")
    print("="*80)
    
    try:
        # 运行测试
        test_log = await test_rag_no_intermediate_llm()
        
        print("\n" + "="*80)
        print("✅ 测试完成")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())




