"""
代表牌选择服务 - 确定性选择代表牌（非随机）
根据PKT规则，根据用户信息和问题类型确定性选择代表牌
"""

from typing import Optional, Tuple, Dict, Any
from app.core.database import get_supabase_service


class SignificatorService:
    """代表牌选择服务 - 确定性选择，非随机"""
    
    def __init__(self):
        self.supabase = get_supabase_service()
    
    # 星座到元素的映射
    ZODIAC_TO_ELEMENT = {
        # 火象星座 → Wands
        'Aries': 'wands',      # 白羊座
        'Leo': 'wands',        # 狮子座
        'Sagittarius': 'wands',  # 射手座
        # 水象星座 → Cups
        'Cancer': 'cups',      # 巨蟹座
        'Scorpio': 'cups',     # 天蝎座
        'Pisces': 'cups',      # 双鱼座
        # 风象星座 → Swords
        'Gemini': 'swords',   # 双子座
        'Libra': 'swords',    # 天秤座
        'Aquarius': 'swords', # 水瓶座
        # 土象星座 → Pentacles
        'Taurus': 'pentacles', # 金牛座
        'Virgo': 'pentacles',  # 处女座
        'Capricorn': 'pentacles',  # 摩羯座
    }
    
    # 问题领域到花色的映射
    QUESTION_DOMAIN_TO_SUIT = {
        'love': 'cups',              # 爱情、关系、情感 → 圣杯（水元素）
        'career': 'wands',            # 事业、工作、职业 → 权杖（火元素）
        'health': 'pentacles',        # 健康、身体、康复 → 星币（土元素）
        'finance': 'pentacles',       # 财务、金钱、物质 → 星币（土元素）
        'personal_growth': 'swords',  # 个人成长、灵性、自我探索 → 宝剑（风元素）
        'general': 'wands',           # 一般生活、综合问题 → 权杖（火元素，默认）
    }
    
    def get_court_card_by_age_and_gender(
        self,
        age: int,
        gender: str
    ) -> str:
        """
        根据年龄和性别选择宫廷牌级别
        
        PKT规则：
        - 40岁以上男性 → Knight
        - 40岁以下男性 → King
        - 40岁以上女性 → Queen
        - 40岁以下女性 → Page
        
        Args:
            age: 年龄
            gender: 性别，'male'/'female'/'other'
            
        Returns:
            宫廷牌级别：'Page'/'Knight'/'Queen'/'King'
        """
        if gender == 'male':
            if age >= 40:
                return 'Knight'
            else:
                return 'King'
        elif gender == 'female':
            if age >= 40:
                return 'Queen'
            else:
                return 'Page'
        else:
            # 对于其他性别，默认使用中性选择（King）
            return 'King'
    
    def get_suit_by_element(
        self,
        zodiac_sign: Optional[str] = None,
        personality_type: Optional[str] = None,
        question_domain: Optional[str] = None,
        significator_priority: str = 'question_first'
    ) -> str:
        """
        根据问题领域、性格类型或星座选择花色
        
        优先级取决于significator_priority参数：
        - 'question_first'（默认）：问题领域 > 性格类型 > 星座
        - 'personality_first'：性格类型 > 问题领域 > 星座
        - 'zodiac_first'：星座 > 问题领域 > 性格类型
        
        元素对应：
        - 火象（白羊、狮子、射手）→ Wands
        - 水象（巨蟹、天蝎、双鱼）→ Cups
        - 风象（双子、天秤、水瓶）→ Swords
        - 土象（金牛、处女、摩羯）→ Pentacles
        
        问题领域对应：
        - love → Cups（水元素）
        - career → Wands（火元素）
        - health → Pentacles（土元素）
        - finance → Pentacles（土元素）
        - personal_growth → Swords（风元素）
        - general → Wands（火元素，默认）
        
        Args:
            zodiac_sign: 星座
            personality_type: 性格类型：'wands'/'cups'/'swords'/'pentacles'
            question_domain: 问题领域：'love'/'career'/'health'/'finance'/'personal_growth'/'general'
            significator_priority: 优先级选择：'question_first'（默认）、'personality_first' 或 'zodiac_first'
            
        Returns:
            花色：'wands'/'cups'/'swords'/'pentacles'
        """
        if significator_priority == 'personality_first':
            # 优先级1：性格类型
            if personality_type and personality_type in ['wands', 'cups', 'swords', 'pentacles']:
                return personality_type
            
            # 优先级2：问题领域
            if question_domain and question_domain in self.QUESTION_DOMAIN_TO_SUIT:
                return self.QUESTION_DOMAIN_TO_SUIT[question_domain]
            
            # 优先级3：根据星座转换为元素
            if zodiac_sign:
                zodiac_sign_normalized = zodiac_sign.capitalize()
                element = self.ZODIAC_TO_ELEMENT.get(zodiac_sign_normalized)
                if element:
                    return element
        elif significator_priority == 'zodiac_first':
            # 优先级1：根据星座转换为元素
            if zodiac_sign:
                zodiac_sign_normalized = zodiac_sign.capitalize()
                element = self.ZODIAC_TO_ELEMENT.get(zodiac_sign_normalized)
                if element:
                    return element
            
            # 优先级2：问题领域
            if question_domain and question_domain in self.QUESTION_DOMAIN_TO_SUIT:
                return self.QUESTION_DOMAIN_TO_SUIT[question_domain]
            
            # 优先级3：性格类型
            if personality_type and personality_type in ['wands', 'cups', 'swords', 'pentacles']:
                return personality_type
        else:
            # 默认优先级：question_first
            # 优先级1：问题领域
            if question_domain and question_domain in self.QUESTION_DOMAIN_TO_SUIT:
                return self.QUESTION_DOMAIN_TO_SUIT[question_domain]
            
            # 优先级2：性格类型
            if personality_type and personality_type in ['wands', 'cups', 'swords', 'pentacles']:
                return personality_type
            
            # 优先级3：根据星座转换为元素
            if zodiac_sign:
                zodiac_sign_normalized = zodiac_sign.capitalize()
                element = self.ZODIAC_TO_ELEMENT.get(zodiac_sign_normalized)
                if element:
                    return element
        
        # 默认返回Wands（火元素）
        return 'wands'
    
    def get_significator_card_name(
        self,
        court_level: str,
        suit: str
    ) -> str:
        """
        根据宫廷牌级别和花色确定代表牌名称
        
        Args:
            court_level: 宫廷牌级别：'Page'/'Knight'/'Queen'/'King'
            suit: 花色：'wands'/'cups'/'swords'/'pentacles'
            
        Returns:
            代表牌名称，如 "Queen of Cups"
        """
        # 转换suit为英文名称
        suit_names = {
            'wands': 'Wands',
            'cups': 'Cups',
            'swords': 'Swords',
            'pentacles': 'Pentacles'
        }
        
        suit_name = suit_names.get(suit.lower(), 'Wands')
        
        return f"{court_level} of {suit_name}"
    
    async def select_significator(
        self,
        age: Optional[int] = None,
        gender: Optional[str] = None,
        zodiac_sign: Optional[str] = None,
        personality_type: Optional[str] = None,
        question_domain: Optional[str] = None,
        question_text: Optional[str] = None,
        significator_priority: str = 'question_first',
        source: str = 'pkt'
    ) -> Tuple[Dict[str, Any], str]:
        """
        选择代表牌（确定性选择，非随机）
        
        根据PKT规则，确定性选择应该使用哪张牌：
        1. 根据年龄和性别（PKT规则）确定宫廷牌级别
        2. 根据优先级选择花色：
           - question_first（默认）：问题领域 > 性格类型 > 星座
           - personality_first：性格类型 > 问题领域 > 星座
           - zodiac_first：星座 > 问题领域 > 性格类型
        
        然后从完整牌堆中找到这张特定的牌（不是随机抽）
        
        Args:
            age: 年龄
            gender: 性别：'male'/'female'/'other'
            zodiac_sign: 星座
            personality_type: 性格类型：'wands'/'cups'/'swords'/'pentacles'
            question_domain: 问题领域：'love'/'career'/'health'/'finance'/'personal_growth'/'general'
            question_text: 问题文本（可选，暂未使用）
            significator_priority: 优先级选择：'question_first'（默认）、'personality_first' 或 'zodiac_first'
            source: 数据源，'pkt' 或 '78degrees'
            
        Returns:
            (代表牌对象, 选择原因)
        """
        # 1. 确定宫廷牌级别（根据年龄和性别）
        if age is None or gender is None:
            # 如果没有年龄和性别信息，默认使用King
            court_level = 'King'
            reason_part1 = "使用默认宫廷牌级别（King）"
        else:
            court_level = self.get_court_card_by_age_and_gender(age, gender)
            reason_part1 = f"根据年龄({age}岁)和性别({gender})选择{court_level}"
        
        # 2. 确定花色（根据优先级：问题领域、性格类型、星座）
        suit = self.get_suit_by_element(
            zodiac_sign=zodiac_sign,
            personality_type=personality_type,
            question_domain=question_domain,
            significator_priority=significator_priority
        )
        
        # 构建选择原因
        reason_parts = [reason_part1]
        if significator_priority == 'personality_first':
            if personality_type:
                reason_parts.append(f"性格类型({personality_type})决定花色（优先级1）")
            elif question_domain:
                reason_parts.append(f"问题领域({question_domain})决定花色（优先级2）")
            elif zodiac_sign:
                reason_parts.append(f"星座({zodiac_sign})对应元素决定花色（优先级3）")
        elif significator_priority == 'zodiac_first':
            if zodiac_sign:
                reason_parts.append(f"星座({zodiac_sign})对应元素决定花色（优先级1）")
            elif question_domain:
                reason_parts.append(f"问题领域({question_domain})决定花色（优先级2）")
            elif personality_type:
                reason_parts.append(f"性格类型({personality_type})决定花色（优先级3）")
        else:
            # question_first（默认）
            if question_domain:
                reason_parts.append(f"问题领域({question_domain})决定花色（优先级1）")
            elif personality_type:
                reason_parts.append(f"性格类型({personality_type})决定花色（优先级2）")
            elif zodiac_sign:
                reason_parts.append(f"星座({zodiac_sign})对应元素决定花色（优先级3）")
        
        # 3. 确定代表牌名称
        card_name = self.get_significator_card_name(court_level, suit)
        
        # 4. 从数据库中找到这张特定的牌
        response = self.supabase.table('tarot_cards').select('*').eq('source', source).eq('card_name_en', card_name).execute()
        
        if not response.data:
            # 如果找不到，尝试使用默认牌（King of Wands）
            card_name = "King of Wands"
            response = self.supabase.table('tarot_cards').select('*').eq('source', source).eq('card_name_en', card_name).execute()
            
            if not response.data:
                raise ValueError(f"Could not find significator card: {card_name} in source {source}")
            
            reason_parts.append(f"使用默认代表牌: {card_name}")
        
        significator_card = response.data[0]
        selection_reason = "；".join(reason_parts)
        
        return significator_card, selection_reason

