"""
问题分析服务 - 使用LLM分析用户问题，识别领域和复杂度
"""

import json
import logging
import time
from typing import Optional, Dict, Any
import openai
from app.core.config import settings
from app.core.model_config import get_model_config
from app.models.schemas import QuestionAnalysis, UserProfileCreate

logger = logging.getLogger(__name__)


class QuestionAnalyzerService:
    """问题分析服务 - 使用LLM"""
    
    # 问题分析Prompt模板
    QUESTION_ANALYSIS_PROMPT = """You are an experienced Tarot reader. Please analyze the following question and return the analysis result in JSON format.

## Question:
{question}

## User Information (Optional):
{user_profile_info}

## Analysis Requirements:
1. **Question Domain**: Identify the domain of the question, choose one from the following options:
   - 'love': Love, relationships, emotions
   - 'career': Career, work, profession
   - 'health': Health, body, recovery
   - 'finance': Finance, money, material matters
   - 'personal_growth': Personal growth, spirituality, self-exploration
   - 'general': General life, comprehensive questions

2. **Question Complexity** (if user has not specified a spread type): Judge based on the scope, depth, and time span of the question.
   - 'simple': Short-term, specific, single-focus questions. Examples: "Will I succeed in this interview?" or "How will my finances be next month?"
   - 'moderate': Questions involving multiple factors but with a clear core issue. Example: "How should I improve my relationship with my partner?"
   - 'complex': Questions involving long-term development, major life decisions, deep psychological exploration, or multiple interrelated complex issues. Examples: "What will my career path be like in the next five years?" or "What is the next important life lesson for me?"

3. **Question Type**:
   - 'specific_event': Specific events (e.g., "Will I get this job?")
   - 'relationship': Relationship questions (e.g., "How will our relationship develop?")
   - 'choice': Choice questions (e.g., "Which direction should I choose?")
   - 'general': General questions (e.g., "What will my future be like?")

4. **Recommended Spread** (if user has not specified):
   - 'three_card': Three-card spread
   - 'celtic_cross': Celtic Cross
   - 'work_cycle': Work cycle (if ongoing advice is needed)
   - 'other': Other (explain reason)

## Output Format (JSON):
{{
    "question_domain": "love",
    "complexity": "simple",
    "question_type": "relationship",
    "recommended_spread": "three_card",
    "reasoning": "This is a simple relationship question, a three-card spread can clearly answer the past-present-future development",
    "question_summary": "Brief summary of the question core"
}}

Please ensure you return valid JSON format without any other text."""

    # 简化版Prompt（当用户指定占卜方式时）
    SIMPLIFIED_QUESTION_ANALYSIS_PROMPT = """You are an experienced Tarot reader. Please analyze the following question and return the analysis result in JSON format.

## Question:
{question}

## User Information (Optional):
{user_profile_info}

## Analysis Requirements:
1. **Question Domain**: Identify the domain of the question, choose one from the following options:
   - 'love': Love, relationships, emotions
   - 'career': Career, work, profession
   - 'health': Health, body, recovery
   - 'finance': Finance, money, material matters
   - 'personal_growth': Personal growth, spirituality, self-exploration
   - 'general': General life, comprehensive questions

2. **Question Type**:
   - 'specific_event': Specific events (e.g., "Will I get this job?")
   - 'relationship': Relationship questions (e.g., "How will our relationship develop?")
   - 'choice': Choice questions (e.g., "Which direction should I choose?")
   - 'general': General questions (e.g., "What will my future be like?")

## Output Format (JSON):
{{
    "question_domain": "love",
    "question_type": "relationship",
    "reasoning": "This is a relationship question",
    "question_summary": "Brief summary of the question core"
}}

Please ensure you return valid JSON format without any other text."""
    
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
            logger.info(f"Using OpenRouter for question analysis: {base_url}")
        else:
            api_key = settings.openai_api_key
            base_url = None
            default_headers = {}
            logger.info("Using OpenAI for question analysis")
        
        self.openai_client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers if default_headers else None
        )
        # 模型将在每次调用时动态获取，而不是在初始化时获取
        self.temperature = 0.3  # 低温度确保结构化输出稳定
    
    def _get_model(self) -> str:
        """动态获取问题分析模型"""
        model_config = get_model_config()
        return model_config.question_analysis_model
    
    def _format_user_profile_info(
        self,
        user_profile: Optional[UserProfileCreate]
    ) -> str:
        """格式化用户信息为字符串"""
        if not user_profile:
            return "无"
        
        parts = []
        if user_profile.age:
            parts.append(f"年龄: {user_profile.age}")
        if user_profile.gender:
            parts.append(f"性别: {user_profile.gender}")
        if user_profile.zodiac_sign:
            parts.append(f"星座: {user_profile.zodiac_sign}")
        if user_profile.personality_type:
            parts.append(f"性格类型: {user_profile.personality_type}")
        # appearance_type已不再使用，保留字段但不在提示中显示
        
        return "\n".join(parts) if parts else "无"
    
    async def _call_llm_for_analysis(
        self,
        question: str,
        user_profile: Optional[UserProfileCreate],
        analyze_complexity: bool
    ) -> Dict[str, Any]:
        """
        调用LLM进行问题分析
        
        Args:
            question: 用户问题
            user_profile: 用户信息（可选）
            analyze_complexity: 是否分析复杂度（如果用户指定了占卜方式，则为False）
            
        Returns:
            分析结果字典
        """
        try:
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
            
            # 调用LLM
            logger.info(f"Calling LLM for question analysis: {question[:50]}...")
            start_time = time.time()
            
            # 动态获取模型
            model = self._get_model()
            
            # 尝试使用response_format（某些模型可能不支持）
            try:
                response = self.openai_client.chat.completions.create(
                    model=model,
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
                    model=model,
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
            required_fields = ["question_domain", "question_type", "reasoning", "question_summary"]
            if analyze_complexity:
                required_fields.extend(["complexity", "recommended_spread"])
            
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"LLM返回结果缺少必需字段: {field}")
            
            # 验证问题领域
            valid_domains = ['love', 'career', 'health', 'finance', 'personal_growth', 'general']
            if result['question_domain'] not in valid_domains:
                logger.warning(f"Invalid question_domain: {result['question_domain']}, defaulting to 'general'")
                result['question_domain'] = 'general'
            
            # 验证复杂度（如果存在）
            if analyze_complexity:
                valid_complexities = ['simple', 'moderate', 'complex']
                if result.get('complexity') not in valid_complexities:
                    logger.warning(f"Invalid complexity: {result.get('complexity')}, defaulting to 'moderate'")
                    result['complexity'] = 'moderate'
                
                # 验证推荐占卜方式
                valid_spreads = ['three_card', 'celtic_cross', 'work_cycle', 'other']
                if result.get('recommended_spread') not in valid_spreads:
                    logger.warning(f"Invalid recommended_spread: {result.get('recommended_spread')}, defaulting to 'three_card'")
                    result['recommended_spread'] = 'three_card'
            
            # 验证提问类型
            valid_types = ['specific_event', 'relationship', 'choice', 'general']
            if result['question_type'] not in valid_types:
                logger.warning(f"Invalid question_type: {result['question_type']}, defaulting to 'general'")
                result['question_type'] = 'general'
            
            logger.info(f"Question analysis completed: domain={result['question_domain']}, "
                       f"complexity={result.get('complexity')}, "
                       f"recommended_spread={result.get('recommended_spread')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze question: {e}")
            raise
    
    async def analyze_question(
        self,
        question: str,
        user_profile: Optional[UserProfileCreate] = None,
        user_selected_spread: Optional[str] = None
    ) -> QuestionAnalysis:
        """
        分析问题
        
        如果用户指定了占卜方式：
            - 只分析问题领域
            - 不分析复杂度
        
        如果系统自动选择：
            - 分析问题领域
            - 分析复杂度
            - 推荐占卜方式
        
        Args:
            question: 用户问题
            user_profile: 用户信息（可选）
            user_selected_spread: 用户指定的占卜方式（可选）
                - 如果为None或'auto'，则系统自动选择
                - 如果指定了占卜方式（如'three_card'/'celtic_cross'），则只分析问题领域
        
        Returns:
            QuestionAnalysis对象
        """
        result = await self.analyze_question_with_details(
            question=question,
            user_profile=user_profile,
            user_selected_spread=user_selected_spread
        )
        return result['analysis']
    
    async def analyze_question_with_details(
        self,
        question: str,
        user_profile: Optional[UserProfileCreate] = None,
        user_selected_spread: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析问题并返回详细信息（包括prompt和LLM response）
        
        Args:
            question: 用户问题
            user_profile: 用户信息（可选）
            user_selected_spread: 用户指定的占卜方式（可选）
        
        Returns:
            包含analysis、prompt、llm_response、processing_time_ms的字典
        """
        import time
        start_time = time.time()
        
        # 判断是否需要分析复杂度
        analyze_complexity = (
            user_selected_spread is None or 
            user_selected_spread.lower() == 'auto'
        )
        
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
        
        # 调用LLM进行分析
        analysis_result = await self._call_llm_for_analysis(
            question=question,
            user_profile=user_profile,
            analyze_complexity=analyze_complexity
        )
        
        # 获取LLM的原始响应
        llm_response = analysis_result.pop('_raw_response', None)
        
        # 确定最终使用的占卜方式
        auto_selected_spread = analyze_complexity
        final_spread = None
        
        if analyze_complexity:
            # 系统自动选择
            final_spread = analysis_result.get('recommended_spread', 'three_card')
        else:
            # 用户指定占卜方式
            final_spread = user_selected_spread
        
        # 构建QuestionAnalysis对象
        analysis = QuestionAnalysis(
            question_domain=analysis_result['question_domain'],
            complexity=analysis_result.get('complexity') if analyze_complexity else None,
            question_type=analysis_result['question_type'],
            recommended_spread=final_spread if analyze_complexity else None,
            reasoning=analysis_result['reasoning'],
            question_summary=analysis_result['question_summary'],
            auto_selected_spread=auto_selected_spread
        )
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # 获取实际使用的模型名称
        model_used = self._get_model()
        
        return {
            'analysis': analysis,
            'prompt': prompt,
            'llm_response': llm_response,
            'processing_time_ms': processing_time_ms,
            'model_used': model_used
        }


# 全局服务实例
question_analyzer_service = QuestionAnalyzerService()

