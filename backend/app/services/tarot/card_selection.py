"""
塔罗牌选择服务 - 纯代码实现选牌逻辑
根据PKT传统方法，实现洗牌、切牌和选牌功能
"""

import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from app.core.database import get_supabase_service
from app.models.schemas import TarotCard


@dataclass
class SelectedCard:
    """选中的牌"""
    card_id: str
    card_name_en: str
    card_name_cn: Optional[str]
    suit: str
    card_number: int
    arcana: str
    position: str
    position_order: int
    position_description: Optional[str]
    is_reversed: bool
    image_url: Optional[str] = None  # 卡牌图像URL


class CardSelectionService:
    """塔罗牌选择服务 - 纯代码实现"""
    
    def __init__(self):
        self.supabase = get_supabase_service()
    
    async def get_deck_from_database(
        self,
        source: str = 'pkt'
    ) -> List[Dict[str, Any]]:
        """
        从数据库获取完整的78张牌
        
        Args:
            source: 数据源，'pkt' 或 '78degrees'
            
        Returns:
            完整的78张牌列表
        """
        response = self.supabase.table('tarot_cards').select('*').eq('source', source).execute()
        cards = response.data
        
        if len(cards) != 78:
            raise ValueError(f"Expected exactly 78 cards from source '{source}', but got {len(cards)}")
        
        return cards
    
    def remove_significator_from_deck(
        self,
        deck: List[Dict[str, Any]],
        significator: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        从牌堆中移除代表牌
        
        Args:
            deck: 完整78张牌堆
            significator: 代表牌对象（如果为None，则不移除）
            
        Returns:
            移除代表牌后的剩余牌堆（77张或78张）
        """
        if significator is None:
            return deck.copy()
        
        # 找到代表牌并移除
        significator_id = significator.get('id')
        remaining_deck = [card for card in deck if card.get('id') != significator_id]
        
        if len(remaining_deck) == len(deck):
            raise ValueError(f"Significator card not found in deck (id: {significator_id})")
        
        return remaining_deck
    
    def shuffle_deck(self, deck: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        洗牌 - 使用Fisher-Yates算法（通过random.shuffle实现）
        
        Args:
            deck: 待洗牌的牌堆
            
        Returns:
            洗好的牌堆（新的列表）
        """
        shuffled = deck.copy()
        random.shuffle(shuffled)
        return shuffled
    
    def generate_reversals(
        self,
        deck: List[Dict[str, Any]],
        reversal_rate: float = 0.45
    ) -> List[Dict[str, Any]]:
        """
        随机翻转部分牌生成逆位（约40-50%）
        
        Args:
            deck: 牌堆
            reversal_rate: 逆位比例（默认45%）
            
        Returns:
            带逆位标记的牌堆
        """
        result = []
        for card in deck:
            card_copy = card.copy()
            # 随机决定是否逆位
            is_reversed = random.random() < reversal_rate
            card_copy['is_reversed'] = is_reversed
            result.append(card_copy)
        
        return result
    
    def cut_deck_three_times(self, deck: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        传统切牌：三次切牌
        
        Args:
            deck: 牌堆
            
        Returns:
            切牌后的牌堆
        """
        cut_deck = deck.copy()
        
        for _ in range(3):
            # 随机选择切牌点（在1/4到3/4之间）
            deck_len = len(cut_deck)
            cut_point = random.randint(deck_len // 4, 3 * deck_len // 4)
            # 切牌：将下半部分移到上半部分
            cut_deck = cut_deck[cut_point:] + cut_deck[:cut_point]
        
        return cut_deck
    
    async def shuffle_and_cut_deck(
        self,
        deck: List[Dict[str, Any]],
        significator: Optional[Dict[str, Any]] = None,
        need_significator: bool = True
    ) -> List[Dict[str, Any]]:
        """
        洗牌和切牌
        
        根据PKT传统方法：
        1. 如果指定了代表牌且need_significator=True，从牌堆中**移除**（代表牌不参与洗牌）
        2. 如果need_significator=False（如三牌占卜），不移除代表牌，直接洗78张牌
        3. 对牌堆进行洗牌：Fisher-Yates算法
        4. 随机翻转部分牌（生成逆位，约40-50%）
        5. 切牌：模拟传统切牌（三次切牌）
        
        Args:
            deck: 完整78张牌堆
            significator: 代表牌对象（可选）
            need_significator: 是否需要代表牌（False时三牌占卜，True时凯尔特十字等）
            
        Returns:
            洗好的牌堆（78张或77张，取决于是否需要代表牌）
        """
        # 1. 如果需要代表牌，移除代表牌
        if need_significator and significator is not None:
            remaining_deck = self.remove_significator_from_deck(deck, significator)
        else:
            remaining_deck = deck.copy()
        
        # 2. 洗牌
        shuffled = self.shuffle_deck(remaining_deck)
        
        # 3. 生成逆位（约45%）
        with_reversals = self.generate_reversals(shuffled, reversal_rate=0.45)
        
        # 4. 切牌三次
        final_deck = self.cut_deck_three_times(with_reversals)
        
        return final_deck
    
    def get_spread_positions(self, spread_type: str) -> List[Dict[str, str]]:
        """
        获取占卜方式的位置定义
        
        Args:
            spread_type: 占卜方式，'three_card' 或 'celtic_cross'
            
        Returns:
            位置定义列表
        """
        # 三牌占卜位置定义
        if spread_type == 'three_card':
            return [
                {
                    'position': 'past',
                    'position_order': 1,
                    'position_description': '过去的影响'
                },
                {
                    'position': 'present',
                    'position_order': 2,
                    'position_description': '当前状况'
                },
                {
                    'position': 'future',
                    'position_order': 3,
                    'position_description': '未来趋势'
                }
            ]
        
        # 凯尔特十字位置定义
        elif spread_type == 'celtic_cross':
            return [
                {
                    'position': 'cover',
                    'position_order': 1,
                    'position_description': '覆盖Significator的牌，代表当前情况'
                },
                {
                    'position': 'crossing',
                    'position_order': 2,
                    'position_description': '横跨第一张牌的牌，代表阻碍或帮助'
                },
                {
                    'position': 'basis',
                    'position_order': 3,
                    'position_description': '位于Significator下方的牌，代表基础或根源'
                },
                {
                    'position': 'behind',
                    'position_order': 4,
                    'position_description': '代表过去的影响'
                },
                {
                    'position': 'crowned',
                    'position_order': 5,
                    'position_description': '代表可能的结果或目标'
                },
                {
                    'position': 'before',
                    'position_order': 6,
                    'position_description': '代表即将到来的未来'
                },
                {
                    'position': 'self',
                    'position_order': 7,
                    'position_description': '代表问卜者自身'
                },
                {
                    'position': 'environment',
                    'position_order': 8,
                    'position_description': '代表周围环境和他人影响'
                },
                {
                    'position': 'hopes_and_fears',
                    'position_order': 9,
                    'position_description': '代表问卜者的希望和恐惧'
                },
                {
                    'position': 'outcome',
                    'position_order': 10,
                    'position_description': '代表最终结果'
                }
            ]
        
        else:
            raise ValueError(f"Unsupported spread type: {spread_type}")
    
    async def select_cards_for_spread(
        self,
        spread_type: str,
        shuffled_deck: List[Dict[str, Any]],
        significator: Optional[Dict[str, Any]] = None
    ) -> List[SelectedCard]:
        """
        根据占卜方式从洗好的牌堆中**随机抽取**牌
        
        步骤：
        1. 获取占卜方式的位置定义
        2. 按照位置顺序**从牌堆顶部随机抽取**牌（完全随机）
        3. 记录每张牌的位置、顺序、是否逆位（洗牌时已确定）
        4. 生成SelectedCard对象列表
        
        重要：这是**完全随机**的抽取过程，从洗好的牌堆顶部按顺序抽取
        
        注意：
        - 三牌占卜：不需要代表牌，从完整的78张牌中抽取
        - 凯尔特十字：需要代表牌，从剩余的77张牌中抽取
        
        Args:
            spread_type: 占卜方式，'three_card' 或 'celtic_cross'
            shuffled_deck: 已洗好的牌堆（78张或77张，取决于是否需要代表牌）
            significator: 代表牌对象（可选，用于记录）
            
        Returns:
            SelectedCard列表（包含位置信息）
        """
        # 1. 获取位置定义
        positions = self.get_spread_positions(spread_type)
        
        # 2. 检查牌堆是否足够
        if len(shuffled_deck) < len(positions):
            raise ValueError(
                f"Not enough cards in deck: need {len(positions)}, "
                f"but only have {len(shuffled_deck)}"
            )
        
        # 3. 从牌堆顶部按位置顺序抽取牌
        selected_cards = []
        for i, position_info in enumerate(positions):
            # 从顶部抽取（完全随机，因为已经洗过牌）
            card = shuffled_deck[i]
            
            # 创建SelectedCard对象
            selected_card = SelectedCard(
                card_id=card.get('id'),
                card_name_en=card.get('card_name_en', ''),
                card_name_cn=card.get('card_name_cn'),
                suit=card.get('suit', ''),
                card_number=card.get('card_number', 0),
                arcana=card.get('arcana', ''),
                position=position_info['position'],
                position_order=position_info['position_order'],
                position_description=position_info.get('position_description'),
                is_reversed=card.get('is_reversed', False),
                image_url=card.get('image_url')  # 从数据库获取image_url
            )
            
            selected_cards.append(selected_card)
        
        return selected_cards

