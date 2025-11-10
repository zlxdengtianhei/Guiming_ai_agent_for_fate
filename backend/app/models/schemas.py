"""
Pydantic schemas for request/response models
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class TarotCard(BaseModel):
    """Tarot card model."""
    card_id: str
    name: str
    suit: Optional[str] = None
    number: Optional[int] = None
    is_reversed: bool = False
    position: Optional[str] = None  # past, present, future, etc.


class TarotReading(BaseModel):
    """Tarot reading model."""
    id: str
    question: str
    spread_type: str
    cards: List[TarotCard]
    interpretation: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# =============================================================================
# 新增：用户个人信息相关模型
# =============================================================================

class UserProfileCreate(BaseModel):
    """创建用户信息请求模型"""
    age: Optional[int] = None
    gender: Optional[str] = None  # 'male'/'female'/'other'
    zodiac_sign: Optional[str] = None
    appearance_type: Optional[str] = None  # 'wands'/'cups'/'swords'/'pentacles' (保留字段，不再使用)
    personality_type: Optional[str] = None  # 'wands'/'cups'/'swords'/'pentacles'
    preferred_source: Optional[str] = 'pkt'  # 'pkt'/'78degrees'/'both'
    preferred_spread: Optional[str] = None  # 'auto'/'three_card'/'celtic_cross'/'work_cycle'
    language: Optional[str] = 'zh'  # 'zh'/'en' - Output language preference, default Chinese
    significator_priority: Optional[str] = 'question_first'  # 'question_first'/'personality_first'/'zodiac_first' - 代表牌选择优先级
    interpretation_model: Optional[str] = None  # 'deepseek'/'gpt4omini'/'gemini_2.5_pro' - 最终解读模型选择


class UserProfileUpdate(BaseModel):
    """更新用户信息请求模型"""
    age: Optional[int] = None
    gender: Optional[str] = None
    zodiac_sign: Optional[str] = None
    appearance_type: Optional[str] = None  # 保留字段，不再使用
    personality_type: Optional[str] = None
    preferred_source: Optional[str] = None
    preferred_spread: Optional[str] = None
    language: Optional[str] = None  # 'zh'/'en' - Output language preference
    significator_priority: Optional[str] = None  # 'question_first'/'personality_first' - 代表牌选择优先级
    interpretation_model: Optional[str] = None  # 'deepseek'/'gpt4omini'/'gemini_2.5_pro' - 最终解读模型选择


class UserProfileResponse(BaseModel):
    """用户信息响应模型"""
    id: str
    user_id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    zodiac_sign: Optional[str] = None
    appearance_type: Optional[str] = None  # 保留字段，不再使用
    personality_type: Optional[str] = None
    preferred_source: str = 'pkt'
    preferred_spread: Optional[str] = None
    language: str = 'zh'  # 'zh'/'en' - Output language preference, default Chinese
    significator_priority: str = 'question_first'  # 'question_first'/'personality_first' - 代表牌选择优先级
    interpretation_model: Optional[str] = None  # 'deepseek'/'gpt4omini'/'gemini_2.5_pro' - 最终解读模型选择
    created_at: datetime
    updated_at: datetime


# =============================================================================
# 新增：选牌相关模型
# =============================================================================

class SelectedCardModel(BaseModel):
    """选中的牌模型"""
    card_id: str
    card_name_en: str
    card_name_cn: Optional[str] = None
    suit: str
    card_number: int
    arcana: str
    position: str
    position_order: int
    position_description: Optional[str] = None
    is_reversed: bool


class SignificatorModel(BaseModel):
    """代表牌模型"""
    card_id: str
    card_name_en: str
    card_name_cn: Optional[str] = None
    suit: str
    selection_reason: str


# =============================================================================
# 新增：占卜相关模型
# =============================================================================

class ReadingCreate(BaseModel):
    """创建占卜请求模型"""
    question: str
    spread_type: Optional[str] = 'auto'  # 'auto'/'three_card'/'celtic_cross'
    user_profile: Optional[UserProfileCreate] = None


class ReadingResponse(BaseModel):
    """占卜响应模型"""
    reading_id: str
    question: str
    spread_type: str
    status: str
    significator: Optional[SignificatorModel] = None
    cards: List[SelectedCardModel]
    created_at: datetime
    updated_at: Optional[datetime] = None


# =============================================================================
# 新增：问题分析相关模型
# =============================================================================

class QuestionAnalysis(BaseModel):
    """问题分析结果模型"""
    question_domain: str  # 'love'/'career'/'health'/'finance'/'personal_growth'/'general'
    complexity: Optional[str] = None  # 'simple'/'moderate'/'complex' (仅当用户未指定占卜方式时)
    question_type: str  # 'specific_event'/'relationship'/'choice'/'general'
    recommended_spread: Optional[str] = None  # 'three_card'/'celtic_cross'/'work_cycle'/'other' (仅当用户未指定占卜方式时)
    reasoning: str  # 分析理由
    question_summary: str  # 问题摘要
    auto_selected_spread: bool = False  # 是否系统自动选择占卜方式


# =============================================================================
# 新增：牌型分析相关模型
# =============================================================================

class PositionRelationships(BaseModel):
    """位置关系分析"""
    time_flow: Optional[str] = ""  # 时间线关系
    causal_relationships: List[str] = []  # 因果关系列表
    support_conflict: Optional[str] = ""  # 支持或对抗关系


class NumberPatterns(BaseModel):
    """数字模式分析"""
    same_numbers: List[str] = []  # 相同数字和含义
    number_sequences: List[str] = []  # 数字序列和含义
    number_jumps: List[str] = []  # 数字跳跃和含义


class SuitDistribution(BaseModel):
    """花色分布分析"""
    wands_count: int = 0
    cups_count: int = 0
    swords_count: int = 0
    pentacles_count: int = 0
    major_count: int = 0
    interpretation: str = ""  # 花色分布的含义解释


class MajorArcanaPatterns(BaseModel):
    """大阿卡纳模式分析"""
    count: int = 0
    positions: List[str] = []  # 大阿卡纳的位置列表
    meaning: str = ""  # 大阿卡纳模式的含义


class ReversedPatterns(BaseModel):
    """逆位模式分析"""
    count: int = 0
    positions: List[str] = []  # 逆位牌的位置列表
    interpretation: str = ""  # 逆位模式的含义解释


class SpreadPatternAnalysis(BaseModel):
    """牌型分析结果模型"""
    position_relationships: PositionRelationships
    number_patterns: NumberPatterns
    suit_distribution: SuitDistribution
    major_arcana_patterns: MajorArcanaPatterns
    reversed_patterns: ReversedPatterns
    special_combinations: List[str] = []  # 特殊组合的描述
    analysis_method: Optional[str] = None  # 'direct_llm' 或 'rag_enhanced'
    model_used: Optional[str] = None  # 使用的模型
    rag_queries: Optional[List[str]] = None  # RAG查询列表（如果使用RAG）


# =============================================================================
# 新增：最终解读相关模型
# =============================================================================

class PositionInterpretation(BaseModel):
    """位置解读"""
    position: str  # 位置名称
    position_order: int  # 位置顺序
    card_name_en: str  # 卡牌英文名
    card_name_cn: Optional[str] = None  # 卡牌中文名
    interpretation: str  # 该位置的详细解读
    relationships: Optional[str] = None  # 与其他位置的关系


class InterpretationReference(BaseModel):
    """解读引用来源"""
    type: str  # 'card' 或 'method'
    card_name: Optional[str] = None  # 卡牌名称（如果type='card'）
    method: Optional[str] = None  # 占卜方法（如果type='method'）
    source: str  # 来源（如"PKT - The Pictorial Key to the Tarot"）


class FinalInterpretation(BaseModel):
    """最终解读模型"""
    overall_summary: str  # 整体解读摘要（2-3句话）
    position_interpretations: List[PositionInterpretation]  # 各位置的详细解读
    relationship_analysis: Optional[str] = None  # 关系分析
    pattern_explanation: Optional[str] = None  # 模式解释
    advice: Optional[str] = None  # 个性化建议
    references: List[InterpretationReference] = []  # 引用来源
    interpretation_metadata: Optional[Dict[str, Any]] = None  # 解读元数据

