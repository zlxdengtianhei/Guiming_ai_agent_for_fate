"""
占卜主服务 - 协调所有步骤，整合问题分析、选牌、牌型分析、RAG检索和最终解读
"""

import logging
import time
import uuid
import asyncio
from typing import Optional, List, Dict, Any, Tuple, AsyncGenerator
from datetime import datetime
from app.core.database import get_supabase_service
from app.services.tarot.card_selection import CardSelectionService, SelectedCard
from app.services.tarot.significator import SignificatorService
from app.services.tarot.question_analyzer import QuestionAnalyzerService
from app.services.tarot.pattern_analyzer import PatternAnalyzerService
from app.services.rag import rag_service
from app.services.chat import chat_service
from app.core.config import settings
from app.core.model_config import get_model_config
from app.models.schemas import (
    UserProfileCreate, QuestionAnalysis, SpreadPatternAnalysis,
    FinalInterpretation, InterpretationReference, PositionInterpretation
)

logger = logging.getLogger(__name__)


def _get_interpretation_model_from_user_preference(
    user_preference: Optional[str],
    default_model: str
) -> str:
    """
    根据用户偏好获取最终解读模型名称
    
    Args:
        user_preference: 用户选择的模型 ('deepseek'/'gpt4omini'/'gemini_2.5_pro')
        default_model: 默认模型（从model_config获取）
        
    Returns:
        实际的模型名称（根据use_openrouter自动调整格式）
    """
    if not user_preference:
        # 默认使用 gpt4omini
        model_mapping = {
            'gpt4omini': 'openai/gpt-4o-mini',
        }
        model_name = model_mapping.get('gpt4omini', default_model)
        if settings.use_openrouter:
            return model_name
        else:
            if '/' in model_name:
                return model_name.split('/', 1)[1]
            return model_name
    
    # 模型映射：用户选择 -> 实际模型名称
    model_mapping = {
        'deepseek': 'deepseek/deepseek-r1',
        'gpt4omini': 'openai/gpt-4o-mini',
        'gemini_2.5_pro': 'google/gemini-2.5-pro',
    }
    
    if user_preference not in model_mapping:
        logger.warning(f"Unknown interpretation model preference: {user_preference}, using default")
        return default_model
    
    model_name = model_mapping[user_preference]
    
    # 如果使用OpenRouter，返回完整路径；否则返回模型名（去掉provider前缀）
    if settings.use_openrouter:
        return model_name
    else:
        # 去掉provider前缀（如 "openai/gpt-4o-mini" -> "gpt-4o-mini"）
        if '/' in model_name:
            return model_name.split('/', 1)[1]
        return model_name


