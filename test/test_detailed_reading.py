"""
详细占卜测试脚本 - 记录所有过程中的输出信息
包括：问题分析、选牌、牌型分析、RAG检索、最终解读等所有步骤的详细信息
"""

import asyncio
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.tarot.reading_service import ReadingService
from app.models.schemas import UserProfileCreate
from app.services.rag import rag_service
from app.services.tarot.question_analyzer import QuestionAnalyzerService
from app.services.tarot.pattern_analyzer import PatternAnalyzerService


# 保存原始函数引用
_original_rag_answer_query = rag_service.answer_query
_original_question_analyze = QuestionAnalyzerService.analyze_question
_original_pattern_analyze_direct = PatternAnalyzerService.analyze_spread_pattern_direct
_original_pattern_analyze_rag = PatternAnalyzerService.analyze_spread_pattern_rag
_original_build_prompt = ReadingService._build_interpretation_prompt
_original_retrieve_card_info = ReadingService._retrieve_card_information
_original_retrieve_spread_method = ReadingService._retrieve_spread_method

# 全局logger实例（在test函数中设置）
_global_logger = None


def setup_logging_interceptors(logger_instance):
    """设置日志拦截器"""
    global _global_logger
    _global_logger = logger_instance
    
    # 拦截RAG查询
    async def intercepted_rag_answer_query(query: str, **kwargs):
        result = await _original_rag_answer_query(query, **kwargs)
        if _global_logger:
            _global_logger.log_rag_query(query, result)
        return result
    
    rag_service.answer_query = intercepted_rag_answer_query
    
    # 拦截问题分析
    async def intercepted_question_analyze(self, question: str, **kwargs):
        # 记录问题分析的prompt
        if _global_logger:
            user_profile = kwargs.get('user_profile')
            user_selected_spread = kwargs.get('user_selected_spread')
            analyze_complexity = user_selected_spread is None
            
            # 格式化用户信息
            user_profile_info = self._format_user_profile_info(user_profile)
            
            # 选择Prompt模板
            if analyze_complexity:
                prompt_template = self.QUESTION_ANALYSIS_PROMPT
            else:
                prompt_template = self.SIMPLIFIED_QUESTION_ANALYSIS_PROMPT
            
            # 构建Prompt
            prompt = prompt_template.format(
                question=question,
                user_profile_info=user_profile_info
            )
            
            _global_logger.log_prompt(
                'question_analysis',
                prompt,
                {
                    'question': question,
                    'user_profile': user_profile.model_dump() if user_profile else None,
                    'user_selected_spread': user_selected_spread,
                    'analyze_complexity': analyze_complexity
                }
            )
        
        result = await _original_question_analyze(self, question, **kwargs)
        return result
    
    QuestionAnalyzerService.analyze_question = intercepted_question_analyze
    
    # 拦截牌型分析（直接LLM）
    async def intercepted_pattern_analyze_direct(self, selected_cards, spread_type, question_domain):
        if _global_logger:
            spread_info = self._format_spread_info(selected_cards)
            prompt = self.PATTERN_ANALYSIS_PROMPT.format(
                spread_type=spread_type,
                question_domain=question_domain,
                spread_info=spread_info
            )
            _global_logger.log_prompt(
                'pattern_analysis_direct',
                prompt,
                {
                    'spread_type': spread_type,
                    'question_domain': question_domain,
                    'cards_count': len(selected_cards)
                }
            )
        return await _original_pattern_analyze_direct(self, selected_cards, spread_type, question_domain)
    
    PatternAnalyzerService.analyze_spread_pattern_direct = intercepted_pattern_analyze_direct
    
    # 拦截牌型分析（RAG增强）
    async def intercepted_pattern_analyze_rag(self, selected_cards, spread_type, question_domain):
        if _global_logger:
            spread_info = self._format_spread_info(selected_cards)
            # 构建查询
            query = f"{spread_type} spread tarot divination method pattern analysis"
            # 这里我们暂时不记录RAG查询，因为会在answer_query中记录
            # 记录prompt
            rag_context = f"[RAG context will be retrieved for: {query}]"
            prompt = self.RAG_ENHANCED_PATTERN_ANALYSIS_PROMPT.format(
                spread_type=spread_type,
                question_domain=question_domain,
                spread_info=spread_info,
                rag_context=rag_context
            )
            _global_logger.log_prompt(
                'pattern_analysis_rag',
                prompt,
                {
                    'spread_type': spread_type,
                    'question_domain': question_domain,
                    'cards_count': len(selected_cards),
                    'rag_query': query
                }
            )
        return await _original_pattern_analyze_rag(self, selected_cards, spread_type, question_domain)
    
    PatternAnalyzerService.analyze_spread_pattern_rag = intercepted_pattern_analyze_rag
    
    # 拦截最终解读prompt构建
    def intercepted_build_prompt(self, question, question_analysis, selected_cards, pattern_analysis_dict, card_information, spread_method, user_profile=None):
        prompt = _original_build_prompt(self, question, question_analysis, selected_cards, pattern_analysis_dict, card_information, spread_method, user_profile)
        if _global_logger:
            _global_logger.log_prompt(
                'final_interpretation',
                prompt,
                {
                    'question': question,
                    'spread_type': spread_method.get('spread_type'),
                    'cards_count': len(selected_cards),
                    'pattern_analysis_method': pattern_analysis_dict.get('analysis_method')
                }
            )
        return prompt
    
    ReadingService._build_interpretation_prompt = intercepted_build_prompt


