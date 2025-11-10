#!/usr/bin/env python3
"""
从PKT文档提取所有78张塔罗牌信息
基于行号精确定位PKT原文，不使用LLM理解

提取内容：
- 22张大阿卡纳的完整描述、象征意义和占卜含义
- 56张小阿卡纳的完整描述和占卜含义

输出：
- JSON文件：rag/data/pkt_tarot_cards.json
- Supabase数据库：tarot_cards表

使用方法：
    python scripts/extract_pkt_cards.py

详细说明请参考：scripts/README_PKT_EXTRACTION.md
"""

import re
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import get_supabase_service
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PreciseCardExtractor:
    """精确提取所有塔罗牌信息，基于行号定位PKT原文"""
    
    def __init__(self, pkt_path: Path):
        self.pkt_path = pkt_path
        with open(pkt_path, 'r', encoding='utf-8') as f:
            self.pkt_content = f.read()
        self.lines = self.pkt_content.split('\n')
        logger.info(f"加载PKT文档: {len(self.lines)} 行")
    
    def extract_text_range(self, start_line: int, end_line: int) -> str:
        """提取指定行号范围内的文本
        start_line和end_line是文档行号（从1开始），需要转换为数组索引（从0开始）
        """
        # 转换为数组索引
        start_idx = max(0, start_line - 1)
        if start_idx >= len(self.lines):
            return ""
        
        # 扩展到end_line，但不超过文档长度
        end_idx = min(end_line, len(self.lines))
        text_lines = []
        
        for i in range(start_idx, end_idx):
            line = self.lines[i].strip()
            # 跳过空行、标题行、分隔符行
            if line and not line.startswith("The Pictorial Key") and "Click to enlarge" not in line:
                # 跳过纯数字或罗马数字行（卡片编号）
                if not re.match(r'^[0-9IVX]+$', line) and not line.startswith("XXI") and not line.startswith("ZERO"):
                    text_lines.append(line)
        
        return ' '.join(text_lines)
    
    def extract_major_arcana_card(self, card_name: str, card_number: int, 
                                  desc_start_line: int, desc_end_line: int,
                                  meaning_line: int) -> Dict[str, Any]:
        """提取大阿卡纳牌的信息"""
        # 1. 提取描述（PART II, section 2）
        # 在指定行号范围内查找卡片标题，然后提取完整描述
        description_text = ""
        symbolic_meaning = ""
        
        # 注意：desc_start_line是文档行号（从1开始），需要转换为数组索引（从0开始）
        desc_start_idx = max(0, desc_start_line - 1 - 5)
        desc_end_idx = min(desc_start_line - 1 + 10, len(self.lines))
        
        # 查找卡片标题（在desc_start_line附近）
        card_title_line = -1
        for i in range(desc_start_idx, desc_end_idx):
            line_upper = self.lines[i].upper()
            # 检查是否包含卡片名称
            if card_name.upper() in line_upper and "Click" not in line_upper:
                card_title_line = i
                break
        
        if card_title_line >= 0:
            # 从标题后开始提取内容
            content_start = card_title_line + 1
            
            # 跳过"Click to enlarge"行
            for i in range(content_start, min(content_start + 5, len(self.lines))):
                if "Click" in self.lines[i]:
                    content_start = i + 1
                    break
            
            # 查找内容结束位置（下一张牌的标题或文档结束）
            # 注意：desc_end_line是文档行号，需要转换为数组索引
            content_end = min(desc_end_line - 1 + 10, len(self.lines))
            
            # 检测下一张牌的起始位置（罗马数字编号）
            for i in range(content_start + 3, content_end):
                line = self.lines[i].strip()
                # 检查是否是下一张牌的编号（罗马数字）
                if re.match(r'^[IVX]+$', line) or line.startswith("XXI") or line.startswith("ZERO"):
                    # 确认这确实是下一张牌的编号（后面应该跟着卡片名称）
                    if i + 2 < len(self.lines):
                        next_line = self.lines[i + 2].strip()
                        # 如果下一行包含常见的卡片名称关键词，说明这是下一张牌
                        if any(keyword in next_line.upper() for keyword in ["MAGICIAN", "PRIESTESS", "EMPRESS", "EMPEROR", "HIEROPHANT", 
                                                                             "LOVERS", "CHARIOT", "STRENGTH", "HERMIT", "WHEEL", "JUSTICE",
                                                                             "HANGED", "DEATH", "TEMPERANCE", "DEVIL", "TOWER", "STAR",
                                                                             "MOON", "SUN", "JUDGMENT", "FOOL", "WORLD"]):
                            content_end = i
                            break
            
            paragraphs = []
            current_paragraph = []
            
            for i in range(content_start, content_end):
                line = self.lines[i].strip()
                
                # 遇到文档结束标记时停止
                if line.startswith("The Pictorial Key"):
                    break
                
                # 跳过空行、标题行、编号行
                if not line or "Click" in line or re.match(r'^[0-9IVX]+$', line):
                    if current_paragraph:
                        paragraphs.append(' '.join(current_paragraph))
                        current_paragraph = []
                    continue
                
                current_paragraph.append(line)
            
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
            
            # 分离视觉描述和象征意义
            # 第一段通常是视觉描述，后续段落是象征意义
            if paragraphs:
                # 第一段作为描述（完整的第一段，包括所有句子）
                description_text = paragraphs[0]
                
                # 后续段落作为象征意义
                if len(paragraphs) > 1:
                    symbolic_meaning = ' '.join(paragraphs[1:])
        
        # 如果没找到，使用行号范围直接提取
        if not description_text:
            full_text = self.extract_text_range(desc_start_line, desc_end_line)
            if full_text:
                # 尝试按段落分离
                parts = full_text.split('. ')
                if len(parts) > 5:
                    # 前一部分作为描述
                    mid_point = len(parts) // 2
                    description_text = '. '.join(parts[:mid_point]) + '.'
                    symbolic_meaning = '. '.join(parts[mid_point:])
                else:
                    description_text = full_text
        
        # 2. 提取占卜含义（PART III, section 3）
        upright_meaning = ""
        reversed_meaning = ""
        
        # 注意：meaning_line是文档行号（从1开始），需要转换为数组索引（从0开始）
        meaning_idx = meaning_line - 1
        if 0 <= meaning_idx < len(self.lines):
            # 读取占卜含义行
            meaning_text = self.lines[meaning_idx].strip()
            
            # 格式: "1. THE MAGICIAN.--Skill, diplomacy... Reversed: Physician..."
            # 或: "ZERO. THE FOOL.--Folly... Reversed: Negligence..."
            # 或: "10. WHEEL OF FORTUNE.-Destiny..." (单个破折号)
            # 分离卡片编号/名称和含义部分
            meaning_part = ""
            if '--' in meaning_text:
                parts = meaning_text.split('--', 1)
                if len(parts) > 1:
                    meaning_part = parts[1].strip()
            elif '.-' in meaning_text:  # 处理单个破折号的情况（如"10. WHEEL OF FORTUNE.-"）
                parts = meaning_text.split('.-', 1)
                if len(parts) > 1:
                    meaning_part = parts[1].strip()
            
            if meaning_part:
                # 分离正位和逆位
                if 'Reversed:' in meaning_part:
                    upright_part, reversed_part = meaning_part.split('Reversed:', 1)
                    upright_meaning = upright_part.strip().rstrip('.')
                    reversed_meaning = reversed_part.strip().rstrip('.')
                else:
                    upright_meaning = meaning_part.strip().rstrip('.')
        
        # 清理格式
        description_text = description_text.replace('\n', ' ').strip()
        symbolic_meaning = symbolic_meaning.replace('\n', ' ').strip()
        upright_meaning = upright_meaning.replace('\n', ' ').strip()
        reversed_meaning = reversed_meaning.replace('\n', ' ').strip()
        
        return {
            "card_name_en": card_name,
            "card_number": card_number,
            "suit": "major",
            "arcana": "major",
            "description": description_text,
            "symbolic_meaning": symbolic_meaning,
            "upright_meaning": upright_meaning,
            "reversed_meaning": reversed_meaning
        }
    
    def extract_minor_arcana_card(self, card_name: str, card_number: int, suit: str,
                                  desc_start_line: int, desc_end_line: int,
                                  additional_line: Optional[int] = None) -> Dict[str, Any]:
        """提取小阿卡纳牌的信息"""
        description_text = ""
        upright_meaning = ""
        reversed_meaning = ""
        
        # 在指定行号范围内查找卡片内容
        # 小阿卡纳格式：标题（如"King", "Queen", "Ten"） -> "Click to enlarge" -> 描述和占卜含义在同一段落
        
        # 提取卡片等级（King, Queen, Knight, Page, Ace, Two, ..., Ten）
        card_rank = card_name.split(" of ")[0].strip()
        
        # 注意：desc_start_line是文档行号（从1开始），需要转换为数组索引（从0开始）
        desc_start_idx = max(0, desc_start_line - 1 - 5)
        desc_end_idx = min(desc_end_line - 1 + 5, len(self.lines))
        
        # 查找卡片标题（只匹配等级名称，如"King", "Queen", "Ten"等）
        card_title_line = -1
        rank_keywords = ["KING", "QUEEN", "KNIGHT", "PAGE", "ACE", "TWO", "THREE", "FOUR", 
                         "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN"]
        
        for i in range(desc_start_idx, desc_end_idx):
            line_upper = self.lines[i].upper().strip()
            # 精确匹配等级名称（如"King", "Queen", "Ten"）
            # 标题行通常是独立的，只包含等级名称
            if line_upper == card_rank.upper():
                # 确认这是卡片标题（前后通常是空行或"WANDS"等花色标记）
                card_title_line = i
                break
        
        if card_title_line >= 0:
            # 从标题后查找"Click to enlarge"，然后提取内容
            content_start = card_title_line + 1
            
            # 跳过"Click to enlarge"行
            for i in range(content_start, min(content_start + 5, len(self.lines))):
                if "Click" in self.lines[i]:
                    content_start = i + 1
                    break
            
            # 提取内容段落（直到下一张牌或文档结束）
            content_lines = []
            found_content = False  # 标记是否已找到内容
            
            for i in range(content_start, min(content_start + 15, len(self.lines))):
                line = self.lines[i].strip()
                
                # 遇到文档结束标记时停止
                if line.startswith("The Pictorial Key"):
                    break
                
                # 如果已经有内容，检查是否是下一张牌的标题
                if found_content and line and len(line) < 30 and line[0].isupper() and i > content_start + 2:
                    line_upper_stripped = line.upper().strip()
                    # 检查是否是已知的等级名称（下一张牌的标题）
                    if any(rank == line_upper_stripped for rank in rank_keywords):
                        break
                
                # 收集非空内容行
                if line and len(line) > 10:  # 过滤空行和太短的行
                    content_lines.append(line)
                    found_content = True
            
            # 合并内容
            full_text = ' '.join(content_lines)
            
            # 分离描述和占卜含义
            # PKT格式：描述 + "Divinatory Meanings:" + 正位含义 + "Reversed:" + 逆位含义
            # 注意：有些牌使用"Divanatory Meanings:"（拼写变体）
            meaning_text = ""
            if "Divinatory Meanings:" in full_text:
                parts = full_text.split("Divinatory Meanings:", 1)
                description_text = parts[0].strip()
                meaning_text = parts[1].strip()
            elif "Divanatory Meanings:" in full_text:  # 处理拼写变体
                parts = full_text.split("Divanatory Meanings:", 1)
                description_text = parts[0].strip()
                meaning_text = parts[1].strip()
            else:
                # 如果没有"Divinatory Meanings:"标记，尝试其他格式
                # 可能格式：描述 + 占卜含义在同一段落，用句号分隔
                description_text = full_text
            
            if meaning_text:
                # 分离正位和逆位
                if "Reversed:" in meaning_text:
                    upright_part, reversed_part = meaning_text.split("Reversed:", 1)
                    upright_meaning = upright_part.strip().rstrip('.')
                    reversed_meaning = reversed_part.strip().rstrip('.')
                else:
                    upright_meaning = meaning_text.strip().rstrip('.')
        
        # 2. 提取额外占卜含义（PART III, section 4，如果有）
        additional_meanings = ""
        if additional_line:
            # 注意：additional_line是文档行号（从1开始），需要转换为数组索引（从0开始）
            additional_idx = additional_line - 1
            if 0 <= additional_idx < len(self.lines):
                # 查找该行附近的额外含义
                # 格式：WANDS. King.--Generally favourable... Reversed: ...
                suit_upper = suit.upper()
                rank_upper = card_rank.upper()
                
                for i in range(max(0, additional_idx - 3), min(additional_idx + 5, len(self.lines))):
                    line = self.lines[i].strip()
                    line_upper = line.upper()
                    
                    # 检查是否匹配格式：SUIT. RANK.--...
                    if suit_upper in line_upper and rank_upper in line_upper:
                        # 提取含义部分（通常在"--"之后）
                        if '--' in line:
                            parts = line.split('--', 1)
                            if len(parts) > 1:
                                additional_meanings = parts[1].strip()
                                break
                        elif len(line) > 50:
                            # 如果没有"--"，尝试提取整行（如果包含Reversed:）
                            additional_meanings = line
                            break
        
        # 清理格式
        description_text = description_text.replace('\n', ' ').strip()
        upright_meaning = upright_meaning.replace('\n', ' ').strip()
        reversed_meaning = reversed_meaning.replace('\n', ' ').strip()
        additional_meanings = additional_meanings.replace('\n', ' ').strip()
        
        return {
            "card_name_en": card_name,
            "card_number": card_number,
            "suit": suit.lower(),
            "arcana": "minor",
            "description": description_text,
            "upright_meaning": upright_meaning,
            "reversed_meaning": reversed_meaning,
            "additional_meanings": additional_meanings if additional_meanings else None
        }
    
    def extract_all_cards(self) -> List[Dict[str, Any]]:
        """提取所有78张牌"""
        all_cards = []
        
        # 大阿卡纳配置（根据tarot_card_info_complete_reference.md）
        major_cards_config = [
            ("The Magician", 1, 333, 343, 1604),
            ("The High Priestess", 2, 348, 359, 1606),
            ("The Empress", 3, 365, 376, 1608),
            ("The Emperor", 4, 382, 393, 1610),
            ("The Hierophant", 5, 399, 410, 1612),
            ("The Lovers", 6, 416, 427, 1614),
            ("The Chariot", 7, 433, 444, 1616),
            ("Strength", 8, 450, 461, 1618),
            ("The Hermit", 9, 467, 479, 1620),
            ("Wheel of Fortune", 10, 484, 495, 1622),
            ("Justice", 11, 501, 512, 1624),
            ("The Hanged Man", 12, 518, 529, 1626),
            ("Death", 13, 535, 546, 1628),
            ("Temperance", 14, 552, 563, 1630),
            ("The Devil", 15, 569, 580, 1632),
            ("The Tower", 16, 586, 597, 1634),
            ("The Star", 17, 603, 614, 1636),
            ("The Moon", 18, 620, 631, 1638),
            ("The Sun", 19, 637, 648, 1640),
            ("The Last Judgment", 20, 654, 665, 1642),
            ("The Fool", 0, 671, 687, 1644),
            ("The World", 21, 692, 703, 1646),
        ]
        
        logger.info("提取大阿卡纳（22张）...")
        for card_name, card_number, desc_start, desc_end, meaning_line in major_cards_config:
            try:
                card_data = self.extract_major_arcana_card(
                    card_name, card_number, desc_start, desc_end, meaning_line
                )
                all_cards.append(card_data)
                logger.info(f"  ✓ {card_name} (#{card_number}) - 描述: {len(card_data['description'])} 字符, 占卜含义: {'有' if card_data['upright_meaning'] else '无'}")
            except Exception as e:
                logger.error(f"  ✗ {card_name}: {e}")
        
        # 小阿卡纳配置（完整56张，根据tarot_card_info_complete_reference.md）
        minor_cards_config = [
            # Wands (权杖)
            ("King of Wands", 14, "wands", 764, 769, 1657),
            ("Queen of Wands", 13, "wands", 775, 784, 1659),
            ("Knight of Wands", 12, "wands", 790, 799, 1661),
            ("Page of Wands", 11, "wands", 805, 814, 1663),
            ("Ten of Wands", 10, "wands", 820, 829, None),
            ("Nine of Wands", 9, "wands", 835, 844, None),
            ("Eight of Wands", 8, "wands", 850, 859, None),
            ("Seven of Wands", 7, "wands", 865, 874, None),
            ("Six of Wands", 6, "wands", 880, 889, 1673),
            ("Five of Wands", 5, "wands", 895, 904, 1675),
            ("Four of Wands", 4, "wands", 910, 919, 1677),
            ("Three of Wands", 3, "wands", 925, 934, 1679),
            ("Two of Wands", 2, "wands", 940, 949, 1681),
            ("Ace of Wands", 1, "wands", 955, 964, 1683),
            # Cups (圣杯)
            ("King of Cups", 14, "cups", 970, 979, 1685),
            ("Queen of Cups", 13, "cups", 985, 994, 1687),
            ("Knight of Cups", 12, "cups", 1000, 1009, 1689),
            ("Page of Cups", 11, "cups", 1015, 1024, 1691),
            ("Ten of Cups", 10, "cups", 1030, 1039, 1693),
            ("Nine of Cups", 9, "cups", 1045, 1054, 1695),
            ("Eight of Cups", 8, "cups", 1060, 1069, 1697),
            ("Seven of Cups", 7, "cups", 1075, 1084, 1699),
            ("Six of Cups", 6, "cups", 1090, 1099, 1701),
            ("Five of Cups", 5, "cups", 1105, 1114, 1703),
            ("Four of Cups", 4, "cups", 1120, 1129, 1705),
            ("Three of Cups", 3, "cups", 1135, 1144, 1707),
            ("Two of Cups", 2, "cups", 1150, 1159, 1709),
            ("Ace of Cups", 1, "cups", 1165, 1174, 1711),
            # Swords (宝剑)
            ("King of Swords", 14, "swords", 1180, 1189, 1713),
            ("Queen of Swords", 13, "swords", 1195, 1204, 1715),
            ("Knight of Swords", 12, "swords", 1210, 1219, 1717),
            ("Page of Swords", 11, "swords", 1225, 1234, 1719),
            ("Ten of Swords", 10, "swords", 1240, 1249, 1721),
            ("Nine of Swords", 9, "swords", 1255, 1264, 1723),
            ("Eight of Swords", 8, "swords", 1270, 1279, 1725),
            ("Seven of Swords", 7, "swords", 1285, 1294, 1727),
            ("Six of Swords", 6, "swords", 1300, 1309, 1729),
            ("Five of Swords", 5, "swords", 1315, 1324, 1731),
            ("Four of Swords", 4, "swords", 1330, 1339, 1733),
            ("Three of Swords", 3, "swords", 1345, 1354, 1735),
            ("Two of Swords", 2, "swords", 1360, 1369, 1737),
            ("Ace of Swords", 1, "swords", 1375, 1384, 1739),
            # Pentacles (星币)
            ("King of Pentacles", 14, "pentacles", 1390, 1399, 1741),
            ("Queen of Pentacles", 13, "pentacles", 1405, 1414, 1743),
            ("Knight of Pentacles", 12, "pentacles", 1420, 1429, 1745),
            ("Page of Pentacles", 11, "pentacles", 1435, 1444, 1747),
            ("Ten of Pentacles", 10, "pentacles", 1450, 1459, 1749),
            ("Nine of Pentacles", 9, "pentacles", 1465, 1474, None),
            ("Eight of Pentacles", 8, "pentacles", 1480, 1489, 1753),
            ("Seven of Pentacles", 7, "pentacles", 1495, 1504, 1755),
            ("Six of Pentacles", 6, "pentacles", 1510, 1519, 1757),
            ("Five of Pentacles", 5, "pentacles", 1525, 1534, 1759),
            ("Four of Pentacles", 4, "pentacles", 1540, 1549, 1761),
            ("Three of Pentacles", 3, "pentacles", 1555, 1564, 1763),
            ("Two of Pentacles", 2, "pentacles", 1570, 1579, 1765),
            ("Ace of Pentacles", 1, "pentacles", 1585, 1594, 1767),
        ]
        
        logger.info("提取小阿卡纳（56张）...")
        
        for card_name, card_number, suit, desc_start, desc_end, additional_line in minor_cards_config:
            try:
                card_data = self.extract_minor_arcana_card(
                    card_name, card_number, suit, desc_start, desc_end, additional_line
                )
                all_cards.append(card_data)
                logger.info(f"  ✓ {card_name} ({suit}) - 描述: {len(card_data['description'])} 字符, 占卜含义: {'有' if card_data['upright_meaning'] else '无'}")
            except Exception as e:
                logger.error(f"  ✗ {card_name}: {e}")
        
        return all_cards
    
    def generate_chinese_names(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成中文名称（使用标准塔罗牌中文译名）"""
        # 标准中文名称映射
        chinese_names = {
            # 大阿卡纳
            "The Fool": "愚人",
            "The Magician": "魔术师",
            "The High Priestess": "女祭司",
            "The Empress": "女皇",
            "The Emperor": "皇帝",
            "The Hierophant": "教皇",
            "The Lovers": "恋人",
            "The Chariot": "战车",
            "Strength": "力量",
            "The Hermit": "隐者",
            "Wheel of Fortune": "命运之轮",
            "Justice": "正义",
            "The Hanged Man": "倒吊人",
            "Death": "死神",
            "Temperance": "节制",
            "The Devil": "恶魔",
            "The Tower": "塔",
            "The Star": "星星",
            "The Moon": "月亮",
            "The Sun": "太阳",
            "The Last Judgment": "审判",
            "The World": "世界",
            # 小阿卡纳 - 需要根据实际牌名添加
        }
        
        for card in cards:
            card_name_en = card["card_name_en"]
            if card_name_en in chinese_names:
                card["card_name_cn"] = chinese_names[card_name_en]
            else:
                # 对于小阿卡纳，使用通用翻译规则
                if " of " in card_name_en:
                    parts = card_name_en.split(" of ")
                    rank = parts[0]
                    suit = parts[1]
                    
                    rank_cn = {
                        "King": "国王", "Queen": "王后", "Knight": "骑士", "Page": "侍从",
                        "Ace": "王牌", "Two": "二", "Three": "三", "Four": "四", "Five": "五",
                        "Six": "六", "Seven": "七", "Eight": "八", "Nine": "九", "Ten": "十"
                    }
                    suit_cn = {
                        "Wands": "权杖", "Cups": "圣杯", "Swords": "宝剑", "Pentacles": "星币"
                    }
                    
                    card["card_name_cn"] = f"{rank_cn.get(rank, rank)} {suit_cn.get(suit, suit)}"
                else:
                    card["card_name_cn"] = card_name_en
        
        return cards


class DatabaseInserter:
    """数据库插入器"""
    
    def __init__(self):
        self.supabase = get_supabase_service()
    
    def insert_cards(self, cards: List[Dict[str, Any]]) -> int:
        """插入卡片到数据库"""
        logger.info(f"插入 {len(cards)} 张卡片到数据库...")
        
        card_data = []
        for card in cards:
            card_data.append({
                "card_name_en": card["card_name_en"],
                "card_name_cn": card.get("card_name_cn", ""),
                "card_number": card["card_number"],
                "suit": card["suit"],
                "arcana": card["arcana"],
                "description": card.get("description", ""),
                "upright_meaning": card.get("upright_meaning", ""),
                "reversed_meaning": card.get("reversed_meaning", ""),
                "symbolic_meaning": card.get("symbolic_meaning"),
                "additional_meanings": card.get("additional_meanings"),
                "image_url": card.get("image_url")
            })
        
        try:
            result = self.supabase.table("tarot_cards").upsert(
                card_data,
                on_conflict="card_name_en"
            ).execute()
            
            inserted_count = len(result.data) if result.data else 0
            logger.info(f"✅ 成功插入/更新 {inserted_count} 张卡片")
            return inserted_count
        except Exception as e:
            logger.error(f"❌ 插入失败: {e}")
            raise


def main():
    """主函数"""
    pkt_path = Path(__file__).parent.parent / "docs" / "pkt.txt"
    
    if not pkt_path.exists():
        logger.error(f"PKT文件不存在: {pkt_path}")
        return
    
    logger.info("=" * 60)
    logger.info("从PKT文档提取所有78张塔罗牌")
    logger.info("=" * 60)
    
    # 提取
    extractor = PreciseCardExtractor(pkt_path)
    all_cards = extractor.extract_all_cards()
    
    # 生成中文名称
    logger.info("生成中文名称...")
    all_cards = extractor.generate_chinese_names(all_cards)
    
    # 保存到JSON
    output_path = Path(__file__).parent.parent / "rag" / "data" / "pkt_tarot_cards.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_cards, f, indent=2, ensure_ascii=False)
    logger.info(f"保存提取数据到: {output_path}")
    
    # 插入数据库
    logger.info("插入数据库...")
    inserter = DatabaseInserter()
    inserted_count = inserter.insert_cards(all_cards)
    
    # 统计
    logger.info("=" * 60)
    logger.info("提取完成!")
    logger.info(f"总卡片数: {len(all_cards)}")
    logger.info(f"大阿卡纳: {len([c for c in all_cards if c['arcana'] == 'major'])}")
    logger.info(f"小阿卡纳: {len([c for c in all_cards if c['arcana'] == 'minor'])}")
    
    # 数据质量统计
    major_with_desc = len([c for c in all_cards if c['arcana'] == 'major' and c.get('description')])
    major_with_meaning = len([c for c in all_cards if c['arcana'] == 'major' and c.get('upright_meaning')])
    minor_with_desc = len([c for c in all_cards if c['arcana'] == 'minor' and c.get('description')])
    minor_with_meaning = len([c for c in all_cards if c['arcana'] == 'minor' and c.get('upright_meaning')])
    
    logger.info(f"大阿卡纳 - 有描述: {major_with_desc}/22, 有占卜含义: {major_with_meaning}/22")
    logger.info(f"小阿卡纳 - 有描述: {minor_with_desc}/56, 有占卜含义: {minor_with_meaning}/56")
    logger.info(f"数据库插入: {inserted_count} 张")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