class ReadingService:
    """占卜主服务 - 协调所有步骤"""
    
    def __init__(self):
        self.supabase = get_supabase_service()
        self.card_selection = CardSelectionService()
        self.significator = SignificatorService()
        self.question_analyzer = QuestionAnalyzerService()
        self.pattern_analyzer = PatternAnalyzerService()
        # RAG查询并发限制（最多同时10个查询，提升并行性能）
        # 注意：如果遇到API限流，可以降低这个值
        self._rag_semaphore = asyncio.Semaphore(10)
    
    async def create_reading(
        self,
        question: str,
        user_id: Optional[str] = None,
        user_selected_spread: Optional[str] = None,
        user_profile: Optional[UserProfileCreate] = None,
        preferred_source: str = 'pkt',  # 偏好的数据源
        source_page: Optional[str] = None,  # 占卜来源页面
        use_rag_for_pattern: Optional[bool] = False  # 是否使用RAG进行牌型分析
    ) -> Dict[str, Any]:
        """
        创建完整的占卜
        
        步骤：
        1. 创建reading记录（status='pending'）
        2. 分析问题（question_analyzer）
        3. 选择占卜方式（用户指定或系统推荐）
        4. 选择代表牌（significator）
        5. 选牌（card_selection）
        6. 保存牌到reading_cards表
        7. 分析牌型（pattern_analyzer）- 支持两种方式
        8. RAG检索（检索卡牌信息和占卜方法）
        9. 生成最终解读（chat_service）
        10. 更新reading记录（status='completed'）
        
        Args:
            question: 用户问题
            user_id: 用户ID（可选）
            user_selected_spread: 用户指定的占卜方式（可选）
            user_profile: 用户信息（可选）
            use_rag_for_pattern: 是否使用RAG进行牌型分析（默认False，使用直接LLM）
            preferred_source: 偏好的数据源（'pkt'或'78degrees'）
            
        Returns:
            完整的占卜结果字典
        """
        reading_id = None
        start_time = time.time()
        
        try:
            # Step 1: 创建reading记录
            logger.info(f"Creating reading for question: {question[:50]}...")
            reading_id = str(uuid.uuid4())
            
            reading_data = {
                'id': reading_id,
                'question': question,
                'spread_type': user_selected_spread or 'three_card',  # 临时值，后续会更新
                'user_id': user_id,
                'status': 'pending',
                'source_page': source_page,  # 保存来源页面
                'created_at': datetime.utcnow().isoformat()
            }
            
            # 插入reading记录
            reading_data['current_step'] = 'question_analysis'
            self.supabase.table('readings').insert(reading_data).execute()
            logger.info(f"Reading record created: {reading_id}")
            
            # Step 2: 分析问题
            logger.info("Step 2: Analyzing question...")
            step_start_time = time.time()
            
            # 调用问题分析，获取完整结果（包括prompt和response）
            question_analysis_result = await self.question_analyzer.analyze_question_with_details(
                question=question,
                user_profile=user_profile,
                user_selected_spread=user_selected_spread
            )
            
            question_analysis = question_analysis_result['analysis']
            prompt_content = question_analysis_result.get('prompt')
            llm_response = question_analysis_result.get('llm_response')
            processing_time_ms = question_analysis_result.get('processing_time_ms', int((time.time() - step_start_time) * 1000))
            model_used = question_analysis_result.get('model_used')  # 获取实际使用的模型
            
            # 确定最终使用的占卜方式
            final_spread = (
                user_selected_spread if user_selected_spread and user_selected_spread != 'auto'
                else question_analysis.recommended_spread or 'three_card'
            )
            
            # 保存过程数据（包含prompt和LLM response）
            await self._save_process_data(
                reading_id=reading_id,
                step_name='question_analysis',
                step_order=2,
                input_data={
                    'question': question,
                    'user_profile': user_profile.model_dump() if user_profile else None,
                    'user_selected_spread': user_selected_spread
                },
                output_data={
                    'analysis': question_analysis.model_dump(),
                    'llm_response': llm_response
                },
                prompt_type='question_analysis',
                prompt_content=prompt_content,
                model_used=model_used,  # 使用实际模型名称
                temperature=0.3,
                processing_time_ms=processing_time_ms
            )
            
            # 更新reading记录
            update_data = {
                'question_domain': question_analysis.question_domain,
                'question_complexity': question_analysis.complexity,
                'question_summary': question_analysis.question_summary,
                'spread_type': final_spread,
                'auto_selected_spread': question_analysis.auto_selected_spread,
                'spread_reason': question_analysis.reasoning,
                'current_step': 'card_selection',
                'question_analyzed_at': datetime.utcnow().isoformat()
            }
            self.supabase.table('readings').update(update_data).eq('id', reading_id).execute()
            
            # Step 3: 选择代表牌（仅十字占卜需要代表牌，三牌占卜不需要）
            significator_card = None
            significator_reason = None
            
            if final_spread == 'celtic_cross':
                logger.info("Step 3: Selecting significator for Celtic Cross spread...")
                if user_profile:
                    significator_priority = user_profile.significator_priority or 'question_first'
                    significator_card, significator_reason = await self.significator.select_significator(
                        age=user_profile.age,
                        gender=user_profile.gender,
                        zodiac_sign=user_profile.zodiac_sign,
                        personality_type=user_profile.personality_type,
                        question_domain=question_analysis.question_domain,
                        significator_priority=significator_priority,
                        source=preferred_source
                    )
                    
                    # 更新reading记录
                    update_data = {
                        'significator_card_id': significator_card['id'],
                        'significator_selection_reason': significator_reason
                    }
                    self.supabase.table('readings').update(update_data).eq('id', reading_id).execute()
                else:
                    logger.warning("No user profile provided, skipping significator selection")
            else:
                logger.info(f"Step 3: Skipping significator selection ({final_spread} spread doesn't use significator)")
            
            # Step 4: 选牌
            logger.info(f"Step 4: Selecting cards for spread: {final_spread}")
            
            # 获取牌堆
            deck = await self.card_selection.get_deck_from_database(source=preferred_source)
            
            # 移除代表牌（仅十字占卜需要移除代表牌）
            if final_spread == 'celtic_cross' and significator_card:
                remaining_deck = self.card_selection.remove_significator_from_deck(
                    deck, significator_card
                )
            else:
                remaining_deck = deck.copy()
            
            # 洗牌和切牌
            shuffled_deck = await self.card_selection.shuffle_and_cut_deck(remaining_deck)
            
            # 选牌
            selected_cards = await self.card_selection.select_cards_for_spread(
                spread_type=final_spread,
                shuffled_deck=shuffled_deck,
                significator=significator_card
            )
            
            # Step 5: 保存牌到reading_cards表
            logger.info(f"Step 5: Saving {len(selected_cards)} cards to database...")
            
            reading_cards_data = []
            for card in selected_cards:
                reading_cards_data.append({
                    'reading_id': reading_id,
                    'card_id': card.card_id,
                    'position': card.position,
                    'position_order': card.position_order,
                    'position_description': card.position_description,
                    'is_reversed': card.is_reversed,
                    'card_selected_at': datetime.utcnow().isoformat()
                })
            
            if reading_cards_data:
                # 批量插入reading_cards记录
                self.supabase.table('reading_cards').insert(reading_cards_data).execute()
            
            # 更新reading记录
            update_data = {
                'status': 'card_selected',
                'current_step': 'pattern_analysis',
                'cards_selected_at': datetime.utcnow().isoformat()
            }
            self.supabase.table('readings').update(update_data).eq('id', reading_id).execute()
            
            # Step 6: 分析牌型（纯代码实现）
            logger.info("Step 6: Analyzing spread pattern (code-based analysis)...")
            step_start_time = time.time()
            
            # 使用纯代码分析牌型
            pattern_analysis_dict = self._analyze_spread_pattern_code(
                selected_cards=selected_cards,
                spread_type=final_spread,
                question_domain=question_analysis.question_domain
            )
            
            processing_time_ms = int((time.time() - step_start_time) * 1000)
            
            # 保存过程数据
            await self._save_process_data(
                reading_id=reading_id,
                step_name='pattern_analysis',
                step_order=6,
                input_data={
                    'selected_cards': [self._selected_card_to_dict(card) for card in selected_cards],
                    'spread_type': final_spread,
                    'question_domain': question_analysis.question_domain,
                    'analysis_method': 'code_based'
                },
                output_data={
                    'analysis': pattern_analysis_dict
                },
                processing_time_ms=processing_time_ms
            )
            
            # 更新reading记录
            update_data = {
                'spread_pattern_analysis': pattern_analysis_dict,
                'current_step': 'rag_retrieval',
                'analysis_completed_at': datetime.utcnow().isoformat()
            }
            self.supabase.table('readings').update(update_data).eq('id', reading_id).execute()
            
            # Step 7: RAG检索（并行执行 - 增强版）
            logger.info("Step 7: Retrieving card information via RAG (enhanced)...")
            step_start_time = time.time()
            
            # 记录RAG查询
            rag_queries = []
            # 并行执行卡牌信息检索、占卜方法检索和牌之间的关系检索
            card_information, spread_method, card_relationships = await asyncio.gather(
                self._retrieve_card_information(selected_cards, rag_queries),
                self._retrieve_spread_method(final_spread, rag_queries),
                self._retrieve_card_relationships(selected_cards, rag_queries)
            )
            
            # 收集所有chunks并去重（跨所有RAG查询）
            logger.info("Collecting and deduplicating all RAG chunks...")
            all_chunks = []
            
            # 从卡牌信息中收集chunks
            for card_info in card_information.values():
                chunks = card_info.get('chunks', [])
                all_chunks.extend(chunks)
            
            # 从占卜方法中收集chunks
            spread_chunks = spread_method.get('chunks', [])
            all_chunks.extend(spread_chunks)
            
            # 从牌之间的关系中收集chunks
            relationship_chunks = card_relationships.get('chunks', [])
            all_chunks.extend(relationship_chunks)
            
            # 全局去重（基于chunk_id，保留相似度最高的）
            seen_chunk_ids = {}
            unique_chunks = []
            for chunk in all_chunks:
                chunk_id = chunk.get('chunk_id', '')
                if chunk_id:
                    if chunk_id not in seen_chunk_ids:
                        seen_chunk_ids[chunk_id] = chunk
                        unique_chunks.append(chunk)
                    else:
                        # 如果已存在，比较相似度，保留更高的
                        existing_sim = seen_chunk_ids[chunk_id].get('similarity', 0)
                        new_sim = chunk.get('similarity', 0)
                        if new_sim > existing_sim:
                            # 替换为相似度更高的chunk
                            unique_chunks.remove(seen_chunk_ids[chunk_id])
                            seen_chunk_ids[chunk_id] = chunk
                            unique_chunks.append(chunk)
            
            # 按相似度排序（降序）
            unique_chunks.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            
            logger.info(f"Collected {len(all_chunks)} chunks, deduplicated to {len(unique_chunks)} unique chunks")
            
            # 保存RAG检索过程数据
            await self._save_process_data(
                reading_id=reading_id,
                step_name='rag_retrieval',
                step_order=7,
                input_data={
                    'selected_cards': [self._selected_card_to_dict(card) for card in selected_cards],
                    'spread_type': final_spread
                },
                output_data={
                    'card_information': card_information,
                    'spread_method': spread_method,
                    'card_relationships': card_relationships,
                    'total_chunks_before_dedup': len(all_chunks),
                    'total_chunks_after_dedup': len(unique_chunks)
                },
                rag_queries=rag_queries,
                processing_time_ms=int((time.time() - step_start_time) * 1000)
            )
            
            # Step 7.5: 生成牌阵意象描述
            logger.info("Step 7.5: Generating spread imagery description...")
            step_start_time_imagery = time.time()
            
            # 从RAG查询结果中提取视觉描述并生成意象描述
            spread_imagery_description = await self._generate_spread_imagery_description(
                selected_cards=selected_cards,
                card_information=card_information,
                question_domain=question_analysis.question_domain,
                rag_queries=rag_queries
            )
            
            processing_time_ms_imagery = int((time.time() - step_start_time_imagery) * 1000)
            
            # 保存意象描述生成过程数据（包含prompt和LLM response）
            imagery_prompt = getattr(self, '_last_imagery_prompt', None)
            imagery_llm_response = getattr(self, '_last_imagery_llm_response', None)
            imagery_model = getattr(self, '_last_imagery_model', None)  # 获取实际使用的模型
            
            await self._save_process_data(
                reading_id=reading_id,
                step_name='imagery_description',
                step_order=8,  # 在RAG检索之后，最终解读之前
                input_data={
                    'selected_cards': [self._selected_card_to_dict(card) for card in selected_cards],
                    'question_domain': question_analysis.question_domain
                },
                output_data={
                    'imagery_description': spread_imagery_description,
                    'llm_response': imagery_llm_response  # 保存LLM响应
                },
                prompt_type='imagery_description',
                prompt_content=imagery_prompt,  # 保存prompt
                model_used=imagery_model,  # 使用实际模型名称
                temperature=0.7,
                processing_time_ms=processing_time_ms_imagery
            )
            
            logger.info(f"Spread imagery description generated in {processing_time_ms_imagery}ms")
            
            # Step 8: 生成最终解读
            logger.info("Step 8: Generating final interpretation...")
            step_start_time = time.time()
            
            # 构建prompt（用于记录）- 使用去重后的所有chunks，包含意象描述
            user_language = user_profile.language if user_profile and user_profile.language else 'zh'
            interpretation_prompt = self._build_interpretation_prompt(
                question=question,
                question_analysis=question_analysis,
                selected_cards=selected_cards,
                pattern_analysis_dict=pattern_analysis_dict,
                card_information=card_information,
                spread_method=spread_method,
                card_relationships=card_relationships,
                user_profile=user_profile,
                all_chunks=unique_chunks,  # 传递去重后的所有chunks
                spread_imagery_description=spread_imagery_description,  # 传递意象描述
                language=user_language
            )
            
            # 生成最终解读，获取完整结果（包括LLM response）
            interpretation_result = await self._generate_final_interpretation_with_details(
                question=question,
                question_analysis=question_analysis,
                selected_cards=selected_cards,
                pattern_analysis_dict=pattern_analysis_dict,
                card_information=card_information,
                spread_method=spread_method,
                card_relationships=card_relationships,
                user_profile=user_profile,
                prompt=interpretation_prompt
            )
            
            final_interpretation = interpretation_result['interpretation']
            llm_response = interpretation_result.get('llm_response')
            processing_time_ms = interpretation_result.get('processing_time_ms', int((time.time() - step_start_time) * 1000))
            model_used = interpretation_result.get('model_used')  # 获取实际使用的模型
            
            # 保存过程数据（包含prompt和LLM response）
            await self._save_process_data(
                reading_id=reading_id,
                step_name='final_interpretation',
                step_order=9,  # 更新为9（意象描述是8）
                input_data={
                    'question': question,
                    'question_analysis': question_analysis.model_dump(),
                    'selected_cards': [self._selected_card_to_dict(card) for card in selected_cards],
                    'pattern_analysis': pattern_analysis_dict,
                    'card_information': card_information,
                    'spread_method': spread_method
                },
                output_data={
                    'interpretation': final_interpretation.model_dump(),
                    'llm_response': llm_response
                },
                prompt_type='final_interpretation',
                prompt_content=interpretation_prompt,
                model_used=model_used,  # 使用实际模型名称
                temperature=0.7,
                processing_time_ms=processing_time_ms
            )
            
            # Step 9: 更新reading记录
            logger.info("Step 9: Updating reading record...")
            interpretation_metadata = {
                'references': [ref.dict() for ref in final_interpretation.references],
                'pattern_analysis_method': pattern_analysis_dict.get('analysis_method'),
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
            
            # 获取完整的LLM输出文本（从interpretation_result中获取）
            interpretation_text = interpretation_result.get('llm_response', '')
            if not interpretation_text and final_interpretation.overall_summary:
                interpretation_text = final_interpretation.overall_summary
            
            # 生成摘要（前500字符，用于预览或隐藏数据）
            interpretation_summary = interpretation_text[:500] if len(interpretation_text) > 500 else interpretation_text
            
            update_data = {
                'interpretation': interpretation_text,  # 只保存LLM的原始输出，不包含位置解读、关系分析等中间数据
                'interpretation_full_text': interpretation_text,  # 完整的LLM原始输出
                'interpretation_summary': interpretation_summary,  # 摘要（隐藏数据）
                'interpretation_metadata': interpretation_metadata,
                'status': 'completed',
                'current_step': 'interpretation',
                'interpreted_at': datetime.utcnow().isoformat()
            }
            self.supabase.table('readings').update(update_data).eq('id', reading_id).execute()
            
            # Step 10: 返回完整结果
            total_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Reading completed successfully in {total_time_ms}ms")
            
            return {
                'reading_id': reading_id,
                'question': question,
                'question_analysis': question_analysis.dict(),
                'spread_type': final_spread,
                'significator': {
                    'card_name_en': significator_card['card_name_en'] if significator_card else None,
                    'card_name_cn': significator_card.get('card_name_cn'),
                    'selection_reason': significator_reason
                } if significator_card else None,
                'cards': [self._selected_card_to_dict(card) for card in selected_cards],
                'pattern_analysis': pattern_analysis_dict,
                'interpretation': final_interpretation.dict(),
                'metadata': {
                    'created_at': datetime.utcnow().isoformat(),
                    'processing_time_ms': total_time_ms,
                    'pattern_analysis_method': pattern_analysis_dict.get('analysis_method')
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create reading: {e}")
            # 更新reading记录为error状态
            if reading_id:
                try:
                    self.supabase.table('readings').update({
                        'status': 'error',
                        'interpretation': f"Error: {str(e)}"
                    }).eq('id', reading_id).execute()
                except Exception as update_error:
                    logger.error(f"Failed to update reading status to error: {update_error}")
            raise
    
    async def create_reading_stream(
        self,
        question: str,
        user_id: Optional[str] = None,
        user_selected_spread: Optional[str] = None,
        user_profile: Optional[UserProfileCreate] = None,
        preferred_source: str = 'pkt',
        source_page: Optional[str] = None,  # 占卜来源页面
        use_rag_for_pattern: Optional[bool] = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        创建完整的占卜（流式输出版本）
        
        执行完整的占卜流程，但最终解读部分以流式方式输出。
        每个步骤完成后会发送进度更新。
        
        Yields:
            - {'type': 'progress', 'step': 'started', 'data': {...}}
            - {'type': 'progress', 'step': 'question_analysis', 'data': {...}}
            - {'type': 'progress', 'step': 'cards_selected', 'data': {...}}
            - {'type': 'progress', 'step': 'pattern_analyzed', 'data': {...}}
            - {'type': 'progress', 'step': 'rag_retrieved', 'data': {...}}
            - {'type': 'progress', 'step': 'interpretation_started', 'data': {...}}
            - {'type': 'interpretation', 'text': '...'}  # 流式文本块
            - {'type': 'complete', 'data': {...}}
            - {'type': 'error', 'error': '...'}  # 如果出错
        """
        reading_id = None
        start_time = time.time()
        
        try:
            # Step 1: 创建reading记录
            logger.info(f"Creating reading for question: {question[:50]}...")
            reading_id = str(uuid.uuid4())
            
            reading_data = {
                'id': reading_id,
                'question': question,
                'spread_type': user_selected_spread or 'three_card',
                'user_id': user_id,
                'status': 'pending',
                'source_page': source_page,  # 保存来源页面
                'created_at': datetime.utcnow().isoformat(),
                'current_step': 'question_analysis'
            }
            
            self.supabase.table('readings').insert(reading_data).execute()
            logger.info(f"Reading record created: {reading_id}")
            
            yield {
                'type': 'progress',
                'step': 'started',
                'data': {
                    'reading_id': reading_id,
                    'message': '开始占卜...'
                }
            }
            
            # Step 2: 分析问题
            logger.info("Step 2: Analyzing question...")
            step_start_time = time.time()
            
            question_analysis_result = await self.question_analyzer.analyze_question_with_details(
                question=question,
                user_profile=user_profile,
                user_selected_spread=user_selected_spread
            )
            
            question_analysis = question_analysis_result['analysis']
            prompt_content = question_analysis_result.get('prompt')
            llm_response = question_analysis_result.get('llm_response')
            processing_time_ms = question_analysis_result.get('processing_time_ms', int((time.time() - step_start_time) * 1000))
            model_used = question_analysis_result.get('model_used')  # 获取实际使用的模型
            
            final_spread = (
                user_selected_spread if user_selected_spread and user_selected_spread != 'auto'
                else question_analysis.recommended_spread or 'three_card'
            )
            
            await self._save_process_data(
                reading_id=reading_id,
                step_name='question_analysis',
                step_order=2,
                input_data={
                    'question': question,
                    'user_profile': user_profile.model_dump() if user_profile else None,
                    'user_selected_spread': user_selected_spread
                },
                output_data={
                    'analysis': question_analysis.model_dump(),
                    'llm_response': llm_response
                },
                prompt_type='question_analysis',
                prompt_content=prompt_content,
                model_used=model_used,  # 使用实际模型名称
                temperature=0.3,
                processing_time_ms=processing_time_ms
            )
            
            update_data = {
                'question_domain': question_analysis.question_domain,
                'question_complexity': question_analysis.complexity,
                'question_summary': question_analysis.question_summary,
                'spread_type': final_spread,
                'auto_selected_spread': question_analysis.auto_selected_spread,
                'spread_reason': question_analysis.reasoning,
                'current_step': 'card_selection',
                'question_analyzed_at': datetime.utcnow().isoformat()
            }
            self.supabase.table('readings').update(update_data).eq('id', reading_id).execute()
            
            yield {
                'type': 'progress',
                'step': 'question_analysis',
                'data': {
                    'question_analysis': question_analysis.model_dump(),
                    'spread_type': final_spread,
                    'message': '问题分析完成'
                }
            }
            
            # Step 3: 选择代表牌（仅十字占卜需要代表牌）
            significator_card = None
            significator_reason = None
            
            if final_spread == 'celtic_cross':
                logger.info("Step 3: Selecting significator for Celtic Cross spread...")
                if user_profile:
                    significator_priority = user_profile.significator_priority or 'question_first'
                    significator_card, significator_reason = await self.significator.select_significator(
                        age=user_profile.age,
                        gender=user_profile.gender,
                        zodiac_sign=user_profile.zodiac_sign,
                        personality_type=user_profile.personality_type,
                        question_domain=question_analysis.question_domain,
                        significator_priority=significator_priority,
                        source=preferred_source
                    )
                    
                    update_data = {
                        'significator_card_id': significator_card['id'],
                        'significator_selection_reason': significator_reason
                    }
                    self.supabase.table('readings').update(update_data).eq('id', reading_id).execute()
                else:
                    logger.warning("No user profile provided, skipping significator selection")
            else:
                logger.info(f"Step 3: Skipping significator selection ({final_spread} spread doesn't use significator)")
            
            # Step 4: 选牌
            logger.info(f"Step 4: Selecting cards for spread: {final_spread}")
            
            deck = await self.card_selection.get_deck_from_database(source=preferred_source)
            # 移除代表牌（仅十字占卜需要移除代表牌）
            if final_spread == 'celtic_cross' and significator_card:
                remaining_deck = self.card_selection.remove_significator_from_deck(deck, significator_card)
            else:
                remaining_deck = deck.copy()
            shuffled_deck = await self.card_selection.shuffle_and_cut_deck(remaining_deck)
            selected_cards = await self.card_selection.select_cards_for_spread(
                spread_type=final_spread,
                shuffled_deck=shuffled_deck,
                significator=significator_card
            )
            
            # Step 5: 保存牌到reading_cards表
            logger.info(f"Step 5: Saving {len(selected_cards)} cards to database...")
            
            reading_cards_data = []
            for card in selected_cards:
                reading_cards_data.append({
                    'reading_id': reading_id,
                    'card_id': card.card_id,
                    'position': card.position,
                    'position_order': card.position_order,
                    'position_description': card.position_description,
                    'is_reversed': card.is_reversed,
                    'card_selected_at': datetime.utcnow().isoformat()
                })
            
            if reading_cards_data:
                self.supabase.table('reading_cards').insert(reading_cards_data).execute()
            
            update_data = {
                'status': 'card_selected',
                'current_step': 'pattern_analysis',
                'cards_selected_at': datetime.utcnow().isoformat()
            }
            self.supabase.table('readings').update(update_data).eq('id', reading_id).execute()
            
            yield {
                'type': 'progress',
                'step': 'cards_selected',
                'data': {
                    'cards': [self._selected_card_to_dict(card) for card in selected_cards],
                    'significator': {
                        'card_name_en': significator_card['card_name_en'] if significator_card else None,
                        'card_name_cn': significator_card.get('card_name_cn'),
                        'selection_reason': significator_reason
                    } if significator_card else None,
                    'message': f'已选择{len(selected_cards)}张牌'
                }
            }
            
            # Step 6: 分析牌型（纯代码实现）
            logger.info("Step 6: Analyzing spread pattern (code-based analysis)...")
            step_start_time = time.time()
            
            # 使用纯代码分析牌型
            pattern_analysis_dict = self._analyze_spread_pattern_code(
                selected_cards=selected_cards,
                spread_type=final_spread,
                question_domain=question_analysis.question_domain
            )
            
            processing_time_ms = int((time.time() - step_start_time) * 1000)
            
            # 保存过程数据
            await self._save_process_data(
                reading_id=reading_id,
                step_name='pattern_analysis',
                step_order=6,
                input_data={
                    'selected_cards': [self._selected_card_to_dict(card) for card in selected_cards],
                    'spread_type': final_spread,
                    'question_domain': question_analysis.question_domain,
                    'analysis_method': 'code_based'
                },
                output_data={
                    'analysis': pattern_analysis_dict
                },
                processing_time_ms=processing_time_ms
            )
            
            # 更新reading记录
            update_data = {
                'spread_pattern_analysis': pattern_analysis_dict,
                'current_step': 'rag_retrieval',
                'analysis_completed_at': datetime.utcnow().isoformat()
            }
            self.supabase.table('readings').update(update_data).eq('id', reading_id).execute()
            
            yield {
                'type': 'progress',
                'step': 'pattern_analyzed',
                'data': {
                    'pattern_analysis': pattern_analysis_dict,
                    'message': '牌型分析完成'
                }
            }
            
            # Step 7: RAG检索
            logger.info("Step 7: Retrieving card information via RAG...")
            step_start_time_rag = time.time()
            
            rag_queries = []
            
            # 使用带进度更新的版本
            card_information = {}
            async for update in self._retrieve_card_information_with_progress(selected_cards, rag_queries):
                if update.get('type') == 'progress':
                    # 发送进度更新到前端
                    yield update
                elif update.get('type') == 'result':
                    card_information = update['data']
            
            # 发送核心卡牌RAG检索完成的消息（约10秒，符合ARCHITECTURE.md预期）
            yield {
                'type': 'progress',
                'step': 'rag_retrieved',
                'data': {
                    'message': '信息检索完成'
                }
            }
            
            # 启动spread_method和card_relationships后台任务（不阻塞）
            logger.info("Starting spread_method and card_relationships retrieval in background...")
            spread_method_task = asyncio.create_task(
                self._retrieve_spread_method(final_spread, rag_queries)
            )
            card_relationships_task = asyncio.create_task(
                self._retrieve_card_relationships(selected_cards, rag_queries)
            )
            
            # Step 7.5: 立即开始生成牌阵意象描述（流式输出）
            logger.info("Step 7.5: Generating spread imagery description (streaming)...")
            step_start_time_imagery = time.time()
            
            # 流式生成意象描述
            imagery_description_chunks = []
            async for chunk in self._generate_spread_imagery_description_stream(
                selected_cards=selected_cards,
                card_information=card_information,
                question_domain=question_analysis.question_domain
            ):
                imagery_description_chunks.append(chunk)
                # 发送意象描述的流式更新
                yield {
                    'type': 'imagery_chunk',
                    'text': chunk
                }
            
            # 合并完整的意象描述
            spread_imagery_description = ''.join(imagery_description_chunks)
            processing_time_ms_imagery = int((time.time() - step_start_time_imagery) * 1000)
            
            # 获取意象描述的prompt和LLM response
            imagery_prompt = getattr(self, '_last_imagery_prompt', None)
            imagery_llm_response = getattr(self, '_last_imagery_llm_response', None)
            imagery_model = getattr(self, '_last_imagery_model', None)
            
            # 发送意象描述完成消息
            yield {
                'type': 'progress',
                'step': 'imagery_generated',
                'data': {
                    'imagery_description': spread_imagery_description,
                    'message': '意象描述生成完成'
                }
            }
            
            # 等待后台RAG任务完成（不阻塞意象生成）
            logger.info("Waiting for background spread_method and card_relationships retrieval...")
            spread_method, card_relationships = await asyncio.gather(
                spread_method_task,
                card_relationships_task
            )
            logger.info(f"Background RAG tasks completed in {int((time.time() - step_start_time_rag) * 1000)}ms")
            
            # 保存RAG检索的过程数据（延迟保存）
            await self._save_process_data(
                reading_id=reading_id,
                step_name='rag_retrieval',
                step_order=7,
                input_data={
                    'selected_cards': [self._selected_card_to_dict(card) for card in selected_cards],
                    'spread_type': final_spread
                },
                output_data={
                    'card_information': card_information,
                    'spread_method': spread_method,
                    'card_relationships': card_relationships
                },
                rag_queries=rag_queries,
                processing_time_ms=int((time.time() - step_start_time_rag) * 1000)
            )
            
            # 保存意象描述的过程数据
            await self._save_process_data(
                reading_id=reading_id,
                step_name='imagery_description',
                step_order=8,
                input_data={
                    'selected_cards': [self._selected_card_to_dict(card) for card in selected_cards],
                    'question_domain': question_analysis.question_domain
                },
                output_data={
                    'imagery_description': spread_imagery_description,
                    'llm_response': imagery_llm_response
                },
                prompt_type='imagery_description',
                prompt_content=imagery_prompt,
                model_used=imagery_model,
                temperature=0.7,
                processing_time_ms=processing_time_ms_imagery
            )
            
            # Step 8: 流式生成最终解读
            logger.info("Step 8: Generating final interpretation (streaming)...")
            step_start_time = time.time()
            
            user_language = user_profile.language if user_profile and user_profile.language else 'zh'
            interpretation_prompt = self._build_interpretation_prompt(
                question=question,
                question_analysis=question_analysis,
                selected_cards=selected_cards,
                pattern_analysis_dict=pattern_analysis_dict,
                card_information=card_information,
                spread_method=spread_method,
                card_relationships=card_relationships,
                user_profile=user_profile,
                spread_imagery_description=spread_imagery_description,
                language=user_language
            )
            
            yield {
                'type': 'progress',
                'step': 'interpretation_started',
                'data': {
                    'message': '开始生成解读...'
                }
            }
            
            # 流式生成解读文本
            full_text = ""
            async for text_chunk in self._generate_final_interpretation_stream(
                question=question,
                question_analysis=question_analysis,
                selected_cards=selected_cards,
                pattern_analysis_dict=pattern_analysis_dict,
                card_information=card_information,
                spread_method=spread_method,
                card_relationships=card_relationships,
                user_profile=user_profile,
                prompt=interpretation_prompt
            ):
                full_text += text_chunk
                yield {
                    'type': 'interpretation',
                    'text': text_chunk
                }
            
            # 构建FinalInterpretation对象（用于保存）
            position_interpretations = []
            for card in selected_cards:
                card_info = card_information.get(card.card_id, {})
                position_interpretations.append(
                    PositionInterpretation(
                        position=card.position,
                        position_order=card.position_order,
                        card_name_en=card.card_name_en,
                        card_name_cn=card.card_name_cn,
                        interpretation=card_info.get('rag_text', ''),
                        relationships=None
                    )
                )
            
            references = []
            for card_info in card_information.values():
                for citation in card_info.get('citations', []):
                    references.append(
                        InterpretationReference(
                            type='card',
                            card_name=card_info.get('card_name_en'),
                            source=citation.get('source', 'Unknown')
                        )
                    )
            
            if spread_method.get('citations'):
                for citation in spread_method['citations']:
                    references.append(
                        InterpretationReference(
                            type='method',
                            method=spread_method.get('spread_type'),
                            source=citation.get('source', 'Unknown')
                        )
                    )
            
            # 保存完整的解读文本（不截断）
            final_interpretation = FinalInterpretation(
                overall_summary=full_text,  # 保存完整的解读文本，不截断
                position_interpretations=position_interpretations,
                relationship_analysis=pattern_analysis_dict.get('position_relationships', {}).get('time_flow', ''),
                pattern_explanation=str(pattern_analysis_dict.get('suit_distribution', {}).get('interpretation', '')),
                advice=None,
                references=references[:10]
            )
            
            processing_time_ms = int((time.time() - step_start_time) * 1000)
            
            # 获取实际使用的模型名称
            interpretation_model = getattr(self, '_last_interpretation_model', None)
            
            await self._save_process_data(
                reading_id=reading_id,
                step_name='final_interpretation',
                step_order=9,  # 更新为9（意象描述是8）
                input_data={
                    'question': question,
                    'question_analysis': question_analysis.model_dump(),
                    'selected_cards': [self._selected_card_to_dict(card) for card in selected_cards],
                    'pattern_analysis': pattern_analysis_dict,
                    'card_information': card_information,
                    'spread_method': spread_method
                },
                output_data={
                    'interpretation': final_interpretation.model_dump(),
                    'llm_response': full_text
                },
                prompt_type='final_interpretation',
                prompt_content=interpretation_prompt,
                model_used=interpretation_model,  # 使用实际模型名称
                temperature=0.7,
                processing_time_ms=processing_time_ms
            )
            
            # Step 9: 更新reading记录
            logger.info("Step 9: Updating reading record...")
            interpretation_metadata = {
                'references': [ref.dict() for ref in final_interpretation.references],
                'pattern_analysis_method': pattern_analysis_dict.get('analysis_method'),
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
            
            # 获取意象描述（从实例变量中获取）
            spread_imagery_description = getattr(self, '_last_imagery_description', None)
            
            # 生成摘要（前500字符，用于预览或隐藏数据）
            interpretation_summary = full_text[:500] if len(full_text) > 500 else full_text
            
            update_data = {
                'interpretation': full_text,  # 只保存LLM的原始输出，不包含位置解读、关系分析等中间数据
                'interpretation_full_text': full_text,  # 完整的LLM原始输出
                'interpretation_summary': interpretation_summary,  # 摘要（隐藏数据）
                'interpretation_metadata': interpretation_metadata,
                'status': 'completed',
                'current_step': 'interpretation',
                'interpreted_at': datetime.utcnow().isoformat()
            }
            
            # 如果有意象描述，保存到readings表
            if spread_imagery_description:
                update_data['imagery_description'] = spread_imagery_description
            
            try:
                self.supabase.table('readings').update(update_data).eq('id', reading_id).execute()
            except Exception as update_error:
                # 如果更新失败（可能是字段不存在），尝试逐步移除可能不存在的字段
                logger.warning(f"Failed to update reading: {update_error}")
                # 尝试移除可能不存在的字段
                fallback_data = update_data.copy()
                fields_to_remove = ['imagery_description', 'interpretation_full_text', 'interpretation_summary']
                
                for field in fields_to_remove:
                    if field in fallback_data:
                        try:
                            test_data = {k: v for k, v in fallback_data.items() if k != field}
                            self.supabase.table('readings').update(test_data).eq('id', reading_id).execute()
                            logger.info(f"Reading updated without {field} field")
                            break
                        except Exception:
                            # 继续尝试移除下一个字段
                            if field in fallback_data:
                                del fallback_data[field]
                            continue
                else:
                    # 如果所有字段都移除了还是失败，抛出错误
                    logger.error(f"Failed to update reading even after removing optional fields: {update_error}")
                    raise
            
            total_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Reading completed successfully in {total_time_ms}ms")
            
            yield {
                'type': 'complete',
                'data': {
                    'reading_id': reading_id,
                    'question': question,
                    'spread_type': final_spread,
                    'total_time_ms': total_time_ms,
                    'message': '占卜完成'
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create reading: {e}")
            if reading_id:
                try:
                    self.supabase.table('readings').update({
                        'status': 'error',
                        'interpretation': f"Error: {str(e)}"
                    }).eq('id', reading_id).execute()
                except Exception as update_error:
                    logger.error(f"Failed to update reading status to error: {update_error}")
            
            yield {
                'type': 'error',
                'error': str(e),
                'reading_id': reading_id
            }
    
    async def _retrieve_card_information(
        self,
        cards: List[SelectedCard],
        rag_queries: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        通过RAG检索卡牌信息（优化版 - test2_final融合查询策略）
        
        根据大阿卡纳和小阿卡纳的区别，采用不同的查询策略：
        
        **大阿卡纳（Major Arcana）**：
        1. basic_upright/reversed_symbolic_meaning (top_k=10) - 融合基础含义、正逆位、象征意义
        2. visual_description (top_k=5) - 视觉描述
        3. position_and_psychological_meaning (top_k=10) - 位置含义和心理学解读
        
        **小阿卡纳（Minor Arcana）**：
        1. basic_upright/reversed_suit_meaning (top_k=10) - 融合基础含义、正逆位、花色/元素含义
        2. visual_description (top_k=5) - 视觉描述
        3. position_and_psychological_meaning (top_k=10) - 位置含义和心理学解读
        
        所有查询并行执行，提升信息完整性
        
        Args:
            cards: 选中的牌列表
            rag_queries: RAG查询列表（用于记录所有查询）
            
        Returns:
            每张牌的RAG检索结果字典
        """
        card_info = {}
        if rag_queries is None:
            rag_queries = []
        
        # 定义单个卡牌的多查询RAG检索函数
        async def retrieve_single_card_enhanced(card: SelectedCard) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
            """检索单张卡牌的信息（融合查询策略）"""
            card_queries = []
            queries = []
            
            # 判断是大阿卡纳还是小阿卡纳
            is_major = card.arcana == 'major'
            
            # 构建融合查询1：基础含义 + 正逆位 + (象征意义/花色含义)
            if is_major:
                # 大阿卡纳：融合基础含义、正逆位、象征意义
                if card.is_reversed:
                    query_text = f"{card.card_name_en} tarot card reversed meaning divinatory reversed symbolic meaning symbolism archetype"
                else:
                    query_text = f"{card.card_name_en} tarot card upright meaning divinatory upright symbolic meaning symbolism archetype"
                queries.append({
                    'query': query_text,
                    'type': 'basic_upright_reversed_symbolic_meaning',
                    'top_k': 10
                })
            else:
                # 小阿卡纳：融合基础含义、正逆位、花色/元素含义
                suit_keywords = {
                    'wands': 'fire element action',
                    'cups': 'water element emotion',
                    'swords': 'air element thought',
                    'pentacles': 'earth element material'
                }
                suit_keyword = ''
                for suit, keywords in suit_keywords.items():
                    if suit in card.card_name_en.lower():
                        suit_keyword = keywords
                        break
                
                if suit_keyword:
                    if card.is_reversed:
                        query_text = f"{card.card_name_en} tarot card reversed meaning divinatory reversed {suit_keyword} suit meaning"
                    else:
                        query_text = f"{card.card_name_en} tarot card upright meaning divinatory upright {suit_keyword} suit meaning"
                else:
                    # 如果没有找到花色，使用通用查询
                    if card.is_reversed:
                        query_text = f"{card.card_name_en} tarot card reversed meaning divinatory reversed"
                    else:
                        query_text = f"{card.card_name_en} tarot card upright meaning divinatory upright"
                
                queries.append({
                    'query': query_text,
                    'type': 'basic_upright_reversed_suit_meaning',
                    'top_k': 10
                })
            
            # 构建查询2：视觉描述
            queries.append({
                'query': f"{card.card_name_en} tarot card description image visual appearance",
                'type': 'visual_description',
                'top_k': 5
            })
            
            # 构建查询3：位置含义和心理学解读（融合）
            position_part = f" {card.position} position" if card.position else ""
            queries.append({
                'query': f"{card.card_name_en} tarot card{position_part} meaning psychological meaning psychological interpretation",
                'type': 'position_and_psychological_meaning',
                'top_k': 10
            })
            
            # 并行执行所有查询
            async def execute_query(query_info: Dict[str, Any]) -> Dict[str, Any]:
                """执行单个RAG查询 - 只返回原始chunks，不调用LLM"""
                try:
                    async with self._rag_semaphore:
                        top_k = query_info.get('top_k', 5)
                        # 使用search_only只返回原始chunks，不调用LLM
                        rag_result = await rag_service.search_only(
                            query_info['query'], 
                            top_k=top_k,
                            min_similarity=0.5
                        )
                    
                    return {
                        'query': query_info['query'],
                        'type': query_info['type'],
                        'card_id': card.card_id,
                        'card_name_en': card.card_name_en,
                        'result': {
                            'chunks': rag_result.get('chunks', []),
                            'citations': rag_result.get('citations', []),
                            'debug': rag_result.get('debug', {})
                        }
                    }
                except Exception as e:
                    logger.warning(f"Failed to execute RAG query '{query_info['query']}': {e}")
                    return {
                        'query': query_info['query'],
                        'type': query_info['type'],
                        'card_id': card.card_id,
                        'card_name_en': card.card_name_en,
                        'error': str(e),
                        'result': None
                    }
            
            # 并行执行所有查询
            query_tasks = [execute_query(q) for q in queries]
            query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
            
            # 收集所有chunks（原始文本，不经过LLM处理）
            all_chunks = []
            all_citations = []
            
            for result in query_results:
                if isinstance(result, Exception):
                    logger.error(f"Error in query execution: {result}")
                    continue
                
                card_queries.append(result)
                
                if result.get('result'):
                    chunks = result['result'].get('chunks', [])
                    all_chunks.extend(chunks)
                    citations = result['result'].get('citations', [])
                    all_citations.extend(citations)
            
            # 去重chunks（基于chunk_id）
            seen_chunk_ids = {}
            unique_chunks = []
            for chunk in all_chunks:
                chunk_id = chunk.get('chunk_id', '')
                if chunk_id:
                    # 保留相似度最高的chunk
                    if chunk_id not in seen_chunk_ids:
                        seen_chunk_ids[chunk_id] = chunk
                        unique_chunks.append(chunk)
                    else:
                        # 如果已存在，比较相似度，保留更高的
                        existing_sim = seen_chunk_ids[chunk_id].get('similarity', 0)
                        new_sim = chunk.get('similarity', 0)
                        if new_sim > existing_sim:
                            # 替换为相似度更高的chunk
                            unique_chunks.remove(seen_chunk_ids[chunk_id])
                            seen_chunk_ids[chunk_id] = chunk
                            unique_chunks.append(chunk)
            
            # 去重citations（基于chunk_id）
            seen_citation_ids = set()
            unique_citations = []
            for citation in all_citations:
                chunk_id = citation.get('chunk_id', '')
                if chunk_id and chunk_id not in seen_citation_ids:
                    seen_citation_ids.add(chunk_id)
                    unique_citations.append(citation)
            
            card_data = {
                'card_name_en': card.card_name_en,
                'card_name_cn': card.card_name_cn,
                'position': card.position,
                'is_reversed': card.is_reversed,
                'arcana': card.arcana,
                'chunks': unique_chunks,  # 存储原始chunks而不是LLM生成的文本
                'citations': unique_citations,
                'query_count': len(card_queries),
                'query_types': [q.get('type') for q in card_queries if q.get('type')]
            }
            
            return card.card_id, card_data, card_queries
        
        # 并行执行所有卡牌的RAG检索
        tasks = [retrieve_single_card_enhanced(card) for card in cards]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集结果
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error in card RAG retrieval: {result}")
                continue
            
            card_id, card_data, query_records = result
            card_info[card_id] = card_data
            rag_queries.extend(query_records)
        
        return card_info
    
    async def _retrieve_card_information_with_progress(
        self,
        cards: List[SelectedCard],
        rag_queries: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        通过RAG检索卡牌信息（带进度更新版本）
        
        使用asyncio.as_completed来发送每张卡牌检索完成的进度更新
        """
        if rag_queries is None:
            rag_queries = []
        
        card_info = {}
        
        # 定义单个卡牌的多查询RAG检索函数（复用原有逻辑）
        async def retrieve_single_card_enhanced(card: SelectedCard) -> Tuple[str, Dict[str, Any], List[Dict[str, Any]]]:
            """检索单张卡牌的信息（融合查询策略）"""
            card_queries = []
            queries = []
            
            # 判断是大阿卡纳还是小阿卡纳
            is_major = card.arcana == 'major'
            
            # 构建融合查询1：基础含义 + 正逆位 + (象征意义/花色含义)
            if is_major:
                if card.is_reversed:
                    query_text = f"{card.card_name_en} tarot card reversed meaning divinatory reversed symbolic meaning symbolism archetype"
                else:
                    query_text = f"{card.card_name_en} tarot card upright meaning divinatory upright symbolic meaning symbolism archetype"
                queries.append({
                    'query': query_text,
                    'type': 'basic_upright_reversed_symbolic_meaning',
                    'top_k': 10
                })
            else:
                suit_keywords = {
                    'wands': 'fire element action',
                    'cups': 'water element emotion',
                    'swords': 'air element thought',
                    'pentacles': 'earth element material'
                }
                suit_keyword = ''
                for suit, keywords in suit_keywords.items():
                    if suit in card.card_name_en.lower():
                        suit_keyword = keywords
                        break
                
                if suit_keyword:
                    if card.is_reversed:
                        query_text = f"{card.card_name_en} tarot card reversed meaning divinatory reversed {suit_keyword} suit meaning"
                    else:
                        query_text = f"{card.card_name_en} tarot card upright meaning divinatory upright {suit_keyword} suit meaning"
                else:
                    if card.is_reversed:
                        query_text = f"{card.card_name_en} tarot card reversed meaning divinatory reversed"
                    else:
                        query_text = f"{card.card_name_en} tarot card upright meaning divinatory upright"
                
                queries.append({
                    'query': query_text,
                    'type': 'basic_upright_reversed_suit_meaning',
                    'top_k': 10
                })
            
            queries.append({
                'query': f"{card.card_name_en} tarot card description image visual appearance",
                'type': 'visual_description',
                'top_k': 5
            })
            
            position_part = f" {card.position} position" if card.position else ""
            queries.append({
                'query': f"{card.card_name_en} tarot card{position_part} meaning psychological meaning psychological interpretation",
                'type': 'position_and_psychological_meaning',
                'top_k': 10
            })
            
            async def execute_query(query_info: Dict[str, Any]) -> Dict[str, Any]:
                try:
                    async with self._rag_semaphore:
                        top_k = query_info.get('top_k', 5)
                        rag_result = await rag_service.search_only(
                            query_info['query'], 
                            top_k=top_k,
                            min_similarity=0.5
                        )
                    return {
                        'query': query_info['query'],
                        'type': query_info['type'],
                        'card_id': card.card_id,
                        'card_name_en': card.card_name_en,
                        'result': {
                            'chunks': rag_result.get('chunks', []),
                            'citations': rag_result.get('citations', []),
                            'debug': rag_result.get('debug', {})
                        }
                    }
                except Exception as e:
                    logger.warning(f"Failed to execute RAG query '{query_info['query']}': {e}")
                    return {
                        'query': query_info['query'],
                        'type': query_info['type'],
                        'card_id': card.card_id,
                        'card_name_en': card.card_name_en,
                        'error': str(e),
                        'result': None
                    }
            
            query_tasks = [execute_query(q) for q in queries]
            query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
            
            all_chunks = []
            all_citations = []
            
            for result in query_results:
                if isinstance(result, Exception):
                    logger.error(f"Error in query execution: {result}")
                    continue
                
                card_queries.append(result)
                
                if result.get('result'):
                    chunks = result['result'].get('chunks', [])
                    all_chunks.extend(chunks)
                    citations = result['result'].get('citations', [])
                    all_citations.extend(citations)
            
            seen_chunk_ids = {}
            unique_chunks = []
            for chunk in all_chunks:
                chunk_id = chunk.get('chunk_id', '')
                if chunk_id:
                    if chunk_id not in seen_chunk_ids:
                        seen_chunk_ids[chunk_id] = chunk
                        unique_chunks.append(chunk)
                    else:
                        existing_sim = seen_chunk_ids[chunk_id].get('similarity', 0)
                        new_sim = chunk.get('similarity', 0)
                        if new_sim > existing_sim:
                            unique_chunks.remove(seen_chunk_ids[chunk_id])
                            seen_chunk_ids[chunk_id] = chunk
                            unique_chunks.append(chunk)
            
            seen_citation_ids = set()
            unique_citations = []
            for citation in all_citations:
                chunk_id = citation.get('chunk_id', '')
                if chunk_id and chunk_id not in seen_citation_ids:
                    seen_citation_ids.add(chunk_id)
                    unique_citations.append(citation)
            
            card_data = {
                'card_name_en': card.card_name_en,
                'card_name_cn': card.card_name_cn,
                'position': card.position,
                'is_reversed': card.is_reversed,
                'arcana': card.arcana,
                'chunks': unique_chunks,
                'citations': unique_citations,
                'query_count': len(card_queries),
                'query_types': [q.get('type') for q in card_queries if q.get('type')]
            }
            
            return card.card_id, card_data, card_queries
        
        # 并行执行所有卡牌的RAG检索，使用asyncio.as_completed来发送进度
        tasks = [retrieve_single_card_enhanced(card) for card in cards]
        completed_count = 0
        total_cards = len(cards)
        
        # 根据占卜类型计算阈值
        threshold = 1 if total_cards == 3 else max(1, total_cards // 10)
        
        # 使用asyncio.as_completed来逐个完成卡牌检索并发送进度
        first_card_sent = False
        for coro in asyncio.as_completed(tasks):
            try:
                card_id, card_data, query_records = await coro
                card_info[card_id] = card_data
                rag_queries.extend(query_records)
                completed_count += 1
                
                # 发送进度更新（每完成一张卡牌）
                progress_ratio = completed_count / total_cards
                yield {
                    'type': 'progress',
                    'step': 'rag_card_progress',
                    'data': {
                        'progress': progress_ratio,
                        'completed_cards': completed_count,
                        'total_cards': total_cards,
                        'card_id': card_id,
                        'card_name': card_data.get('card_name_en', ''),
                        'message': f'已检索 {completed_count}/{total_cards} 张卡牌'
                    }
                }
                
                # 如果达到阈值且还没发送第一张卡牌，发送卡牌数据更新
                if not first_card_sent and completed_count >= threshold:
                    # 获取已完成的卡牌（按position_order排序）
                    completed_card_ids = sorted(card_info.keys(), key=lambda cid: next(
                        (card.position_order for card in cards if card.card_id == cid), 0
                    ))
                    first_card_sent = True
                    yield {
                        'type': 'progress',
                        'step': 'rag_first_card_ready',
                        'data': {
                            'completed_cards': completed_count,
                            'total_cards': total_cards,
                            'message': '第一张卡牌检索完成'
                        }
                    }
            except Exception as e:
                logger.error(f"Error in card RAG retrieval: {e}")
                continue
        
        # 返回最终结果
        yield {
            'type': 'result',
            'data': card_info
        }
    
    async def _retrieve_spread_method(
        self,
        spread_type: str,
        rag_queries: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        通过RAG检索占卜方法信息（增强版 - 多查询并行执行）
        
        执行多个RAG查询，全面获取占卜方法信息：
        1. 占卜方法说明和步骤
        2. 位置含义和解读方法
        3. 心理学背景（78 Degrees特有）
        4. 传统解读方法（PKT特有）
        
        Args:
            spread_type: 占卜方式
            rag_queries: RAG查询列表（用于记录查询）
            
        Returns:
            占卜方法信息字典
        """
        if rag_queries is None:
            rag_queries = []
        
        # 构建多个查询
        queries = []
        
        # 1. 占卜方法说明和步骤
        queries.append({
            'query': f"{spread_type} spread tarot divination method how to use steps",
            'type': 'method_steps'
        })
        
        # 2. 位置含义和解读方法
        queries.append({
            'query': f"{spread_type} spread tarot card positions meaning interpretation",
            'type': 'position_interpretation'
        })
        
        # 3. 心理学背景（78 Degrees特有）
        queries.append({
            'query': f"{spread_type} spread tarot psychological approach interpretation",
            'type': 'psychological_background'
        })
        
        # 4. 传统解读方法（PKT特有）
        queries.append({
            'query': f"{spread_type} spread tarot traditional divination method ancient celtic",
            'type': 'traditional_method'
        })
        
        # 并行执行所有查询
        async def execute_query(query_info: Dict[str, str]) -> Dict[str, Any]:
            """执行单个RAG查询 - 只返回原始chunks，不调用LLM"""
            try:
                async with self._rag_semaphore:
                    # 对于占卜方法查询，使用较低的相似度阈值(0.25)以获取更多相关信息
                    rag_result = await rag_service.search_only(
                        query_info['query'], 
                        top_k=5,
                        min_similarity=0.25
                    )
                
                return {
                    'query': query_info['query'],
                    'type': query_info['type'],
                    'spread_type': spread_type,
                    'result': {
                        'chunks': rag_result.get('chunks', []),
                        'citations': rag_result.get('citations', []),
                        'debug': rag_result.get('debug', {})
                    }
                }
            except Exception as e:
                logger.warning(f"Failed to execute spread method query '{query_info['query']}': {e}")
                return {
                    'query': query_info['query'],
                    'type': query_info['type'],
                    'spread_type': spread_type,
                    'error': str(e),
                    'result': None
                }
        
        # 并行执行所有查询
        query_tasks = [execute_query(q) for q in queries]
        query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
        
        # 收集所有chunks（原始文本，不经过LLM处理）
        all_chunks = []
        all_citations = []
        
        for result in query_results:
            if isinstance(result, Exception):
                logger.error(f"Error in spread method query execution: {result}")
                continue
            
            rag_queries.append(result)
            
            if result.get('result'):
                chunks = result['result'].get('chunks', [])
                all_chunks.extend(chunks)
                citations = result['result'].get('citations', [])
                all_citations.extend(citations)
        
        # 去重chunks（基于chunk_id）
        seen_chunk_ids = {}
        unique_chunks = []
        for chunk in all_chunks:
            chunk_id = chunk.get('chunk_id', '')
            if chunk_id:
                if chunk_id not in seen_chunk_ids:
                    seen_chunk_ids[chunk_id] = chunk
                    unique_chunks.append(chunk)
                else:
                    existing_sim = seen_chunk_ids[chunk_id].get('similarity', 0)
                    new_sim = chunk.get('similarity', 0)
                    if new_sim > existing_sim:
                        unique_chunks.remove(seen_chunk_ids[chunk_id])
                        seen_chunk_ids[chunk_id] = chunk
                        unique_chunks.append(chunk)
        
        # 去重citations
        seen_citation_ids = set()
        unique_citations = []
        for citation in all_citations:
            chunk_id = citation.get('chunk_id', '')
            if chunk_id and chunk_id not in seen_citation_ids:
                seen_citation_ids.add(chunk_id)
                unique_citations.append(citation)
        
        return {
            'spread_type': spread_type,
            'chunks': unique_chunks,  # 存储原始chunks而不是LLM生成的文本
            'citations': unique_citations,
            'query_count': len([r for r in query_results if not isinstance(r, Exception)]),
            'query_types': [r.get('type') for r in query_results if not isinstance(r, Exception) and r.get('type')]
        }
    
    async def _retrieve_card_relationships(
        self,
        cards: List[SelectedCard],
        rag_queries: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        通过RAG检索牌之间的关系和模式信息（增强版）
        
        执行多个RAG查询，全面获取牌之间的关系信息：
        1. 数字模式（相同数字、序列、跳跃）
        2. 花色分布和元素平衡
        3. 大阿卡纳模式
        4. 逆位模式
        5. 特殊组合（宫廷牌组合等）
        
        Args:
            cards: 选中的牌列表
            rag_queries: RAG查询列表（用于记录查询）
            
        Returns:
            牌之间的关系信息字典
        """
        if rag_queries is None:
            rag_queries = []
        
        # 分析牌的特征
        card_names = [card.card_name_en for card in cards]
        reversed_count = sum(1 for card in cards if card.is_reversed)
        major_count = sum(1 for card in cards if any(major in card.card_name_en.lower() for major in ['fool', 'magician', 'priestess', 'empress', 'emperor', 'hierophant', 'lovers', 'chariot', 'strength', 'hermit', 'wheel', 'justice', 'hanged', 'death', 'temperance', 'devil', 'tower', 'star', 'moon', 'sun', 'judgement', 'judgment', 'world']))
        
        # 构建多个查询
        queries = []
        
        # 1. 数字模式
        queries.append({
            'query': f"tarot card number patterns same numbers sequences in spread {', '.join(card_names)}",
            'type': 'number_patterns'
        })
        
        # 2. 花色分布和元素平衡
        suits = []
        for card in cards:
            for suit in ['wands', 'cups', 'swords', 'pentacles']:
                if suit in card.card_name_en.lower():
                    suits.append(suit)
                    break
        if suits:
            queries.append({
                'query': f"tarot card suit distribution element balance {', '.join(set(suits))} in spread",
                'type': 'suit_distribution'
            })
        
        # 3. 大阿卡纳模式
        if major_count > 0:
            queries.append({
                'query': f"tarot major arcana pattern meaning {major_count} major arcana cards in spread interpretation",
                'type': 'major_arcana_pattern'
            })
        
        # 4. 逆位模式
        if reversed_count > 0:
            queries.append({
                'query': f"tarot reversed cards pattern meaning {reversed_count} reversed cards in spread interpretation",
                'type': 'reversed_pattern'
            })
        
        # 5. 特殊组合（宫廷牌组合）
        court_cards = [card for card in cards if any(court in card.card_name_en.lower() for court in ['king', 'queen', 'knight', 'page'])]
        if len(court_cards) > 1:
            queries.append({
                'query': f"tarot court cards combination meaning {', '.join([c.card_name_en for c in court_cards])} in spread",
                'type': 'court_card_combination'
            })
        
        # 6. 牌之间的关系和顺序
        if len(cards) >= 2:
            position_info = ', '.join([f"{card.card_name_en} ({card.position})" for card in cards if card.position])
            if position_info:
                queries.append({
                    'query': f"tarot card relationships sequence meaning {position_info}",
                    'type': 'card_relationships'
                })
        
        # 如果没有足够的特征，至少查询一般的关系解读
        if not queries:
            queries.append({
                'query': f"tarot card spread interpretation relationships between cards {', '.join(card_names)}",
                'type': 'general_relationships'
            })
        
        # 并行执行所有查询
        async def execute_query(query_info: Dict[str, str]) -> Dict[str, Any]:
            """执行单个RAG查询 - 只返回原始chunks，不调用LLM"""
            try:
                async with self._rag_semaphore:
                    # 对于关系查询，使用较低的相似度阈值(0.25)以获取更多相关信息
                    rag_result = await rag_service.search_only(
                        query_info['query'], 
                        top_k=5,
                        min_similarity=0.25
                    )
                
                return {
                    'query': query_info['query'],
                    'type': query_info['type'],
                    'result': {
                        'chunks': rag_result.get('chunks', []),
                        'citations': rag_result.get('citations', []),
                        'debug': rag_result.get('debug', {})
                    }
                }
            except Exception as e:
                logger.warning(f"Failed to execute relationship query '{query_info['query']}': {e}")
                return {
                    'query': query_info['query'],
                    'type': query_info['type'],
                    'error': str(e),
                    'result': None
                }
        
        # 并行执行所有查询
        query_tasks = [execute_query(q) for q in queries]
        query_results = await asyncio.gather(*query_tasks, return_exceptions=True)
        
        # 收集所有chunks（原始文本，不经过LLM处理）
        all_chunks = []
        all_citations = []
        
        for result in query_results:
            if isinstance(result, Exception):
                logger.error(f"Error in relationship query execution: {result}")
                continue
            
            rag_queries.append(result)
            
            if result.get('result'):
                chunks = result['result'].get('chunks', [])
                all_chunks.extend(chunks)
                citations = result['result'].get('citations', [])
                all_citations.extend(citations)
        
        # 去重chunks（基于chunk_id）
        seen_chunk_ids = {}
        unique_chunks = []
        for chunk in all_chunks:
            chunk_id = chunk.get('chunk_id', '')
            if chunk_id:
                if chunk_id not in seen_chunk_ids:
                    seen_chunk_ids[chunk_id] = chunk
                    unique_chunks.append(chunk)
                else:
                    existing_sim = seen_chunk_ids[chunk_id].get('similarity', 0)
                    new_sim = chunk.get('similarity', 0)
                    if new_sim > existing_sim:
                        unique_chunks.remove(seen_chunk_ids[chunk_id])
                        seen_chunk_ids[chunk_id] = chunk
                        unique_chunks.append(chunk)
        
        # 去重citations
        seen_citation_ids = set()
        unique_citations = []
        for citation in all_citations:
            chunk_id = citation.get('chunk_id', '')
            if chunk_id and chunk_id not in seen_citation_ids:
                seen_citation_ids.add(chunk_id)
                unique_citations.append(citation)
        
        return {
            'chunks': unique_chunks,  # 存储原始chunks而不是LLM生成的文本
            'citations': unique_citations,
            'query_count': len([r for r in query_results if not isinstance(r, Exception)]),
            'query_types': [r.get('type') for r in query_results if not isinstance(r, Exception) and r.get('type')]
        }
    
    async def _generate_final_interpretation_with_details(
        self,
        question: str,
        question_analysis: QuestionAnalysis,
        selected_cards: List[SelectedCard],
        pattern_analysis_dict: Dict[str, Any],
        card_information: Dict[str, Any],
        spread_method: Dict[str, Any],
        card_relationships: Optional[Dict[str, Any]] = None,
        user_profile: Optional[UserProfileCreate] = None,
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成最终解读并返回详细信息（包括LLM response）
        
        Returns:
            包含interpretation、llm_response、processing_time_ms的字典
        """
        import time
        start_time = time.time()
        
        interpretation = await self._generate_final_interpretation(
            question=question,
            question_analysis=question_analysis,
            selected_cards=selected_cards,
            pattern_analysis_dict=pattern_analysis_dict,
            card_information=card_information,
            spread_method=spread_method,
            card_relationships=card_relationships,
            user_profile=user_profile,
            prompt=prompt
        )
        
        # 获取LLM的原始响应（从_generate_final_interpretation中获取）
        llm_response = getattr(self, '_last_llm_response', None)
        model_used = getattr(self, '_last_interpretation_model', None)  # 获取实际使用的模型
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            'interpretation': interpretation,
            'llm_response': llm_response,
            'processing_time_ms': processing_time_ms,
            'model_used': model_used
        }
    
    async def _generate_final_interpretation_stream(
        self,
        question: str,
        question_analysis: QuestionAnalysis,
        selected_cards: List[SelectedCard],
        pattern_analysis_dict: Dict[str, Any],
        card_information: Dict[str, Any],
        spread_method: Dict[str, Any],
        card_relationships: Optional[Dict[str, Any]] = None,
        user_profile: Optional[UserProfileCreate] = None,
        prompt: Optional[str] = None
    ):
        """
        生成最终解读（非流式，直接返回完整答案）
        
        Yields:
            完整答案文本（str）- 为了保持接口兼容性，仍然使用yield，但只yield一次完整答案
        """
        # 构建综合prompt（如果未提供）
        if prompt is None:
            # 需要先生成意象描述（如果还没有生成）
            spread_imagery_description = getattr(self, '_last_imagery_description', None)
            if spread_imagery_description is None:
                # 如果没有，生成一个简单的默认描述
                spread_imagery_description = "基于牌阵的视觉意象，这些牌共同构成了一个独特的画面，反映了当前问题的核心能量。"
            
            prompt = self._build_interpretation_prompt(
                question=question,
                question_analysis=question_analysis,
                selected_cards=selected_cards,
                pattern_analysis_dict=pattern_analysis_dict,
                card_information=card_information,
                spread_method=spread_method,
                card_relationships=card_relationships,
                user_profile=user_profile,
                spread_imagery_description=spread_imagery_description
            )
        
        # 调用LLM生成解读（非流式）
        import openai
        
        if settings.use_openrouter and settings.openrouter_api_key:
            api_key = settings.openrouter_api_key
            base_url = "https://openrouter.ai/api/v1"
            default_headers = {
                "HTTP-Referer": "https://github.com/yourusername/tarot_agent",
                "X-Title": "Tarot Agent"
            }
        else:
            api_key = settings.openai_api_key
            base_url = None
            default_headers = {}
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers if default_headers else None
        )
        
        # 使用模型配置系统获取最终解读模型
        model_config = get_model_config()
        default_model = model_config.final_interpretation_model
        
        # 如果用户提供了interpretation_model偏好，使用用户选择的模型
        user_model_preference = user_profile.interpretation_model if user_profile else None
        model = _get_interpretation_model_from_user_preference(user_model_preference, default_model)
        
        logger.info(f"Generating final interpretation with model: {model} (non-streaming)")
        
        # 非流式调用，直接获取完整答案
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        full_text = response.choices[0].message.content
        
        # DeepSeek R1 特殊处理：过滤掉 <think>...</think> 部分
        is_deepseek_r1 = model and ('deepseek-r1' in model.lower() or 'deepseek/deepseek-r1' in model.lower())
        if is_deepseek_r1:
            logger.info("Filtering DeepSeek R1 thinking tags from response")
            # 移除所有 <think>...</think> 标签及其内容
            import re
            full_text = re.sub(r'<think>.*?</think>', '', full_text, flags=re.DOTALL)
            # 清理多余的空白字符
            full_text = re.sub(r'\n\s*\n', '\n\n', full_text).strip()
        
        # 保存完整响应和模型名称
        self._last_llm_response = full_text
        self._last_interpretation_model = model  # 保存实际使用的模型名称
        
        # 为了保持接口兼容性，仍然使用yield，但只yield一次完整答案
        yield full_text
    
    async def _generate_final_interpretation(
        self,
        question: str,
        question_analysis: QuestionAnalysis,
        selected_cards: List[SelectedCard],
        pattern_analysis_dict: Dict[str, Any],
        card_information: Dict[str, Any],
        spread_method: Dict[str, Any],
        card_relationships: Optional[Dict[str, Any]] = None,
        user_profile: Optional[UserProfileCreate] = None,
        prompt: Optional[str] = None
    ) -> FinalInterpretation:
        """
        生成最终解读
        
        Args:
            question: 用户问题
            question_analysis: 问题分析结果
            selected_cards: 选中的牌列表
            pattern_analysis_dict: 牌型分析结果字典
            card_information: 卡牌信息字典
            spread_method: 占卜方法信息字典
            user_profile: 用户信息（可选）
            prompt: 已构建的prompt（可选，如果不提供则自动构建）
            
        Returns:
            FinalInterpretation对象
        """
        # 构建综合prompt（如果未提供）
        if prompt is None:
            # 需要先生成意象描述（如果还没有生成）
            spread_imagery_description = getattr(self, '_last_imagery_description', None)
            if spread_imagery_description is None:
                # 如果没有，生成一个简单的默认描述
                spread_imagery_description = "基于牌阵的视觉意象，这些牌共同构成了一个独特的画面，反映了当前问题的核心能量。"
            
            prompt = self._build_interpretation_prompt(
                question=question,
                question_analysis=question_analysis,
                selected_cards=selected_cards,
                pattern_analysis_dict=pattern_analysis_dict,
                card_information=card_information,
                spread_method=spread_method,
                card_relationships=card_relationships,
                user_profile=user_profile,
                spread_imagery_description=spread_imagery_description
            )
        
        # 调用LLM生成解读
        # 使用更大的模型进行最终解读
        import openai
        
        if settings.use_openrouter and settings.openrouter_api_key:
            api_key = settings.openrouter_api_key
            base_url = "https://openrouter.ai/api/v1"
            default_headers = {
                "HTTP-Referer": "https://github.com/yourusername/tarot_agent",
                "X-Title": "Tarot Agent"
            }
        else:
            api_key = settings.openai_api_key
            base_url = None
            default_headers = {}
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers if default_headers else None
        )
        
        # 使用模型配置系统获取最终解读模型
        model_config = get_model_config()
        default_model = model_config.final_interpretation_model
        
        # 如果用户提供了interpretation_model偏好，使用用户选择的模型
        user_model_preference = user_profile.interpretation_model if user_profile else None
        model = _get_interpretation_model_from_user_preference(user_model_preference, default_model)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7  # 较高温度以获得更自然的解读
        )
        
        interpretation_text = response.choices[0].message.content
        
        # 保存原始响应到实例变量（用于_generate_final_interpretation_with_details）
        self._last_llm_response = interpretation_text
        self._last_interpretation_model = model  # 保存实际使用的模型名称
        
        # 解析解读文本（简化版，实际可以使用更复杂的解析）
        # 这里我们返回一个结构化的解读对象
        position_interpretations = []
        for card in selected_cards:
            card_info = card_information.get(card.card_id, {})
            # 从chunks中提取文本作为解读（如果没有rag_text）
            chunks = card_info.get('chunks', [])
            interpretation_text = ''
            if chunks:
                # 合并前3个chunks的文本
                interpretation_text = '\n\n'.join([chunk.get('text', '')[:200] for chunk in chunks[:3]])
            position_interpretations.append(
                PositionInterpretation(
                    position=card.position,
                    position_order=card.position_order,
                    card_name_en=card.card_name_en,
                    card_name_cn=card.card_name_cn,
                    interpretation=interpretation_text,
                    relationships=None
                )
            )
        
        # 提取引用来源
        references = []
        for card_info in card_information.values():
            for citation in card_info.get('citations', []):
                references.append(
                    InterpretationReference(
                        type='card',
                        card_name=card_info.get('card_name_en'),
                        source=citation.get('source', 'Unknown')
                    )
                )
        
        if spread_method.get('citations'):
            for citation in spread_method['citations']:
                references.append(
                    InterpretationReference(
                        type='method',
                        method=spread_method.get('spread_type'),
                        source=citation.get('source', 'Unknown')
                    )
                )
        
        return FinalInterpretation(
            overall_summary=interpretation_text[:500] if len(interpretation_text) > 500 else interpretation_text,
            position_interpretations=position_interpretations,
            relationship_analysis=pattern_analysis_dict.get('position_relationships', {}).get('time_flow', ''),
            pattern_explanation=str(pattern_analysis_dict.get('suit_distribution', {}).get('interpretation', '')),
            advice=None,
            references=references[:10]  # 限制引用数量
        )
    
    async def _generate_spread_imagery_description(
        self,
        selected_cards: List[SelectedCard],
        card_information: Dict[str, Any],
        question_domain: str,
        rag_queries: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        生成牌阵意象描述
        
        从RAG检索结果中提取每张卡的视觉描述，结合问题领域，生成一个综合的意象描述。
        
        Args:
            selected_cards: 选中的牌列表
            card_information: 卡牌信息字典（包含RAG检索结果）
            question_domain: 问题领域
            rag_queries: RAG查询列表（用于提取visual_description类型的查询）
            
        Returns:
            牌阵意象描述文本
        """
        # 从RAG查询结果中提取视觉描述
        visual_descriptions = []
        
        if rag_queries:
            # 按卡牌分组，提取visual_description类型的查询结果
            for card in selected_cards:
                card_visual_chunks = []
                
                # 从rag_queries中找到该卡的visual_description查询
                for query_record in rag_queries:
                    if (query_record.get('card_id') == card.card_id and 
                        query_record.get('type') == 'visual_description' and
                        query_record.get('result')):
                        chunks = query_record['result'].get('chunks', [])
                        card_visual_chunks.extend(chunks)
                
                # 如果没有找到，尝试从card_information中提取
                if not card_visual_chunks:
                    card_info = card_information.get(card.card_id, {})
                    # 尝试从chunks中查找视觉描述相关的chunks
                    all_chunks = card_info.get('chunks', [])
                    # 查找包含视觉描述关键词的chunks
                    for chunk in all_chunks:
                        text = chunk.get('text', '').lower()
                        if any(keyword in text for keyword in ['image', 'visual', 'appearance', 'depicts', 'shows', 'picture', 'illustration']):
                            card_visual_chunks.append(chunk)
                
                # 合并该卡的所有视觉描述chunks
                if card_visual_chunks:
                    # 去重（基于chunk_id）
                    seen_chunk_ids = set()
                    unique_chunks = []
                    for chunk in card_visual_chunks:
                        chunk_id = chunk.get('chunk_id', '')
                        if chunk_id and chunk_id not in seen_chunk_ids:
                            seen_chunk_ids.add(chunk_id)
                            unique_chunks.append(chunk)
                    
                    # 提取文本内容
                    card_visual_texts = []
                    for chunk in unique_chunks[:3]:  # 最多取前3个chunks
                        text = chunk.get('text', '')
                        if text:
                            # 截断过长的文本
                            if len(text) > 300:
                                text = text[:300] + "..."
                            card_visual_texts.append(text)
                    
                    if card_visual_texts:
                        visual_descriptions.append({
                            'card_name': card.card_name_en,
                            'position': card.position,
                            'is_reversed': card.is_reversed,
                            'descriptions': card_visual_texts
                        })
        
        # 如果没有找到视觉描述，返回默认描述
        if not visual_descriptions:
            logger.warning("No visual descriptions found in RAG results, using default description")
            return "基于牌阵的视觉意象，这些牌共同构成了一个独特的画面，反映了当前问题的核心能量。"
        
        # 构建prompt用于生成意象描述
        visual_info_lines = []
        for desc in visual_descriptions:
            card_desc = f"{desc['card_name']}"
            if desc['position']:
                card_desc += f" ({desc['position']}位置)"
            if desc['is_reversed']:
                card_desc += " [逆位]"
            card_desc += ":\n"
            card_desc += "\n".join([f"  - {d}" for d in desc['descriptions']])
            visual_info_lines.append(card_desc)
        
        visual_info = "\n\n".join(visual_info_lines)
        
        imagery_prompt = f"""You are an experienced Tarot reader. Based on the visual descriptions of the following cards and the question domain, generate a comprehensive spread imagery description.

## Question Domain:
{question_domain}

## Cards in the Spread and Their Visual Descriptions:
{visual_info}

## Requirements:
Please generate a creative, imaginative, and aesthetically pleasing comprehensive imagery description, 3-5 sentences in length. This description should paint the entire spread as a vivid, symbolic picture.
1. **Creative Integration**: Do not merely list the visual elements of the cards, but fuse them into a coherent, dynamic scene or story.
2. **Deep Association**: Combine with the context of the question domain ({question_domain}), engage in divergent thinking, and explore the deeper symbols and metaphors behind the imagery.
3. **Atmosphere Creation**: Vividly depict the overall energy, atmosphere, and emotional tone of the spread.
4. **Beautiful Language**: Output in Chinese, with poetic and vivid language that captivates.

**Important Note**: The visual descriptions provided by RAG may contain duplicate or inaccurate information. Please use critical thinking to filter and integrate the information, creating the most appropriate and inspiring imagery.

Please output the imagery description directly without any other explanations."""

        # 调用LLM生成意象描述
        try:
            import openai
            
            if settings.use_openrouter and settings.openrouter_api_key:
                api_key = settings.openrouter_api_key
                base_url = "https://openrouter.ai/api/v1"
                default_headers = {
                    "HTTP-Referer": "https://github.com/yourusername/tarot_agent",
                    "X-Title": "Tarot Agent"
                }
            else:
                api_key = settings.openai_api_key
                base_url = None
                default_headers = {}
            
            client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url,
                default_headers=default_headers if default_headers else None
            )
            
            # 使用模型配置系统获取意象生成模型
            model_config = get_model_config()
            model = model_config.imagery_generation_model
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": imagery_prompt}
                ],
                temperature=0.7  # 较高温度以获得更富有创造性的描述
            )
            
            imagery_description = response.choices[0].message.content.strip()
            llm_response = response.choices[0].message.content.strip()  # 保存完整响应
            logger.info(f"Generated imagery description: {imagery_description[:100]}...")
            # 保存到实例变量，以便后续使用
            self._last_imagery_description = imagery_description
            # 保存prompt和response到实例变量，以便在_save_process_data中使用
            self._last_imagery_prompt = imagery_prompt
            self._last_imagery_llm_response = llm_response
            self._last_imagery_model = model  # 保存实际使用的模型名称
            return imagery_description
            
        except Exception as e:
            logger.error(f"Failed to generate imagery description: {e}")
            # 返回默认描述
            return "基于牌阵的视觉意象，这些牌共同构成了一个独特的画面，反映了当前问题的核心能量。"
    
    async def _generate_spread_imagery_description_stream(
        self,
        selected_cards: List[SelectedCard],
        card_information: Dict[str, Any],
        question_domain: str
    ):
        """
        流式生成牌阵意象描述（Generator版本，用于SSE流式输出）
        
        Yields:
            文本块（chunks）
        """
        # 复用现有的prompt构建逻辑
        visual_descriptions = []
        
        # 从card_information中提取视觉描述
        for card in selected_cards:
            card_info = card_information.get(card.card_id, {})
            all_chunks = card_info.get('chunks', [])
            
            # 查找视觉描述相关chunks
            card_visual_texts = []
            for chunk in all_chunks:
                text = chunk.get('text', '').lower()
                if any(keyword in text for keyword in ['image', 'visual', 'appearance', 'depicts', 'shows', 'picture', 'illustration']):
                    chunk_text = chunk.get('text', '')
                    if len(chunk_text) > 300:
                        chunk_text = chunk_text[:300] + "..."
                    card_visual_texts.append(chunk_text)
                    if len(card_visual_texts) >= 3:  # 最多取3个
                        break
            
            if card_visual_texts:
                visual_descriptions.append({
                    'card_name': card.card_name_en,
                    'position': card.position,
                    'is_reversed': card.is_reversed,
                    'descriptions': card_visual_texts
                })
        
        # 如果没有找到视觉描述，使用默认描述
        if not visual_descriptions:
            logger.warning("No visual descriptions found, using default description")
            yield "基于牌阵的视觉意象，这些牌共同构成了一个独特的画面，反映了当前问题的核心能量。"
            return
        
        # 构建prompt
        visual_info_lines = []
        for desc in visual_descriptions:
            card_desc = f"{desc['card_name']}"
            if desc['position']:
                card_desc += f" ({desc['position']}位置)"
            if desc['is_reversed']:
                card_desc += " [逆位]"
            card_desc += ":\n"
            card_desc += "\n".join([f"  - {d}" for d in desc['descriptions']])
            visual_info_lines.append(card_desc)
        
        visual_info = "\n\n".join(visual_info_lines)
        
        imagery_prompt = f"""You are an experienced Tarot reader. Based on the visual descriptions of the following cards and the question domain, generate a comprehensive spread imagery description.

## Question Domain:
{question_domain}

## Cards in the Spread and Their Visual Descriptions:
{visual_info}

## Requirements:
Please generate a creative, imaginative, and aesthetically pleasing comprehensive imagery description, 3-5 sentences in length. This description should paint the entire spread as a vivid, symbolic picture.
1. **Creative Integration**: Do not merely list the visual elements of the cards, but fuse them into a coherent, dynamic scene or story.
2. **Deep Association**: Combine with the context of the question domain ({question_domain}), engage in divergent thinking, and explore the deeper symbols and metaphors behind the imagery.
3. **Atmosphere Creation**: Vividly depict the overall energy, atmosphere, and emotional tone of the spread.
4. **Beautiful Language**: Output in Chinese, with poetic and vivid language that captivates.

**Important Note**: The visual descriptions provided by RAG may contain duplicate or inaccurate information. Please use critical thinking to filter and integrate the information, creating the most appropriate and inspiring imagery.

Please output the imagery description directly without any other explanations."""
        
        # 调用LLM流式生成意象描述
        try:
            import openai
            
            if settings.use_openrouter and settings.openrouter_api_key:
                api_key = settings.openrouter_api_key
                base_url = "https://openrouter.ai/api/v1"
                default_headers = {
                    "HTTP-Referer": "https://github.com/yourusername/tarot_agent",
                    "X-Title": "Tarot Agent"
                }
            else:
                api_key = settings.openai_api_key
                base_url = None
                default_headers = {}
            
            client = openai.OpenAI(
                api_key=api_key,
                base_url=base_url,
                default_headers=default_headers if default_headers else None
            )
            
            # 使用模型配置系统获取意象生成模型
            model_config = get_model_config()
            model = model_config.imagery_generation_model
            
            stream = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": imagery_prompt}
                ],
                temperature=0.7,
                stream=True  # 启用流式输出
            )
            
            # 流式yield每个chunk
            full_text = []
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    full_text.append(text_chunk)
                    yield text_chunk
            
            # 保存到实例变量以便后续保存
            complete_text = ''.join(full_text)
            self._last_imagery_description = complete_text
            self._last_imagery_prompt = imagery_prompt
            self._last_imagery_llm_response = complete_text
            self._last_imagery_model = model
            
        except Exception as e:
            logger.error(f"Failed to generate imagery description: {e}")
            yield "基于牌阵的视觉意象，这些牌共同构成了一个独特的画面，反映了当前问题的核心能量。"
    
    def _build_interpretation_prompt(
        self,
        question: str,
        question_analysis: QuestionAnalysis,
        selected_cards: List[SelectedCard],
        pattern_analysis_dict: Dict[str, Any],
        card_information: Dict[str, Any],
        spread_method: Dict[str, Any],
        card_relationships: Optional[Dict[str, Any]] = None,
        user_profile: Optional[UserProfileCreate] = None,
        all_chunks: Optional[List[Dict[str, Any]]] = None,
        spread_imagery_description: Optional[str] = None,
        language: str = 'zh'
    ) -> str:
        """Build the final interpretation prompt"""
        
        # Get output language from user profile or default to 'zh'
        output_language = language
        if user_profile and user_profile.language:
            output_language = user_profile.language
        
        # Language mapping - explicitly specify Simplified Chinese to avoid Traditional Chinese output
        language_map = {
            'zh': 'Simplified Chinese',  # 明确指定简体中文，避免某些模型（如Gemini）输出繁体中文
            'en': 'English'
        }
        output_language_name = language_map.get(output_language, 'Simplified Chinese')
        
        # Format spread information
        spread_info_lines = []
        for card in selected_cards:
            card_info = card_information.get(card.card_id, {})
            line = f"{card.position_order}. {card.position}: {card.card_name_en}"
            if card.is_reversed:
                line += " [Reversed]"
            spread_info_lines.append(line)
        
        spread_info = "\n".join(spread_info_lines)
        
        # Format user information
        user_info = "None"
        if user_profile:
            parts = []
            if user_profile.age:
                parts.append(f"Age: {user_profile.age}")
            if user_profile.gender:
                parts.append(f"Gender: {user_profile.gender}")
            if user_profile.zodiac_sign:
                parts.append(f"Zodiac Sign: {user_profile.zodiac_sign}")
            user_info = "\n".join(parts) if parts else "None"
        
        # Format all RAG-retrieved chunks (raw text, not processed by LLM)
        context_chunks = []
        if all_chunks:
            for i, chunk in enumerate(all_chunks[:50], 1):  # Limit to 50 chunks
                text = chunk.get('text', '')
                source = chunk.get('source', 'Unknown')
                similarity = chunk.get('similarity', 0)
                # Truncate overly long text
                if len(text) > 500:
                    text = text[:500] + "..."
                context_chunks.append(f"[{i}] [{source}] (Similarity: {similarity:.2f})\n{text}")
        
        context_text = "\n\n".join(context_chunks) if context_chunks else "No relevant information"
        
        # Add imagery description section
        imagery_section = ""
        if spread_imagery_description:
            imagery_section = f"""
## Spread Imagery Description:
{spread_imagery_description}

This imagery description integrates all visual elements of the cards and reflects the overall energy and atmosphere of the spread. When interpreting, please pay special attention to this imagery description, as it can help you understand the overall picture and deeper meanings of the spread."""
        
        prompt = f"""# Role Setting

You are an experienced and insightful Tarot reader. Your reading style is not to simply recite card meanings, but to weave the card imagery, the querent's question, and your intuitive impressions into a complete, coherent, and guiding narrative. Please maintain an objective, neutral, and empathetic tone.

# Background Information for the Reading

## Querent's Question:

{question}

## Question Analysis:

- Domain: {question_analysis.question_domain}

- Type: {question_analysis.question_type}

## Spread and Cards:

{spread_info}

## Core Intuitive Imagery:

{spread_imagery_description}

(This imagery is the intuitive core of this reading. It is crucial that you use it as the main thread and source of inspiration for the interpretation.)

## Pattern Analysis Results (Macro-level Energy Scan):

{pattern_analysis_dict}

## RAG Retrieved Information (Raw Document Snippets):

{context_text}

# Reading Task Instructions

Please strictly follow the format below to provide a rich, detailed, complete and in-depth Tarot reading:

**Overall Atmosphere Analysis**

Before delving into individual cards, conduct a macro-level "energy scan" of the entire spread based on the [Pattern Analysis Results] and briefly explain its meaning:

- **Major/Minor Arcana Ratio Analysis**: Based on `major_arcana_patterns`, analyze whether the fundamental level of the issue leans towards "major life lessons" (Major Arcana dominant) or "specific matters of daily life" (Minor Arcana dominant).

- **Elemental Distribution Analysis**: Based on `suit_distribution`, identify the most prominent elemental energy (driving force) and any missing elements (areas needing attention).

- **Numeric Energy Analysis**: Based on `number_patterns`, determine the current developmental stage of the situation (e.g., beginning, conflict, stability, completion).

**Construct the Core Narrative**

This is the core part of the reading. Please weave a smooth, logical story by combining the [Core Intuitive Imagery] you received with all the background information. **In this section, focus more on building from the imagery and narrative of the cards.** Use the [Core Intuitive Imagery] as the central thread running through the entire interpretation. Narrate according to the spread's sequence (e.g., Past-Present-Future), explaining how one card develops into the next to reveal the underlying causal logic.

**The Oracle's Answer**

This is the culminating section where you must concentrate your intuitive faculties and provide a comprehensive answer to the querent's question. Based on all the analysis and narrative from the previous sections, you should now directly address the specific question that brought the querent to this reading.

In this section, please provide a detailed and thorough response that:

1. **Directly Addresses the Question**: Return to the querent's original question and provide a clear, direct answer based on what the cards have revealed. Do not be vague or evasive—the querent has come seeking guidance, and you must offer it with clarity and conviction.

2. **Synthesize All Insights**: Draw together all the threads from your previous analysis—the overall atmosphere, the core narrative, the pattern meanings, and the intuitive imagery. Show how these elements converge to form a coherent answer to the question.

3. **Reveal the Core Message**: Distill the essential message that the spread communicates regarding the querent's specific situation. What is the fundamental truth or direction that emerges from this reading? What does the querent most need to understand about their question?

4. **Indicate the Likely Outcome**: Based on the energy patterns, card positions, and narrative flow, describe what is likely to come to pass if current trends continue. Be specific about timing, circumstances, and the nature of the outcome, while remaining mindful that the future is not fixed and the querent has agency.

5. **Provide Context and Nuance**: Explain any important conditions, factors, or circumstances that may influence the outcome. Are there particular energies that need to be balanced? Are there obstacles to be aware of, or opportunities to seize?

6. **Connect to the Querent's Life**: Make the answer relevant and meaningful to the querent's actual situation. Reference the question domain and type to ensure your answer speaks directly to their concerns and circumstances.

This section should be substantial and comprehensive—typically 3-5 paragraphs in length—as it represents the heart of what the querent seeks from this reading. It is here that the cards speak most directly to their question, and you must ensure that your answer is both insightful and actionable.

**Provide Actionable Guidance**

Finally, based on all the analysis above, provide specific, positive, and actionable advice.

- **Positive Guidance**: Even if the cards show challenges, find the lessons for growth and the potential for transformation within them.

- **Specific Suggestions**: Based on the energy analysis from the Overall Atmosphere Analysis (e.g., missing elements) and the insights from The Oracle's Answer, propose 1-2 concrete action steps.

- **Emphasize Personal Agency**: At the end, reiterate that the cards reveal current energy trends and possibilities, but the querent holds the ultimate power to shape their own future.

# Important Instructions

- **Critical Thinking**: The [RAG Retrieved Information] may contain repetitive, contradictory, or not entirely accurate content. You must act as an expert to critically filter, integrate, and refine this information to form a logically coherent and insightful reading.

- **Output Language**: Please generate your complete reading in **{output_language_name}** and use Markdown formatting for optimal readability.

- **Readability and Clarity**: The reader of this interpretation may know little or nothing about Tarot divination. Please minimize the use of technical terms and jargon. When it is necessary to use Tarot-specific terms (such as "Major Arcana," "reversed," "suit," etc.), provide clear explanations or context so that a layperson can understand. Throughout the entire reading, provide detailed and comprehensive explanations, ensuring that every concept, symbol, and insight is thoroughly explained in plain, easy-to-understand language. Your goal is to make the reading meaningful and accessible even to someone encountering Tarot for the first time.

"""
        
        return prompt
    
    def _format_interpretation(self, interpretation: FinalInterpretation) -> str:
        """格式化解读为文本"""
        lines = [f"## 整体解读\n\n{interpretation.overall_summary}\n"]
        
        if interpretation.position_interpretations:
            lines.append("\n## 位置解读\n")
            for pos in interpretation.position_interpretations:
                lines.append(f"### {pos.position_order}. {pos.position}: {pos.card_name_en}")
                if pos.card_name_cn:
                    lines.append(f"({pos.card_name_cn})\n")
                lines.append(f"{pos.interpretation}\n")
        
        if interpretation.relationship_analysis:
            lines.append(f"\n## 关系分析\n\n{interpretation.relationship_analysis}\n")
        
        if interpretation.pattern_explanation:
            lines.append(f"\n## 模式解释\n\n{interpretation.pattern_explanation}\n")
        
        if interpretation.advice:
            lines.append(f"\n## 建议\n\n{interpretation.advice}\n")
        
        if interpretation.references:
            lines.append("\n## 参考来源\n")
            for ref in interpretation.references:
                lines.append(f"- {ref.source}")
        
        return "\n".join(lines)
    
    def _selected_card_to_dict(self, card: SelectedCard) -> Dict[str, Any]:
        """将SelectedCard转换为字典"""
        return {
            'card_id': card.card_id,
            'card_name_en': card.card_name_en,
            'card_name_cn': card.card_name_cn,
            'suit': card.suit,
            'card_number': card.card_number,
            'arcana': card.arcana,
            'position': card.position,
            'position_order': card.position_order,
            'position_description': card.position_description,
            'is_reversed': card.is_reversed,
            'image_url': card.image_url  # 包含卡牌图像URL
        }
    
    def _analyze_spread_pattern_code(
        self,
        selected_cards: List[SelectedCard],
        spread_type: str,
        question_domain: str
    ) -> Dict[str, Any]:
        """
        纯代码实现牌型分析（不使用LLM）
        
        分析内容：
        1. 位置关系：时间线、因果、支持/对抗
        2. 数字模式：相同数字、数字序列、数字跳跃
        3. 花色分布：各花色的分布和平衡
        4. 大阿卡纳模式：大阿卡纳的数量、位置、意义
        5. 逆位模式：逆位牌的数量和含义
        6. 特殊组合：宫廷牌组合、相同牌等
        
        Args:
            selected_cards: 选中的牌列表
            spread_type: 占卜方式
            question_domain: 问题领域
            
        Returns:
            牌型分析结果字典
        """
        # 1. 位置关系分析
        position_relationships = self._analyze_position_relationships(selected_cards, spread_type)
        
        # 2. 数字模式分析
        number_patterns = self._analyze_number_patterns(selected_cards)
        
        # 3. 花色分布分析
        suit_distribution = self._analyze_suit_distribution(selected_cards)
        
        # 4. 大阿卡纳模式分析
        major_arcana_patterns = self._analyze_major_arcana_patterns(selected_cards)
        
        # 5. 逆位模式分析
        reversed_patterns = self._analyze_reversed_patterns(selected_cards)
        
        # 6. 特殊组合分析
        special_combinations = self._analyze_special_combinations(selected_cards)
        
        return {
            'analysis_method': 'code_based',
            'position_relationships': position_relationships,
            'number_patterns': number_patterns,
            'suit_distribution': suit_distribution,
            'major_arcana_patterns': major_arcana_patterns,
            'reversed_patterns': reversed_patterns,
            'special_combinations': special_combinations
        }
    
    def _analyze_position_relationships(
        self,
        cards: List[SelectedCard],
        spread_type: str
    ) -> Dict[str, Any]:
        """分析位置关系 - 输出为英文"""
        # 时间线关系（适用于三牌占卜和凯尔特十字）
        time_flow = ""
        if spread_type == 'three_card':
            time_flow = f"Past → Present → Future: {cards[0].card_name_en if len(cards) > 0 else 'N/A'} → {cards[1].card_name_en if len(cards) > 1 else 'N/A'} → {cards[2].card_name_en if len(cards) > 2 else 'N/A'}"
        elif spread_type == 'celtic_cross':
            # 凯尔特十字有更复杂的位置关系
            time_flow = "Celtic Cross: Current Situation → Challenge → Past → Future → Goal → Near Future → Attitude → Environment → Hopes & Fears → Outcome"
        
        # 因果关系（简化分析）
        causal_relationships = []
        if len(cards) >= 2:
            for i in range(len(cards) - 1):
                if cards[i].position and cards[i+1].position:
                    causal_relationships.append(f"{cards[i].position} → {cards[i+1].position}")
        
        # 支持/对抗关系（简化分析：相同花色为支持，不同花色为对抗）
        support_conflict = ""
        if len(cards) >= 2:
            suits = [card.suit for card in cards]
            unique_suits = set(suits)
            suit_names = {'wands': 'Wands', 'cups': 'Cups', 'swords': 'Swords', 'pentacles': 'Pentacles'}
            if len(unique_suits) == 1:
                suit_name = suit_names.get(suits[0], suits[0])
                support_conflict = f"All cards are {suit_name} suit, indicating unified element and mutual support"
            elif len(unique_suits) == len(cards):
                support_conflict = "All cards are different suits, indicating diverse elements, possible conflicts or balance"
            else:
                suit_list = ', '.join([suit_names.get(s, s) for s in unique_suits])
                support_conflict = f"Suit distribution: {suit_list}, indicating mixed elements requiring balance"
        
        return {
            'time_flow': time_flow,
            'causal_relationships': causal_relationships,
            'support_conflict': support_conflict
        }
    
    def _analyze_number_patterns(self, cards: List[SelectedCard]) -> Dict[str, Any]:
        """分析数字模式 - 输出为英文"""
        # 提取数字（大阿卡纳使用card_number，小阿卡纳也使用card_number）
        numbers = [card.card_number for card in cards if card.arcana == 'minor']
        major_numbers = [card.card_number for card in cards if card.arcana == 'major']
        
        # 相同数字
        same_numbers = []
        from collections import Counter
        number_counts = Counter(numbers)
        for num, count in number_counts.items():
            if count > 1:
                same_numbers.append(f"Number {num} appears {count} times")
        
        # 数字序列（连续数字）
        number_sequences = []
        if len(numbers) >= 2:
            sorted_numbers = sorted(set(numbers))
            for i in range(len(sorted_numbers) - 1):
                if sorted_numbers[i+1] - sorted_numbers[i] == 1:
                    sequence = [sorted_numbers[i], sorted_numbers[i+1]]
                    if sequence not in number_sequences:
                        number_sequences.append(f"Number sequence: {sequence[0]} → {sequence[1]}")
        
        # 数字跳跃（大间隔）
        number_jumps = []
        if len(numbers) >= 2:
            sorted_numbers = sorted(set(numbers))
            for i in range(len(sorted_numbers) - 1):
                jump = sorted_numbers[i+1] - sorted_numbers[i]
                if jump > 3:
                    number_jumps.append(f"Number jump: {sorted_numbers[i]} → {sorted_numbers[i+1]} (gap: {jump})")
        
        return {
            'same_numbers': same_numbers if same_numbers else [],
            'number_sequences': number_sequences if number_sequences else [],
            'number_jumps': number_jumps if number_jumps else [],
            'major_numbers': major_numbers if major_numbers else []
        }
    
    def _analyze_suit_distribution(self, cards: List[SelectedCard]) -> Dict[str, Any]:
        """分析花色分布 - 输出为英文"""
        suits = {'wands': 0, 'cups': 0, 'swords': 0, 'pentacles': 0, 'major': 0}
        
        for card in cards:
            if card.arcana == 'major':
                suits['major'] += 1
            elif card.suit in suits:
                suits[card.suit] += 1
        
        # 解释
        interpretation = ""
        total_minor = sum(suits[s] for s in ['wands', 'cups', 'swords', 'pentacles'])
        if suits['major'] > total_minor:
            interpretation = f"Major Arcana dominant ({suits['major']} cards), indicating major themes and spiritual influences"
        elif total_minor > 0:
            element_counts = {
                'wands': suits['wands'],
                'cups': suits['cups'],
                'swords': suits['swords'],
                'pentacles': suits['pentacles']
            }
            max_element = max(element_counts.items(), key=lambda x: x[1])
            element_names = {'wands': 'Wands', 'cups': 'Cups', 'swords': 'Swords', 'pentacles': 'Pentacles'}
            interpretation = f"Element distribution: Wands {suits['wands']}, Cups {suits['cups']}, Swords {suits['swords']}, Pentacles {suits['pentacles']}. {element_names.get(max_element[0], max_element[0])} element is more prominent"
        else:
            interpretation = "All cards are Major Arcana, indicating complete spiritual influence"
        
        return {
            'wands_count': suits['wands'],
            'cups_count': suits['cups'],
            'swords_count': suits['swords'],
            'pentacles_count': suits['pentacles'],
            'major_count': suits['major'],
            'interpretation': interpretation
        }
    
    def _analyze_major_arcana_patterns(self, cards: List[SelectedCard]) -> Dict[str, Any]:
        """分析大阿卡纳模式 - 输出为英文"""
        major_cards = [card for card in cards if card.arcana == 'major']
        major_positions = [card.position for card in major_cards if card.position]
        
        meaning = ""
        if len(major_cards) == 0:
            meaning = "No Major Arcana, indicating daily affairs and specific events"
        elif len(major_cards) == 1:
            meaning = f"Only 1 Major Arcana ({major_cards[0].card_name_en}), indicating a single major theme"
        elif len(major_cards) >= len(cards) // 2:
            meaning = f"Major Arcana in majority ({len(major_cards)} cards), indicating major transitions and spiritual growth"
        else:
            meaning = f"Moderate number of Major Arcana ({len(major_cards)} cards), indicating balance between spiritual and mundane matters"
        
        return {
            'count': len(major_cards),
            'positions': major_positions,
            'meaning': meaning
        }
    
    def _analyze_reversed_patterns(self, cards: List[SelectedCard]) -> Dict[str, Any]:
        """分析逆位模式 - 输出为英文"""
        reversed_cards = [card for card in cards if card.is_reversed]
        reversed_positions = [card.position for card in reversed_cards if card.position]
        
        interpretation = ""
        reversal_rate = len(reversed_cards) / len(cards) if cards else 0
        if reversal_rate == 0:
            interpretation = "All cards are upright, indicating smooth energy flow and normal development"
        elif reversal_rate < 0.3:
            interpretation = f"Few reversed cards ({len(reversed_cards)} cards), indicating mostly smooth energy flow with a few areas needing attention"
        elif reversal_rate < 0.7:
            interpretation = f"Moderate number of reversed cards ({len(reversed_cards)} cards), indicating mixed energy requiring balance between upright and reversed influences"
        else:
            interpretation = f"Many reversed cards ({len(reversed_cards)} cards), indicating blocked energy requiring special attention to reversed meanings"
        
        return {
            'count': len(reversed_cards),
            'positions': reversed_positions,
            'interpretation': interpretation
        }
    
    def _analyze_special_combinations(self, cards: List[SelectedCard]) -> List[str]:
        """分析特殊组合 - 输出为英文"""
        combinations = []
        
        # 宫廷牌组合
        court_cards = [card for card in cards if any(court in card.card_name_en.lower() for court in ['king', 'queen', 'knight', 'page'])]
        if len(court_cards) >= 2:
            combinations.append(f"Court card combination: {', '.join([c.card_name_en for c in court_cards])}, may represent people or personality traits")
        
        # 相同牌（基于card_name_en）
        from collections import Counter
        card_names = [card.card_name_en for card in cards]
        name_counts = Counter(card_names)
        duplicates = [name for name, count in name_counts.items() if count > 1]
        if duplicates:
            combinations.append(f"Duplicate cards: {', '.join(duplicates)}, indicating the importance of this theme")
        
        # 相同花色组合（小阿卡纳）
        minor_cards = [card for card in cards if card.arcana == 'minor']
        if len(minor_cards) >= 2:
            suits = [card.suit for card in minor_cards]
            suit_counts = Counter(suits)
            dominant_suit = max(suit_counts.items(), key=lambda x: x[1]) if suit_counts else None
            if dominant_suit and dominant_suit[1] >= 2:
                suit_names = {'wands': 'Wands', 'cups': 'Cups', 'swords': 'Swords', 'pentacles': 'Pentacles'}
                suit_name = suit_names.get(dominant_suit[0], dominant_suit[0])
                combinations.append(f"{suit_name} suit dominant ({dominant_suit[1]} cards), indicating strong influence of this element")
        
        return combinations if combinations else []
    
    async def _save_process_data(
        self,
        reading_id: str,
        step_name: str,
        step_order: int,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        prompt_type: Optional[str] = None,
        prompt_content: Optional[str] = None,
        rag_queries: Optional[List[Dict[str, Any]]] = None,
        model_used: Optional[str] = None,
        temperature: Optional[float] = None,
        processing_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        error_message: Optional[str] = None,
        error_traceback: Optional[str] = None
    ):
        """
        保存占卜过程数据到 reading_process_data 表
        
        Args:
            reading_id: 占卜ID
            step_name: 步骤名称
            step_order: 步骤顺序
            input_data: 输入数据（字典）
            output_data: 输出数据（字典）
            prompt_type: Prompt类型
            prompt_content: Prompt内容
            rag_queries: RAG查询列表
            model_used: 使用的模型
            temperature: 温度参数
            processing_time_ms: 处理时间（毫秒）
            tokens_used: 使用的token数
            error_message: 错误消息
            error_traceback: 错误堆栈
        """
        try:
            process_data = {
                'reading_id': reading_id,
                'step_name': step_name,
                'step_order': step_order,
                'input_data': input_data,
                'output_data': output_data,
                'prompt_type': prompt_type,
                'prompt_content': prompt_content,
                'rag_queries': rag_queries,
                'model_used': model_used,
                'temperature': temperature,
                'processing_time_ms': processing_time_ms,
                'tokens_used': tokens_used,
                'error_message': error_message,
                'error_traceback': error_traceback
            }
            
            # 移除None值
            process_data = {k: v for k, v in process_data.items() if v is not None}
            
            self.supabase.table('reading_process_data').insert(process_data).execute()
            logger.debug(f"Process data saved for step: {step_name} (order: {step_order})")
        except Exception as e:
            # 记录过程数据失败不应该影响主流程
            logger.warning(f"Failed to save process data for step {step_name}: {e}")


# 全局服务实例
reading_service = ReadingService()