def cleanup_logging_interceptors():
    """清理日志拦截器"""
    rag_service.answer_query = _original_rag_answer_query
    QuestionAnalyzerService.analyze_question = _original_question_analyze
    PatternAnalyzerService.analyze_spread_pattern_direct = _original_pattern_analyze_direct
    PatternAnalyzerService.analyze_spread_pattern_rag = _original_pattern_analyze_rag
    ReadingService._build_interpretation_prompt = _original_build_prompt


class DetailedReadingLogger:
    """详细记录占卜过程中的所有信息"""
    
    def __init__(self):
        self.logs = {
            'timestamp': datetime.now().isoformat(),
            'steps': [],
            'prompts': {},  # 记录所有prompt
            'rag_queries': [],  # 记录所有RAG查询
            'final_result': None
        }
    
    def log_step(self, step_name: str, data: dict):
        """记录一个步骤的信息"""
        step_log = {
            'step': step_name,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.logs['steps'].append(step_log)
        print(f"\n{'='*80}")
        print(f"步骤: {step_name}")
        print(f"{'='*80}")
        self._print_dict(data, indent=2)
    
    def log_prompt(self, prompt_type: str, prompt: str, context: Optional[dict] = None):
        """记录prompt信息"""
        self.logs['prompts'][prompt_type] = {
            'prompt': prompt,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        }
        print(f"\n{'='*80}")
        print(f"Prompt: {prompt_type}")
        print(f"{'='*80}")
        print(prompt)
        if context:
            print("\n上下文:")
            self._print_dict(context, indent=2)
    
    def log_rag_query(self, query: str, result: dict):
        """记录RAG查询"""
        rag_log = {
            'query': query,
            'result': result,
            'timestamp': datetime.now().isoformat()
        }
        self.logs['rag_queries'].append(rag_log)
        print(f"\n{'='*80}")
        print(f"RAG查询: {query[:100]}...")
        print(f"{'='*80}")
        print(f"结果: {result.get('text', '')[:300]}...")
        print(f"引用来源数量: {len(result.get('citations', []))}")
    
    def log_final_result(self, result: dict):
        """记录最终结果"""
        self.logs['final_result'] = result
        print(f"\n{'='*80}")
        print("最终结果")
        print(f"{'='*80}")
        self._print_dict(result, indent=2)
    
    def save_to_file(self, filename: str):
        """保存日志到文件"""
        result_dir = Path(__file__).parent / "result"
        result_dir.mkdir(exist_ok=True)
        output_path = result_dir / filename
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 详细日志已保存到: {output_path}")
    
    def _print_dict(self, data: dict, indent: int = 0):
        """格式化打印字典"""
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                print(f"{prefix}{key}:")
                self._print_dict(value, indent + 1)
            elif isinstance(value, list):
                print(f"{prefix}{key}:")
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        print(f"{prefix}  [{i}]:")
                        self._print_dict(item, indent + 2)
                    else:
                        print(f"{prefix}  [{i}]: {item}")
            else:
                # 处理长文本
                if isinstance(value, str) and len(value) > 200:
                    print(f"{prefix}{key}:")
                    print(f"{prefix}  {value[:200]}...")
                    print(f"{prefix}  [全文长度: {len(value)} 字符]")
                else:
                    print(f"{prefix}{key}: {value}")


async def test_detailed_reading():
    """详细占卜测试 - 记录所有过程输出"""
    
    logger = DetailedReadingLogger()
    
    # 设置日志拦截器
    setup_logging_interceptors(logger)
    
    try:
        # 初始化服务
        service = ReadingService()
        
        # 设置问题
        question = "我这次比赛的结果会好吗"
        
        logger.log_step("输入问题", {
            'question': question,
            'note': '用户询问比赛结果'
        })
        
        # 创建用户信息（可选）
        user_profile = UserProfileCreate(
            age=25,
            gender="male",
            zodiac_sign="Sagittarius",
            appearance_type="wands",
            personality_type="wands",
            preferred_source="pkt"
        )
        
        logger.log_step("用户信息", {
            'age': user_profile.age,
            'gender': user_profile.gender,
            'zodiac_sign': user_profile.zodiac_sign,
            'appearance_type': user_profile.appearance_type,
            'personality_type': user_profile.personality_type,
            'preferred_source': user_profile.preferred_source
        })
        
        # 开始占卜
        start_time = time.time()
        
        result = await service.create_reading(
            question=question,
            user_id=None,
            user_selected_spread=None,  # 让系统自动选择
            user_profile=user_profile,
            use_rag_for_pattern=True,  # 使用RAG增强分析
            preferred_source="pkt"
        )
        
        elapsed_time = time.time() - start_time
        
        # 记录每个步骤的结果
        logger.log_step("问题分析结果", {
            'question_domain': result.get('question_analysis', {}).get('question_domain'),
            'complexity': result.get('question_analysis', {}).get('complexity'),
            'question_type': result.get('question_analysis', {}).get('question_type'),
            'recommended_spread': result.get('question_analysis', {}).get('recommended_spread'),
            'reasoning': result.get('question_analysis', {}).get('reasoning'),
            'question_summary': result.get('question_analysis', {}).get('question_summary'),
            'auto_selected_spread': result.get('question_analysis', {}).get('auto_selected_spread')
        })
        
        logger.log_step("占卜方式", {
            'spread_type': result.get('spread_type'),
            'spread_reason': result.get('question_analysis', {}).get('reasoning')
        })
        
        # 记录代表牌
        if result.get('significator'):
            sig = result.get('significator')
            logger.log_step("代表牌选择", {
                'card_name_en': sig.get('card_name_en'),
                'card_name_cn': sig.get('card_name_cn'),
                'selection_reason': sig.get('selection_reason')
            })
        
        # 记录选中的牌
        cards = result.get('cards', [])
        logger.log_step("抽取的牌", {
            'total_cards': len(cards),
            'cards': [
                {
                    'position_order': card.get('position_order'),
                    'position': card.get('position'),
                    'position_description': card.get('position_description'),
                    'card_name_en': card.get('card_name_en'),
                    'card_name_cn': card.get('card_name_cn'),
                    'suit': card.get('suit'),
                    'card_number': card.get('card_number'),
                    'arcana': card.get('arcana'),
                    'is_reversed': card.get('is_reversed')
                }
                for card in cards
            ]
        })
        
        # 记录牌型分析
        pattern_analysis = result.get('pattern_analysis', {})
        logger.log_step("牌型分析结果", {
            'analysis_method': pattern_analysis.get('analysis_method'),
            'position_relationships': pattern_analysis.get('position_relationships', {}),
            'number_patterns': pattern_analysis.get('number_patterns', {}),
            'suit_distribution': pattern_analysis.get('suit_distribution', {}),
            'major_arcana_patterns': pattern_analysis.get('major_arcana_patterns', {}),
            'reversed_patterns': pattern_analysis.get('reversed_patterns', {}),
            'special_combinations': pattern_analysis.get('special_combinations', [])
        })
        
        # 记录最终解读
        interpretation = result.get('interpretation', {})
        logger.log_step("最终解读", {
            'overall_summary': interpretation.get('overall_summary'),
            'position_interpretations': [
                {
                    'position': pos.get('position'),
                    'position_order': pos.get('position_order'),
                    'card_name_en': pos.get('card_name_en'),
                    'card_name_cn': pos.get('card_name_cn'),
                    'interpretation': pos.get('interpretation')
                }
                for pos in interpretation.get('position_interpretations', [])
            ],
            'relationship_analysis': interpretation.get('relationship_analysis'),
            'pattern_explanation': interpretation.get('pattern_explanation'),
            'advice': interpretation.get('advice'),
            'references': [
                {
                    'type': ref.get('type'),
                    'card_name': ref.get('card_name'),
                    'method': ref.get('method'),
                    'source': ref.get('source')
                }
                for ref in interpretation.get('references', [])
            ]
        })
        
        # 记录元数据
        metadata = result.get('metadata', {})
        logger.log_step("处理元数据", {
            'processing_time_ms': metadata.get('processing_time_ms'),
            'actual_elapsed_ms': int(elapsed_time * 1000),
            'pattern_analysis_method': metadata.get('pattern_analysis_method'),
            'reading_id': result.get('reading_id')
        })
        
        # 记录最终结果
        logger.log_final_result({
            'reading_id': result.get('reading_id'),
            'question': result.get('question'),
            'spread_type': result.get('spread_type'),
            'total_processing_time_ms': int(elapsed_time * 1000),
            'steps_completed': len(logger.logs['steps'])
        })
        
        # 保存到文件
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.save_to_file(f"detailed_reading_log_{timestamp_str}.json")
        
        # 也打印一个简化的总结
        print("\n" + "="*80)
        print("占卜总结")
        print("="*80)
        print(f"\n问题: {question}")
        print(f"\n占卜方式: {result.get('spread_type')}")
        if result.get('significator'):
            sig = result.get('significator')
            print(f"\n代表牌: {sig.get('card_name_en')} ({sig.get('card_name_cn', '')})")
            print(f"选择原因: {sig.get('selection_reason', '')[:100]}...")
        
        print(f"\n选中的牌 ({len(cards)}张):")
        for card in cards:
            card_str = f"  {card['position_order']}. {card['position']}: {card['card_name_en']}"
            if card.get('card_name_cn'):
                card_str += f" ({card['card_name_cn']})"
            if card.get('is_reversed'):
                card_str += " [逆位]"
            print(card_str)
        
        print(f"\n整体解读:")
        print(f"  {interpretation.get('overall_summary', '')[:300]}...")
        
        print(f"\n处理时间: {int(elapsed_time * 1000)}ms")
        
        return result
        
    except Exception as e:
        logger.log_step("错误", {
            'error_type': type(e).__name__,
            'error_message': str(e)
        })
        import traceback
        error_trace = traceback.format_exc()
        logger.log_step("错误堆栈", {
            'traceback': error_trace
        })
        
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.save_to_file(f"detailed_reading_error_{timestamp_str}.json")
        
        print(f"\n❌ 占卜失败: {e}")
        traceback.print_exc()
        raise
    finally:
        # 清理拦截器
        cleanup_logging_interceptors()


async def main():
    """主函数"""
    print("\n" + "="*80)
    print("详细占卜测试 - 记录所有过程输出")
    print("="*80)
    print("\n此测试将:")
    print("  1. 进行一次完整的占卜")
    print("  2. 记录所有过程中的输出信息")
    print("  3. 包括：问题分析、选牌、牌型分析、RAG检索、最终解读等")
    print("  4. 保存详细日志到JSON文件")
    print("\n问题: 我这次比赛的结果会好吗")
    print("="*80)
    
    try:
        result = await test_detailed_reading()
        print("\n" + "="*80)
        print("✅ 占卜测试完成")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

