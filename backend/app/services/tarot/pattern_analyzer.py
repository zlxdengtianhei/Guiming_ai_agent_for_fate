"""
牌型分析服务 - 使用LLM分析牌阵中的模式、关系和特殊组合
支持两种方式：直接LLM分析和RAG增强分析
"""

import json
import logging
import time
from typing import List, Dict, Any, Optional
import openai
from app.core.config import settings
from app.services.rag import rag_service
from app.services.tarot.card_selection import SelectedCard

logger = logging.getLogger(__name__)


class PatternAnalyzerService:
    """牌型分析服务 - 使用LLM"""
    
    # 直接LLM分析Prompt模板
    PATTERN_ANALYSIS_PROMPT = """你是一位经验丰富的塔罗占卜师。请分析以下牌阵的模式和关系。

## 占卜方式：{spread_type}
## 问题领域：{question_domain}

## 牌阵信息：
{spread_info}

## 分析要求：
1. **位置关系**：分析各位置之间的关系（时间线、因果、支持/对抗）
2. **数字模式**：识别相同数字、数字序列、数字跳跃
3. **花色分布**：分析各花色的分布和平衡
4. **大阿卡纳模式**：分析大阿卡纳的位置和意义
5. **逆位模式**：分析逆位牌的模式和含义
6. **特殊组合**：识别宫廷牌组合、相同牌等特殊模式

## 输出格式（JSON）：
{{
    "position_relationships": {{
        "time_flow": "描述时间线关系（如果有）",
        "causal_relationships": ["原因→结果的关系列表"],
        "support_conflict": "支持或对抗关系描述"
    }},
    "number_patterns": {{
        "same_numbers": ["相同数字和含义说明"],
        "number_sequences": ["数字序列和含义说明"],
        "number_jumps": ["数字跳跃和含义说明"]
    }},
    "suit_distribution": {{
        "wands_count": 0,
        "cups_count": 0,
        "swords_count": 0,
        "pentacles_count": 0,
        "major_count": 0,
        "interpretation": "花色分布的含义解释"
    }},
    "major_arcana_patterns": {{
        "count": 0,
        "positions": ["大阿卡纳的位置列表"],
        "meaning": "大阿卡纳模式的含义"
    }},
    "reversed_patterns": {{
        "count": 0,
        "positions": ["逆位牌的位置列表"],
        "interpretation": "逆位模式的含义解释"
    }},
    "special_combinations": ["特殊组合的描述列表"]
}}

请确保返回有效的JSON格式，不要包含任何其他文本。"""

    # RAG增强分析Prompt模板
    RAG_ENHANCED_PATTERN_ANALYSIS_PROMPT = """你是一位经验丰富的塔罗占卜师，精通PKT和78 Degrees of Wisdom的传统解读方法。请分析以下牌阵的模式和关系。

## 占卜方式：{spread_type}
## 问题领域：{question_domain}

## 牌阵信息：
{spread_info}

## 传统占卜方法指导：
{rag_context}

## 分析要求：
请结合传统占卜方法指导，分析以下内容：
1. **位置关系**：根据传统方法，分析各位置之间的关系（时间线、因果、支持/对抗）
2. **数字模式**：识别相同数字、数字序列、数字跳跃，并结合传统解读方法
3. **花色分布**：分析各花色的分布和平衡，参考传统元素理论
4. **大阿卡纳模式**：分析大阿卡纳的位置和意义，参考传统大阿卡纳解读
5. **逆位模式**：分析逆位牌的模式和含义，参考传统逆位解读方法
6. **特殊组合**：识别宫廷牌组合、相同牌等特殊模式，参考传统组合解读

## 输出格式（JSON）：
{{
    "position_relationships": {{
        "time_flow": "描述时间线关系（如果有）",
        "causal_relationships": ["原因→结果的关系列表"],
        "support_conflict": "支持或对抗关系描述"
    }},
    "number_patterns": {{
        "same_numbers": ["相同数字和含义说明"],
        "number_sequences": ["数字序列和含义说明"],
        "number_jumps": ["数字跳跃和含义说明"]
    }},
    "suit_distribution": {{
        "wands_count": 0,
        "cups_count": 0,
        "swords_count": 0,
        "pentacles_count": 0,
        "major_count": 0,
        "interpretation": "花色分布的含义解释"
    }},
    "major_arcana_patterns": {{
        "count": 0,
        "positions": ["大阿卡纳的位置列表"],
        "meaning": "大阿卡纳模式的含义"
    }},
    "reversed_patterns": {{
        "count": 0,
        "positions": ["逆位牌的位置列表"],
        "interpretation": "逆位模式的含义解释"
    }},
    "special_combinations": ["特殊组合的描述列表"]
}}

请确保返回有效的JSON格式，不要包含任何其他文本。"""
    
    def __init__(self):
        """初始化LLM客户端"""
        # 判断使用 OpenRouter 还是 OpenAI
        if settings.use_openrouter and settings.openrouter_api_key:
            api_key = settings.openrouter_api_key
            base_url = "https://openrouter.ai/api/v1"
            default_headers = {
                "HTTP-Referer": "https://github.com/yourusername/tarot_agent",
                "X-Title": "Tarot Agent"
            }
            logger.info(f"Using OpenRouter for pattern analysis: {base_url}")
        else:
            api_key = settings.openai_api_key
            base_url = None
            default_headers = {}
            logger.info("Using OpenAI for pattern analysis")
        
        self.openai_client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers if default_headers else None
        )
        # 使用较小的模型进行快速分析
        self.model = "gpt-4o-mini" if settings.use_openrouter else "gpt-4o-mini"
        self.temperature = 0.5  # 中等温度，需要一定创造性
    
    def _format_spread_info(self, selected_cards: List[SelectedCard]) -> str:
        """格式化牌阵信息为字符串"""
        lines = []
        for card in selected_cards:
            card_info = f"{card.position_order}. {card.position}"
            if card.position_description:
                card_info += f" ({card.position_description})"
            card_info += f": {card.card_name_en}"
            if card.card_name_cn:
                card_info += f" ({card.card_name_cn})"
            card_info += f" - {card.suit}"
            if card.arcana == "major":
                card_info += f" ({card.arcana})"
            else:
                card_info += f" {card.card_number}"
            if card.is_reversed:
                card_info += " [逆位]"
            lines.append(card_info)
        return "\n".join(lines)
    
    async def _call_llm_for_analysis(
        self,
        prompt: str
    ) -> Dict[str, Any]:
        """
        调用LLM进行牌型分析
        
        Args:
            prompt: 完整的prompt文本
            
        Returns:
            分析结果字典
        """
        try:
            logger.info(f"Calling LLM for pattern analysis")
            start_time = time.time()
            
            # 尝试使用response_format（某些模型可能不支持）
            try:
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature,
                    response_format={"type": "json_object"}  # 强制JSON输出
                )
            except Exception as e:
                # 如果response_format不支持，尝试不使用它
                logger.warning(f"Response format not supported, retrying without it: {e}")
                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=self.temperature
                )
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # 解析响应
            raw_content = response.choices[0].message.content
            logger.info(f"LLM response received ({processing_time_ms}ms)")
            
            # 保存原始响应
            original_response = raw_content
            
            # 清理响应内容（移除可能的markdown代码块）
            content = raw_content.strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()
            
            # 解析JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {content[:200]}...")
                raise ValueError(f"LLM返回的JSON格式无效: {e}")
            
            # 将原始响应添加到结果中
            result['_raw_response'] = original_response
            
            # 验证必需字段
            required_fields = [
                "position_relationships", "number_patterns", "suit_distribution",
                "major_arcana_patterns", "reversed_patterns", "special_combinations"
            ]
            
            for field in required_fields:
                if field not in result:
                    logger.warning(f"Missing field in pattern analysis result: {field}")
                    # 设置默认值
                    if field == "position_relationships":
                        result[field] = {"time_flow": "", "causal_relationships": [], "support_conflict": ""}
                    elif field == "number_patterns":
                        result[field] = {"same_numbers": [], "number_sequences": [], "number_jumps": []}
                    elif field == "suit_distribution":
                        result[field] = {"wands_count": 0, "cups_count": 0, "swords_count": 0, 
                                         "pentacles_count": 0, "major_count": 0, "interpretation": ""}
                    elif field == "major_arcana_patterns":
                        result[field] = {"count": 0, "positions": [], "meaning": ""}
                    elif field == "reversed_patterns":
                        result[field] = {"count": 0, "positions": [], "interpretation": ""}
                    elif field == "special_combinations":
                        result[field] = []
            
            logger.info(f"Pattern analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze pattern: {e}")
            raise
    
    async def analyze_spread_pattern_direct(
        self,
        selected_cards: List[SelectedCard],
        spread_type: str,
        question_domain: str
    ) -> Dict[str, Any]:
        """
        直接使用LLM分析牌型模式（不使用RAG）
        
        Args:
            selected_cards: 选中的牌列表
            spread_type: 占卜方式（'three_card'/'celtic_cross'等）
            question_domain: 问题领域
            
        Returns:
            牌型分析结果字典
        """
        try:
            # 格式化牌阵信息
            spread_info = self._format_spread_info(selected_cards)
            
            # 构建Prompt
            prompt = self.PATTERN_ANALYSIS_PROMPT.format(
                spread_type=spread_type,
                question_domain=question_domain,
                spread_info=spread_info
            )
            
            # 调用LLM
            result = await self._call_llm_for_analysis(prompt)
            
            # 添加元数据
            result['analysis_method'] = 'direct_llm'
            result['model_used'] = self.model
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze spread pattern (direct): {e}")
            raise
    
    async def analyze_spread_pattern_rag(
        self,
        selected_cards: List[SelectedCard],
        spread_type: str,
        question_domain: str
    ) -> Dict[str, Any]:
        """
        使用RAG增强分析牌型模式
        
        步骤：
        1. 构建查询，检索传统占卜方法相关信息
        2. 使用RAG检索结果作为上下文
        3. 调用LLM进行增强分析
        
        Args:
            selected_cards: 选中的牌列表
            spread_type: 占卜方式（'three_card'/'celtic_cross'等）
            question_domain: 问题领域
            
        Returns:
            牌型分析结果字典
        """
        try:
            # 格式化牌阵信息
            spread_info = self._format_spread_info(selected_cards)
            
            # 构建RAG查询 - 检索占卜方法相关的传统解读
            rag_queries = [
                f"{spread_type} spread interpretation method",
                f"how to interpret tarot card patterns in {spread_type}",
                f"traditional tarot reading patterns for {spread_type}"
            ]
            
            # 收集RAG检索结果
            rag_contexts = []
            for query in rag_queries:
                try:
                    rag_result = await rag_service.answer_query(query, top_k=3)
                    if rag_result.get('text'):
                        rag_contexts.append(rag_result['text'])
                    # 添加引用信息
                    if rag_result.get('citations'):
                        rag_contexts.append(f"\n参考来源: {', '.join([c.get('source', '') for c in rag_result['citations']])}")
                except Exception as e:
                    logger.warning(f"RAG query failed for '{query}': {e}")
                    continue
            
            # 合并RAG上下文
            rag_context = "\n\n".join(rag_contexts) if rag_contexts else "未找到相关的传统占卜方法指导"
            
            # 构建增强Prompt
            prompt = self.RAG_ENHANCED_PATTERN_ANALYSIS_PROMPT.format(
                spread_type=spread_type,
                question_domain=question_domain,
                spread_info=spread_info,
                rag_context=rag_context
            )
            
            # 调用LLM
            result = await self._call_llm_for_analysis(prompt)
            
            # 添加元数据
            result['analysis_method'] = 'rag_enhanced'
            result['model_used'] = self.model
            result['rag_queries'] = rag_queries
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze spread pattern (RAG): {e}")
            raise
    
    async def analyze_spread_pattern(
        self,
        selected_cards: List[SelectedCard],
        spread_type: str,
        question_domain: str,
        use_rag: bool = False
    ) -> Dict[str, Any]:
        """
        分析牌型模式（统一接口）
        
        Args:
            selected_cards: 选中的牌列表
            spread_type: 占卜方式
            question_domain: 问题领域
            use_rag: 是否使用RAG增强（默认False，使用直接LLM分析）
            
        Returns:
            牌型分析结果字典
        """
        result = await self.analyze_spread_pattern_with_details(
            selected_cards, spread_type, question_domain, use_rag
        )
        return result['analysis']
    
    async def analyze_spread_pattern_with_details(
        self,
        selected_cards: List[SelectedCard],
        spread_type: str,
        question_domain: str,
        use_rag: bool = False
    ) -> Dict[str, Any]:
        """
        分析牌型模式并返回详细信息（包括prompt和LLM response）
        
        Args:
            selected_cards: 选中的牌列表
            spread_type: 占卜方式
            question_domain: 问题领域
            use_rag: 是否使用RAG增强（默认False，使用直接LLM分析）
            
        Returns:
            包含analysis、prompt、llm_response、processing_time_ms的字典
        """
        import time
        start_time = time.time()
        
        if use_rag:
            # RAG增强分析
            spread_info = self._format_spread_info(selected_cards)
            
            # 构建RAG查询
            rag_queries = [
                f"{spread_type} spread interpretation method",
                f"how to interpret tarot card patterns in {spread_type}",
                f"traditional tarot reading patterns for {spread_type}"
            ]
            
            # 收集RAG检索结果
            rag_contexts = []
            for query in rag_queries:
                try:
                    rag_result = await rag_service.answer_query(query, top_k=3)
                    if rag_result.get('text'):
                        rag_contexts.append(rag_result['text'])
                    if rag_result.get('citations'):
                        rag_contexts.append(f"\n参考来源: {', '.join([c.get('source', '') for c in rag_result['citations']])}")
                except Exception as e:
                    logger.warning(f"RAG query failed for '{query}': {e}")
                    continue
            
            rag_context = "\n\n".join(rag_contexts) if rag_contexts else "未找到相关的传统占卜方法指导"
            
            # 构建Prompt
            prompt = self.RAG_ENHANCED_PATTERN_ANALYSIS_PROMPT.format(
                spread_type=spread_type,
                question_domain=question_domain,
                spread_info=spread_info,
                rag_context=rag_context
            )
            
            # 调用LLM
            result = await self._call_llm_for_analysis(prompt)
            
            # 获取原始响应
            llm_response = result.pop('_raw_response', None)
            
            # 添加元数据
            result['analysis_method'] = 'rag_enhanced'
            result['model_used'] = self.model
            result['rag_queries'] = rag_queries
        else:
            # 直接LLM分析
            spread_info = self._format_spread_info(selected_cards)
            
            # 构建Prompt
            prompt = self.PATTERN_ANALYSIS_PROMPT.format(
                spread_type=spread_type,
                question_domain=question_domain,
                spread_info=spread_info
            )
            
            # 调用LLM
            result = await self._call_llm_for_analysis(prompt)
            
            # 获取原始响应
            llm_response = result.pop('_raw_response', None)
            
            # 添加元数据
            result['analysis_method'] = 'direct_llm'
            result['model_used'] = self.model
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            'analysis': result,
            'prompt': prompt,
            'llm_response': llm_response,
            'processing_time_ms': processing_time_ms
        }


# 全局服务实例
pattern_analyzer_service = PatternAnalyzerService()

