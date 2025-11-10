#!/usr/bin/env python3
"""
从78 Degrees of Wisdom文档提取所有78张塔罗牌信息

提取策略：
1. 先分析文档结构，定位每张牌的位置
2. 测试提取单张牌（The Fool）
3. 确认正确后批量提取所有78张牌

输出：
- JSON文件：database/data/78degrees_tarot_cards.json
- Supabase数据库：tarot_cards表（使用upsert更新，基于card_name_en）

使用方法：
    python scripts/extract_78degrees_cards.py
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


class SeventyEightDegreesExtractor:
    """从78 Degrees of Wisdom文档提取塔罗牌信息"""
    
    def __init__(self, doc_path: Path):
        self.doc_path = doc_path
        with open(doc_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
        self.lines = self.content.split('\n')
        logger.info(f"加载文档: {len(self.lines)} 行")
        
        # 缓存花色起始位置
        self.suit_positions = {}
        self._find_suit_positions()
    
    def _find_suit_positions(self):
        """查找并缓存所有花色的起始位置"""
        suits = ["WANDS", "CUPS", "SWORDS", "PENTACLES"]
        for suit in suits:
            for i, line in enumerate(self.lines):
                if line.strip() == suit:
                    # 确认这是独立行标题
                    if i > 0 and (not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")):
                        self.suit_positions[suit] = i
                        logger.debug(f"找到花色 {suit} 在行 {i+1}")
                        break
    
    def find_card_section(self, card_name: str, start_line: int = 0) -> Optional[Tuple[int, int]]:
        """查找卡牌章节的起始和结束行号
        
        Returns:
            (start_line, end_line) 或 None
        """
        # 生成匹配模式，优先使用完整牌名（包括"The"）
        card_name_patterns = []
        
        # 首先尝试添加带"The"的版本（如果原名称没有"The"）
        if not card_name.startswith("The "):
            card_name_with_the = "The " + card_name
            card_name_patterns.extend([
                card_name_with_the,
                card_name_with_the.upper(),
                card_name_with_the.lower(),
                card_name_with_the.title(),
            ])
        
        # 然后添加原始名称
        card_name_patterns.extend([
            card_name,
            card_name.upper(),
            card_name.lower(),
            card_name.title(),
        ])
        
        # 如果牌名包含"The"，也添加不带"The"的版本
        if card_name.startswith("The "):
            name_without_the = card_name[4:].strip()
            card_name_patterns.extend([
                name_without_the,
                name_without_the.upper(),
                name_without_the.lower(),
                name_without_the.title(),
            ])
        
        start_idx = -1
        end_idx = len(self.lines)
        
        # 查找章节标题（通常是独立行）
        # 优先查找作为独立行标题的卡牌名称
        for i in range(start_line, len(self.lines)):
            line = self.lines[i].strip()
            
            # 检查是否是卡牌标题（独立行，前后有空行或章节标记）
            for pattern in card_name_patterns:
                if line == pattern:  # 精确匹配独立行
                    # 确认前后环境
                    prev_empty = i == 0 or not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")
                    next_empty = i == len(self.lines) - 1 or not self.lines[i+1].strip() or self.lines[i+1].strip().startswith("Figure")
                    has_chapter_marker = i > 0 and ("Chapter" in self.lines[i-1] or "THE " in self.lines[i-1].upper())
                    
                    if prev_empty or next_empty or has_chapter_marker:
                        start_idx = i
                        logger.debug(f"找到卡牌标题 '{pattern}' 在行 {i+1}")
                        break
            
            if start_idx >= 0:
                break
        
        # 如果没找到独立行标题，尝试包含空格的标题
        # 但要确保这是真正的章节标题，而不是文本中的提及
        if start_idx < 0:
            for i in range(start_line, len(self.lines)):
                line = self.lines[i].strip()
                
                for pattern in card_name_patterns:
                    # 检查是否是章节标题（精确匹配，前后有空行或章节标记）
                    if line == pattern or (line.startswith(pattern) and len(line) == len(pattern) + 1 and line[len(pattern)] in [' ', '\n']):
                        # 确认前后环境（前后有空行、章节标记或Figure标记）
                        prev_empty = i == 0 or not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure") or "THE " in self.lines[i-1].upper()
                        next_empty = i == len(self.lines) - 1 or not self.lines[i+1].strip() or self.lines[i+1].strip().startswith("Figure")
                        has_chapter_marker = i > 0 and ("Chapter" in self.lines[i-1] or "THE " in self.lines[i-1].upper())
                        
                        # 确保不是文本中的提及（如果后面有大量文本，可能是章节标题）
                        # 如果下一行是空行或Figure标记，更可能是章节标题
                        if prev_empty or next_empty or has_chapter_marker:
                            start_idx = i
                            logger.debug(f"找到卡牌标题 '{pattern}' 在行 {i+1} (带空格)")
                            break
                
                if start_idx >= 0:
                    break
        
        if start_idx < 0:
            logger.warning(f"未找到卡牌章节: {card_name}")
            return None
        
        # 查找章节结束位置（下一张牌的标题）
        # 注意：需要确保包含逆位含义部分（通常在章节末尾）
        major_arcana_names = [
            "The Fool", "The Magician", "The High Priestess", "The Empress",
            "The Emperor", "The Hierophant", "The Lovers", "The Chariot",
            "Strength", "The Hermit", "Wheel of Fortune", "Justice",
            "The Hanged Man", "Death", "Temperance", "The Devil",
            "The Tower", "The Star", "The Moon", "The Sun",
            "The Last Judgment", "Judgement", "The World"
        ]
        
        minor_arcana_keywords = [
            "KING", "QUEEN", "KNIGHT", "PAGE", "ACE", "TWO", "THREE", "FOUR",
            "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN"
        ]
        
        # 扩大搜索范围，确保包含逆位含义部分（通常在章节末尾）
        # 但不要太大，避免包含过多下一章节内容
        # 大阿卡纳章节通常不超过250行
        search_end = min(start_idx + 250, len(self.lines))
        
        for i in range(start_idx + 10, search_end):
            line = self.lines[i].strip()
            line_upper = line.upper()
            
            # 检查是否是下一张牌的标题（独立行，前后有空行）
            if any(name.upper() == line_upper for name in major_arcana_names if name != card_name):
                # 确认这是独立行标题（前后有空行或章节标记）
                if i > 0 and (not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("THE ")):
                    # 检查后面是否确认这是下一张牌
                    if i + 2 < len(self.lines):
                        next_line = self.lines[i+1].strip()
                        if not next_line or next_line.startswith("Figure"):
                            end_idx = i
                            logger.debug(f"找到下一张牌 '{line}' 在行 {i+1}，结束位置: {end_idx}")
                            break
            
            # 检查是否是下一章节（Chapter）- 但要确保不是当前章节内的引用
            if line.startswith("Chapter") and i > start_idx + 100:
                end_idx = i
                break
            
            # 检查是否是下一张小阿卡纳牌
            if any(keyword == line_upper for keyword in minor_arcana_keywords):
                if i > start_idx + 100:
                    end_idx = i
                    break
        
        logger.debug(f"章节边界: {start_idx} -> {end_idx} (共{end_idx - start_idx}行)")
        
        return (start_idx, end_idx)
    
    def extract_text_section(self, start_line: int, end_line: int) -> str:
        """提取指定行号范围内的文本"""
        text_lines = []
        
        # 小阿卡纳的rank标题（如"KING", "EIGHT"等）需要跳过
        minor_ranks = ["KING", "QUEEN", "KNIGHT", "PAGE", "ACE", "TWO", "THREE", "FOUR",
                      "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN"]
        
        for i in range(start_line, end_line):
            line = self.lines[i].strip()
            
            # 跳过空行、页码、章节标题
            if not line:
                continue
            
            # 跳过页码行（纯数字）
            if re.match(r'^\d+$', line):
                continue
            
            # 跳过小阿卡纳的rank标题（独立行，前后有空行）
            # 但只在章节开始位置跳过，避免跳过内容中的提及
            if line.upper() in minor_ranks and i == start_line:
                # 检查是否是独立行标题（在章节开始位置）
                prev_empty = i == 0 or not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")
                next_empty = i == len(self.lines) - 1 or not self.lines[i+1].strip() or self.lines[i+1].strip().startswith("Figure")
                if prev_empty or next_empty:
                    continue  # 跳过章节开始的rank标题行
            
            # 跳过章节标题（如果它们出现在内容中间）
            # 但不要跳过"THE OPENING TRUMPS"这样的章节标记（它们可能出现在内容中）
            if line.startswith("Chapter"):
                if i > start_line + 10:  # 允许开头的章节标题
                    continue
            
            text_lines.append(line)
        
        return ' '.join(text_lines)
    
    def extract_major_arcana_card(self, card_name: str, card_number: int) -> Dict[str, Any]:
        """提取大阿卡纳牌的信息"""
        logger.info(f"提取大阿卡纳: {card_name} (#{card_number})")
        
        # 查找章节位置
        section = self.find_card_section(card_name)
        if not section:
            return self._create_empty_card(card_name, card_number, "major")
        
        start_line, end_line = section
        
        # 提取文本内容
        full_text = self.extract_text_section(start_line, end_line)
        
        # 调试：检查是否包含逆位文本
        if "reversal" in full_text.lower() or "reversed" in full_text.lower():
            logger.debug(f"找到逆位相关内容（长度: {len(full_text)}）")
        else:
            logger.warning(f"提取的文本中未找到逆位相关内容（文本长度: {len(full_text)}）")
            logger.debug(f"文本末尾200字符: {full_text[-200:]}")
        
        # 分离描述、象征意义和占卜含义
        # 78 Degrees格式：描述 -> 象征意义 -> 占卜含义（正位/逆位）
        
        description = ""
        symbolic_meaning = ""
        upright_meaning = ""
        reversed_meaning = ""
        
        # 查找逆位含义标记
        # 格式："For the Fool a reversal means" 或 "reversed" 出现在句子中
        # 先查找包含"reversal"的句子（这是最可靠的标记）
        reversed_start = -1
        
        # 模式1: "For the [Card] a reversal means" - 最常用的格式
        # 使用更灵活的模式来匹配卡片名称
        reversal_match = re.search(r'For the [A-Za-z\s]+ a reversal means', full_text, re.IGNORECASE)
        if reversal_match:
            reversed_start = reversal_match.start()
            logger.debug(f"找到逆位标记（模式1）: {reversal_match.group()}")
        
        # 模式1b: 如果没有匹配到，尝试更宽松的模式
        if reversed_start < 0:
            reversal_match = re.search(r'For the\s+\w+\s+a reversal means', full_text, re.IGNORECASE)
            if reversal_match:
                reversed_start = reversal_match.start()
                logger.debug(f"找到逆位标记（模式1b）: {reversal_match.group()}")
        
        # 模式2: "Reversed," 出现在句子开头（常见格式：Reversed, the card signifies）
        if reversed_start < 0:
            reversed_match = re.search(r'\bReversed[,\.]?\s+(the\s+)?(card|trump|we)', full_text, re.IGNORECASE)
            if reversed_match:
                reversed_start = reversed_match.start()
                logger.debug(f"找到逆位标记（模式2）: {reversed_match.group()}")
        
        # 模式2b: "The trump reversed indicates" 或 "The card reversed"
        if reversed_start < 0:
            trump_match = re.search(r'\b(The\s+)?(trump|card)\s+reversed\s+indicates', full_text, re.IGNORECASE)
            if trump_match:
                reversed_start = trump_match.start()
                logger.debug(f"找到逆位标记（模式2b）: {trump_match.group()}")
        
        # 模式2c: "Reversed, we" 格式（如The Star）
        if reversed_start < 0:
            reversed_we_match = re.search(r'\bReversed[,\.]?\s+we\s+', full_text, re.IGNORECASE)
            if reversed_we_match:
                reversed_start = reversed_we_match.start()
                logger.debug(f"找到逆位标记（模式2c）: {reversed_we_match.group()}")
        
        # 模式3: "The [Card] reversed" 或 "[Card] reversed"
        if reversed_start < 0:
            card_name_short = card_name.replace("The ", "").strip()
            pattern = rf'{re.escape(card_name_short)}\s+reversed|{re.escape(card_name)}\s+reversed'
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                reversed_start = match.start()
                logger.debug(f"找到逆位标记（模式3）: {match.group()}")
        
        # 模式4: "Like ... reversed" 格式（如The Emperor, Temperance）
        # 简化：直接查找"The trump reversed"或"The card reversed"或"The reversed"
        if reversed_start < 0:
            like_reversed_match = re.search(r'(?:The\s+)?(?:trump|card|reversed)\s+(?:reversed\s+)?(?:can\s+)?(?:act\s+as\s+a\s+warning|indicates|signifies|means)', full_text, re.IGNORECASE)
            if like_reversed_match:
                reversed_start = like_reversed_match.start()
                logger.debug(f"找到逆位标记（模式4）: {like_reversed_match.group()[:50]}...")
        
        # 模式5: 查找包含"reversal"的段落
        if reversed_start < 0:
            reversal_match = re.search(r'[Rr]eversal.*?means', full_text, re.DOTALL)
            if reversal_match:
                reversed_start = reversal_match.start()
                logger.debug(f"找到逆位标记（模式5）: {reversal_match.group()[:50]}")
        
        # 模式6: "The reversed meanings of the cards also have" - The Empress的特殊格式
        if reversed_start < 0:
            reversed_meanings_match = re.search(r'The reversed meanings of the cards also have', full_text, re.IGNORECASE)
            if reversed_meanings_match:
                reversed_start = reversed_meanings_match.start()
                logger.debug(f"找到逆位标记（模式6）: The reversed meanings of the cards also have")
        
        # 模式7: "[Card] reversed can mean" - The Empress的特殊格式
        if reversed_start < 0:
            card_name_short = card_name.replace("The ", "").strip()
            pattern = rf'{re.escape(card_name_short)}\s+reversed\s+can\s+mean|{re.escape(card_name)}\s+reversed\s+can\s+mean'
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                reversed_start = match.start()
                logger.debug(f"找到逆位标记（模式7）: {match.group()}")
        
        # 模式8: "if the card appears reversed" - The Moon的特殊格式
        if reversed_start < 0:
            appears_reversed_match = re.search(r'if the card appears reversed', full_text, re.IGNORECASE)
            if appears_reversed_match:
                # 检查这个模式后面是否有逆位含义内容
                # 查找"The Moon reversed"或"Again, the Moon reversed"
                after_match = re.search(r'Again,?\s+the\s+\w+\s+reversed\s+signifies', full_text[appears_reversed_match.end():], re.IGNORECASE)
                if after_match:
                    reversed_start = appears_reversed_match.start() + appears_reversed_match.end() + after_match.start()
                    logger.debug(f"找到逆位标记（模式8）: if the card appears reversed + Again")
                else:
                    # 如果没有找到"Again"，检查是否有逆位含义内容（"it shows a struggle"等）
                    after_text = full_text[appears_reversed_match.end():appears_reversed_match.end()+200]
                    if "struggle" in after_text.lower() or "fear" in after_text.lower():
                        reversed_start = appears_reversed_match.start()
                        logger.debug(f"找到逆位标记（模式8b）: if the card appears reversed (直接)")
        
        # 模式10: "Reversed, the card" - The Chariot, Justice等的格式
        if reversed_start < 0:
            reversed_card_match = re.search(r'Reversed,?\s+the\s+card', full_text, re.IGNORECASE)
            if reversed_card_match:
                reversed_start = reversed_card_match.start()
                logger.debug(f"找到逆位标记（模式10）: Reversed, the card")
        
        # 模式11: "[Card] reversed, on the other hand" - The Devil的特殊格式
        if reversed_start < 0:
            card_name_short = card_name.replace("The ", "").strip()
            pattern = rf'{re.escape(card_name_short)}\s+reversed,?\s+on\s+the\s+other\s+hand|{re.escape(card_name)}\s+reversed,?\s+on\s+the\s+other\s+hand'
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                reversed_start = match.start()
                logger.debug(f"找到逆位标记（模式11）: {match.group()}")
        
        # 模式9: "Reversed, the trump indicates" - The World的特殊格式
        if reversed_start < 0:
            reversed_trump_match = re.search(r'Reversed,?\s+the\s+trump\s+indicates', full_text, re.IGNORECASE)
            if reversed_trump_match:
                reversed_start = reversed_trump_match.start()
                logger.debug(f"找到逆位标记（模式9）: Reversed, the trump indicates")
        
        if reversed_start < 0:
            logger.warning(f"未找到逆位含义标记，卡片: {card_name}")
        
        # 如果没有找到明确的逆位标记，查找"In readings"之后的文本
        readings_match = re.search(r'In readings.*?(?=For the|reversed|$)', full_text, re.IGNORECASE | re.DOTALL)
        
        if reversed_start >= 0:
            # 分离逆位含义 - 提取从逆位标记开始到章节结束的所有内容
            # 需要找到逆位含义的真正结束位置（下一章节标记或段落结束）
            reversed_text = full_text[reversed_start:]
            
            # 查找逆位含义的结束位置：下一章节标记或下一张卡牌标题
            reversed_end = len(reversed_text)
            
            # 查找下一章节标记（但需要确保不是当前章节内的引用）
            next_chapter_markers = ['THE OPENING TRUMPS', 'THE WORLDLY SEQUENCE', 
                                   'TURNING INWARDS', 'THE GREAT JOURNEY', 'THE MAGICIAN']
            
            # 也查找下一张卡牌标题（Major Arcana）
            major_arcana_names = [
                "The Fool", "The Magician", "The High Priestess", "The Empress",
                "The Emperor", "The Hierophant", "The Lovers", "The Chariot",
                "Strength", "The Hermit", "Wheel of Fortune", "Justice",
                "The Hanged Man", "Death", "Temperance", "The Devil",
                "The Tower", "The Star", "The Moon", "The Sun",
                "The Last Judgment", "Judgement", "The World"
            ]
            
            # 在逆位文本中查找结束标记
            for marker in next_chapter_markers:
                marker_pos = reversed_text.find(marker)
                if marker_pos > 0 and marker_pos < reversed_end:
                    # 检查是否是独立行标题（前后有空行或章节标记）
                    # 对于The Moon和The World，限制更严格（前2000字符内）
                    max_pos = 2000 if card_name in ["The Moon", "The World"] else 500
                    if marker_pos < max_pos:
                        reversed_end = marker_pos
                        break
            
            # 特殊处理：对于The Moon和The World，需要更严格地限制逆位含义长度
            # 但不要过度截断，应该保留完整的逆位含义内容
            
            # 截取逆位含义部分（到结束位置）
            reversed_meaning = reversed_text[:reversed_end].strip()
            
            # 对于The Moon，特别处理：查找"the gateways open to adventure"作为结束标记
            if card_name == "The Moon":
                # 首先查找"Again, the Moon reversed signifies"作为开始位置
                again_start = reversed_meaning.find("Again, the Moon reversed signifies")
                if again_start > 0:
                    # 如果找到了，从"Again"开始
                    reversed_meaning = reversed_meaning[again_start:].strip()
                    logger.debug(f"The Moon: 从Again开始提取逆位含义")
                
                # 查找"the gateways open to adventure"作为结束标记
                adventure_end = reversed_meaning.lower().find("the gateways open to adventure")
                if adventure_end > 0:
                    # 找到这个标记后的句号位置
                    period_after = reversed_meaning.find('.', adventure_end)
                    if period_after > 0:
                        reversed_meaning = reversed_meaning[:period_after + 1].strip()
                        logger.debug(f"The Moon逆位含义截断到: {len(reversed_meaning)} 字符")
                
                # 查找"THE GREAT JOURNEY"标记并截断（如果之前没有找到adventure）
                if adventure_end <= 0:
                    journey_end = reversed_meaning.upper().find("THE GREAT JOURNEY")
                    if journey_end > 0:
                        # 在标记前查找最后一个句号
                        last_period = reversed_meaning.rfind('.', 0, journey_end)
                        if last_period > 0:
                            reversed_meaning = reversed_meaning[:last_period + 1].strip()
                            logger.debug(f"The Moon逆位含义截断到标记前的句号: {len(reversed_meaning)} 字符")
                
                # 如果仍然太长（>5000字符），强制截断到前2000字符内的最后一个句号
                if len(reversed_meaning) > 5000:
                    # 查找前2000字符内的最后一个句号
                    last_period = reversed_meaning.rfind('.', 0, 2000)
                    if last_period > 0:
                        reversed_meaning = reversed_meaning[:last_period + 1].strip()
                        logger.debug(f"The Moon逆位含义强制截断到: {len(reversed_meaning)} 字符")
            
            # 对于The World，特别处理：查找"the dance of life"作为结束标记
            if card_name == "The World":
                dance_end = reversed_meaning.lower().find("the dance of life")
                if dance_end > 0:
                    # 找到这个标记后的句号位置
                    period_after = reversed_meaning.find('.', dance_end)
                    if period_after > 0:
                        reversed_meaning = reversed_meaning[:period_after + 1].strip()
                        logger.debug(f"The World逆位含义截断到: {len(reversed_meaning)} 字符")
                # 查找"Bibliography"或"These are the meanings"标记并截断
                bibliography_end = reversed_meaning.find("Bibliography")
                if bibliography_end > 0:
                    # 在标记前查找最后一个句号
                    last_period = reversed_meaning.rfind('.', 0, bibliography_end)
                    if last_period > 0:
                        reversed_meaning = reversed_meaning[:last_period + 1].strip()
                        logger.debug(f"The World逆位含义截断到标记前的句号: {len(reversed_meaning)} 字符")
                else:
                    # 查找"These are the meanings of the World in divination"
                    meanings_end = reversed_meaning.find("These are the meanings of the World")
                    if meanings_end > 0:
                        last_period = reversed_meaning.rfind('.', 0, meanings_end)
                        if last_period > 0:
                            reversed_meaning = reversed_meaning[:last_period + 1].strip()
                            logger.debug(f"The World逆位含义截断到标记前的句号: {len(reversed_meaning)} 字符")
            
            # 特殊处理：对于某些卡牌（如The Hanged Man），逆位含义可能跨越章节标记
            # 检查在原始文本中，章节标记之后是否还有逆位含义内容
            # 这需要在行级别进行搜索，因为extract_text_section会跳过空行
            # 直接在原始行中查找"The card reversed also means"这样的模式
            additional_reversed_patterns = [
                r'^The\s+card\s+reversed\s+also\s+means',
                r'^The\s+trump\s+reversed\s+also\s+means',
                r'^The\s+card\s+reversed\s+also',
            ]
            
            # 在原始行中查找额外的逆位含义段落
            # 从逆位标记开始的行之后查找（逆位标记通常在章节的后半部分）
            # 从章节中间位置开始查找，确保能找到跨章节的逆位含义
            search_start_line = max(start_line + 50, start_line + (end_line - start_line) // 2)
            
            # 在章节的剩余部分中查找
            for i in range(search_start_line, end_line):
                line = self.lines[i].strip()
                if not line:
                    continue
                
                # 检查是否匹配额外的逆位含义模式
                for pattern in additional_reversed_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        # 找到额外的逆位含义段落
                        # 提取从这个位置到章节结束的所有内容
                        additional_lines = []
                        for j in range(i, end_line):
                            additional_line = self.lines[j].strip()
                            if not additional_line:
                                continue
                            # 如果遇到下一章节或下一张卡牌标题，停止
                            if any(marker in additional_line.upper() for marker in next_chapter_markers):
                                break
                            if any(name.upper() == additional_line.upper() for name in major_arcana_names if name != card_name):
                                # 检查是否是独立行标题
                                if j > 0 and (not self.lines[j-1].strip() or self.lines[j-1].strip().startswith("THE ")):
                                    break
                            additional_lines.append(additional_line)
                        
                        if additional_lines:
                            additional_text = ' '.join(additional_lines)
                            # 移除标记文本
                            additional_text = re.sub(r'^(?:The\s+)?(?:trump|card)\s+reversed\s+also\s+means\s+', '', additional_text, flags=re.IGNORECASE).strip()
                            
                            if additional_text and len(additional_text) > 20:  # 确保有足够的内容
                                # 合并到逆位含义中
                                reversed_meaning = reversed_meaning + ' ' + additional_text
                                logger.debug(f"找到额外的逆位含义段落（行 {i+1}-{i+len(additional_lines)}，长度: {len(additional_text)}）")
                        break
                
                # 如果找到了，不再继续搜索
                if reversed_meaning != reversed_text[:reversed_end].strip():
                    break
            
            # 只移除开头的标记文本，不删除内容中的"reversed"
            # 检查开头是否包含标记模式
            opening_patterns = [
                r'^For the [A-Za-z\s]+ a reversal means\s+',
                r'^For the\s+\w+\s+a reversal means\s+',
                r'^Reversed[,\.]?\s+(the\s+)?(card|trump)\s+signifies\s+',
                r'^Reversed[,\.]?\s+(the\s+)?(card|trump)\s+indicates\s+',
                r'^Reversed[,\.]?\s+we\s+',
                r'^(The\s+)?(trump|card)\s+reversed\s+indicates\s+',
                r'^Like\s+.*?\s+reversed.*?(?:,|\.)?\s+(?:the\s+)?(?:card|trump|emperor|temperance).*?(?:when\s+upside\s+down|The\s+reversed).*?(?:indicates|can\s+signify|means)\s+',
                r'^The reversed meanings of the cards also have\s+',
                r'^Again,?\s+the\s+\w+\s+reversed\s+signifies\s+',
                r'^if the card appears reversed,?\s+it shows\s+',
            ]
            for pattern in opening_patterns:
                reversed_meaning = re.sub(pattern, '', reversed_meaning, flags=re.IGNORECASE | re.DOTALL)
            
            # 清理：移除明显属于下一章节的文本（在结尾处）
            # 但保留所有逆位含义内容，包括多段落的情况
            # 查找段落结束标记（如空行后的章节标题）
            lines = reversed_meaning.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 如果遇到明显的章节标记，停止
                if any(marker in line.upper() for marker in ['THE OPENING TRUMPS', 'THE WORLDLY SEQUENCE', 
                                                            'TURNING INWARDS', 'THE GREAT JOURNEY', 'CHAPTER']):
                    break
                cleaned_lines.append(line)
            
            reversed_meaning = ' '.join(cleaned_lines).strip()
            
            # 清理多余的空白字符，但保留段落结构
            reversed_meaning = re.sub(r'\s+', ' ', reversed_meaning)
            
            # 主文本（逆位之前的部分）
            main_text = full_text[:reversed_start]
        else:
            main_text = full_text
        
        # 从主文本中分离描述、象征意义和正位含义
        # 查找"In readings"或"In divinatory readings"标记
        readings_idx = -1
        readings_patterns = [
            r'\bIn\s+divinatory\s+readings\b',
            r'\bIn\s+readings\b',
        ]
        for pattern in readings_patterns:
            match = re.search(pattern, main_text, re.IGNORECASE)
            if match:
                readings_idx = match.start()
                logger.debug(f"找到占卜含义标记: {pattern}")
                break
        
        if readings_idx >= 0:
            # 描述和象征意义在"In readings"之前
            desc_symbol_text = main_text[:readings_idx]
            
            # 正位含义在"In readings"之后，直到逆位含义开始（如果有）
            if reversed_start >= 0 and reversed_start < len(main_text):
                # 正位含义应该在逆位含义之前
                upright_text = main_text[readings_idx:reversed_start]
            else:
                upright_text = main_text[readings_idx:]
            
            # 特殊处理：对于The Empress，逆位含义在正位含义文本中间
            # 需要从正位含义中分离出逆位含义（无论是否找到reversed_start）
            if card_name == "The Empress":
                # 查找"The reversed meanings of the cards also have"标记
                reversed_in_upright = upright_text.find("The reversed meanings of the cards also have")
                if reversed_in_upright > 0:
                    # 分离正位含义和逆位含义
                    actual_upright = upright_text[:reversed_in_upright].strip()
                    # 提取逆位含义部分（从标记开始到章节结束）
                    reversed_in_text = upright_text[reversed_in_upright:]
                    # 查找逆位含义的结束位置（下一段落或章节标记）
                    reversed_end_markers = [
                        "In their right side up and reversed meanings",
                        "THE WORLDLY SEQUENCE"
                    ]
                    for marker in reversed_end_markers:
                        marker_pos = reversed_in_text.find(marker)
                        if marker_pos > 0:
                            reversed_in_text = reversed_in_text[:marker_pos].strip()
                            break
                    
                    # 移除开头的标记文本
                    reversed_in_text = re.sub(r'^The reversed meanings of the cards also have their positive and negative contexts\.\s+', '', reversed_in_text, flags=re.IGNORECASE).strip()
                    
                    # 更新逆位含义（如果之前没有找到或为空）
                    if not reversed_meaning or len(reversed_meaning) == 0:
                        reversed_meaning = reversed_in_text
                        logger.debug(f"The Empress: 从正位含义中提取逆位含义（长度: {len(reversed_meaning)}）")
                    
                    # 更新正位含义
                    upright_text = actual_upright
            
            # 移除"In readings"或"In divinatory readings"标记本身，但保留后面的所有内容
            # 使用更精确的正则表达式，只移除标记部分，不删除后面的内容
            # 模式：匹配 "In readings" 或 "In divinatory readings" 后跟可能的标点符号和空格
            upright_text = re.sub(r'^.*?In\s+(?:divinatory\s+)?readings[,\s]+', '', upright_text, flags=re.IGNORECASE | re.DOTALL).strip()
            # 如果还有冒号在开头，也移除
            upright_text = re.sub(r'^:\s*', '', upright_text).strip()
            
            # 分离描述和象征意义
            sentences = desc_symbol_text.split('.')
            if len(sentences) > 5:
                # 限制描述和象征意义的长度，避免过长
                if len(sentences) > 100:
                    sentences = sentences[:100]  # 只取前100句
                mid_point = len(sentences) // 2
                description = '. '.join(sentences[:mid_point]).strip()
                symbolic_meaning = '. '.join(sentences[mid_point:]).strip()
            else:
                description = desc_symbol_text
            
            # 清理正位含义：移除明显的逆位含义标记，但保留所有正位内容
            upright_sentences = upright_text.split('.')
            filtered_sentences = []
            for s in upright_sentences:
                s = s.strip()
                if not s:
                    continue
                # 过滤掉明显属于逆位含义的句子
                # 检查是否包含逆位标记（但不要误删包含"reversed"的正位内容）
                s_lower = s.lower()
                # 如果句子开头包含逆位标记，则跳过
                if re.match(r'^(the\s+)?(trump|card)\s+reversed', s_lower):
                    break  # 遇到逆位标记，停止处理
                if re.match(r'^reversed[,\.]?\s+(the\s+)?(card|trump)', s_lower):
                    break
                if re.match(r'^for\s+the\s+.*?\s+a\s+reversal\s+means', s_lower):
                    break
                # 保留所有其他句子（包括可能包含"reversed"的正位内容）
                # 但要过滤掉明显过短或过长的句子
                if len(s) > 10 and len(s) < 1000:  # 放宽单句长度限制
                    filtered_sentences.append(s)
            
            # 不再限制总句子数，保留所有提取的正位含义
            upright_meaning = '. '.join(filtered_sentences).strip()
        else:
            # 没有"In readings"，尝试简单分离
            sentences = main_text.split('.')
            if len(sentences) > 10:
                desc_end = len(sentences) // 3
                symbol_end = len(sentences) * 2 // 3
                description = '. '.join(sentences[:desc_end]).strip()
                symbolic_meaning = '. '.join(sentences[desc_end:symbol_end]).strip()
                upright_meaning = '. '.join(sentences[symbol_end:]).strip()
            else:
                description = main_text
        
        # 清理文本
        description = self._clean_text(description)
        symbolic_meaning = self._clean_text(symbolic_meaning)
        upright_meaning = self._clean_text(upright_meaning)
        reversed_meaning = self._clean_text(reversed_meaning)
        
        return {
            "card_name_en": card_name,
            "card_number": card_number,
            "suit": "major",
            "arcana": "major",
            "description": description,
            "symbolic_meaning": symbolic_meaning,
            "upright_meaning": upright_meaning,
            "reversed_meaning": reversed_meaning
        }
    
    def find_minor_arcana_section(self, card_rank: str, suit: str, start_search_line: int = 0) -> Optional[Tuple[int, int]]:
        """查找小阿卡纳牌的位置（在指定花色区域内）"""
        suit_upper = suit.upper()
        
        # 使用缓存的花色位置
        if suit_upper in self.suit_positions:
            suit_start = self.suit_positions[suit_upper]
        else:
            # 如果缓存中没有，尝试查找
            suit_start = -1
            for i in range(start_search_line, len(self.lines)):
                line = self.lines[i].strip()
                if line == suit_upper:
                    if i > 0 and (not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")):
                        suit_start = i
                        self.suit_positions[suit_upper] = i
                        break
        
        if suit_start < 0:
            logger.warning(f"未找到花色标题: {suit}")
            return None
        
        # 在花色区域内查找rank标题（如"KING"）
        # 注意：文档中的数字rank是全大写（如"TEN"、"TWO"）
        rank_upper = card_rank.upper()
        # 数字rank的映射
        rank_mapping = {
            "TEN": "TEN", "NINE": "NINE", "EIGHT": "EIGHT", "SEVEN": "SEVEN",
            "SIX": "SIX", "FIVE": "FIVE", "FOUR": "FOUR", "THREE": "THREE",
            "TWO": "TWO", "ACE": "ACE"
        }
        # 如果rank是数字，使用全大写
        if rank_upper in rank_mapping:
            search_rank = rank_mapping[rank_upper]
        else:
            search_rank = rank_upper
        
        rank_start = -1
        rank_end = len(self.lines)
        
        # 扩大搜索范围：从花色开始到下一个花色或章节结束（增加到1500行，确保覆盖所有rank）
        search_end = min(suit_start + 1500, len(self.lines))
        next_suits = ["WANDS", "CUPS", "SWORDS", "PENTACLES"]
        minor_ranks = ["KING", "QUEEN", "KNIGHT", "PAGE", "ACE", "TWO", "THREE", "FOUR",
                      "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN"]
        
        for i in range(suit_start + 10, search_end):
            line = self.lines[i].strip()
            line_upper = line.upper()
            
            # 检查是否是rank标题（精确匹配独立行）
            if line_upper == search_rank:
                # 确认这是独立行标题（前后有空行或"Figure"标记）
                prev_empty = i == 0 or not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")
                next_empty = i == len(self.lines) - 1 or not self.lines[i+1].strip() or self.lines[i+1].strip().startswith("Figure")
                
                if prev_empty or next_empty:
                    rank_start = i
                    logger.debug(f"找到rank标题 '{search_rank}' 在行 {i+1} (花色: {suit})")
                    
                    # 查找结束位置（下一个rank或下一个花色）
                    # 扩大搜索范围到250行，确保包含完整的逆位含义部分
                    for j in range(i + 5, min(i + 250, len(self.lines))):
                        next_line = self.lines[j].strip()
                        next_line_upper = next_line.upper()
                        
                        # 检查是否是下一个rank（独立行标题）
                        if next_line_upper in minor_ranks and next_line_upper != search_rank:
                            # 确认这是独立行标题
                            if j > 0 and (not self.lines[j-1].strip() or self.lines[j-1].strip().startswith("Figure")):
                                rank_end = j
                                logger.debug(f"找到下一个rank '{next_line_upper}' 在行 {j+1}，结束位置: {rank_end}")
                                break
                        
                        # 检查是否是下一个花色
                        if next_line_upper in next_suits and next_line_upper != suit_upper:
                            # 确认这是花色标题（独立行）
                            if j > 0 and (not self.lines[j-1].strip() or self.lines[j-1].strip().startswith("Figure")):
                                rank_end = j
                                logger.debug(f"找到下一个花色 '{next_line_upper}' 在行 {j+1}，结束位置: {rank_end}")
                                break
                        
                        # 检查是否是章节结束
                        if next_line.startswith("Chapter"):
                            rank_end = j
                            logger.debug(f"找到章节标记在行 {j+1}，结束位置: {rank_end}")
                            break
                    
                    # 如果没找到结束位置，可能是因为这是最后一个rank或者搜索范围不够
                    # 对于这种情况，至少确保不会超出下一个花色
                    if rank_end == len(self.lines):
                        # 查找下一个花色，如果找到且距离合理，使用它作为结束位置
                        for j in range(i + 5, min(i + 300, len(self.lines))):
                            next_line = self.lines[j].strip()
                            next_line_upper = next_line.upper()
                            if next_line_upper in next_suits and next_line_upper != suit_upper:
                                if j > 0 and (not self.lines[j-1].strip() or self.lines[j-1].strip().startswith("Figure")):
                                    rank_end = j
                                    logger.debug(f"找到下一个花色 '{next_line_upper}' 在行 {j+1}作为结束位置: {rank_end}")
                                    break
                    
                    break
        
        if rank_start < 0:
            logger.warning(f"在 {suit} 花色中未找到 {card_rank} (搜索: {search_rank})")
            return None
        
        if rank_end == len(self.lines):
            logger.warning(f"未找到 {card_rank} 的结束位置，使用文档末尾")
        
        logger.debug(f"章节边界: {rank_start} -> {rank_end} (共{rank_end - rank_start}行)")
        
        return (rank_start, rank_end)
    
    def extract_minor_arcana_card(self, card_name: str, card_number: int, suit: str) -> Dict[str, Any]:
        """提取小阿卡纳牌的信息"""
        logger.info(f"提取小阿卡纳: {card_name} ({suit})")
        
        # 小阿卡纳格式：标题（如"KING"）-> 描述 -> REVERSED段落
        card_rank = card_name.split(" of ")[0].strip()
        
        # 查找卡片位置（在指定花色区域内）
        section = self.find_minor_arcana_section(card_rank, suit)
        
        if not section:
            return self._create_empty_card(card_name, card_number, "minor", suit)
        
        start_line, end_line = section
        
        # 提取文本内容
        full_text = self.extract_text_section(start_line, end_line)
        
        if not full_text.strip():
            logger.warning(f"提取的文本为空: {card_name}")
            return self._create_empty_card(card_name, card_number, "minor", suit)
        
        # 移除开头的rank标题（如"EIGHT", "KING"等）
        rank_upper = card_rank.upper()
        if full_text.startswith(rank_upper + " "):
            full_text = full_text[len(rank_upper) + 1:].strip()
        elif full_text.startswith(rank_upper):
            full_text = full_text[len(rank_upper):].strip()
        
        description = ""
        upright_meaning = ""
        reversed_meaning = ""
        
        # 分离描述和占卜含义
        # 78 Degrees格式：描述（可能包含正位含义） -> REVERSED段落（逆位含义）
        
        # 查找"REVERSED"标记（通常独立成段或在一行开头）
        # 注意：避免匹配文本中的"reversed"单词（如"From the Nine reversed"）
        reversed_markers = [
            r'^REVERSED\s*$',  # 独立行的REVERSED
            r'\n\s*REVERSED\s*\n',  # 前后有换行的REVERSED
            r'\bREVERSED\s*\n',  # REVERSED后跟换行
        ]
        
        reversed_start = -1
        reversed_pattern = None
        
        for pattern in reversed_markers:
            match = re.search(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            if match:
                reversed_start = match.start()
                reversed_pattern = pattern
                logger.debug(f"找到逆位标记（模式: {pattern}）在位置 {reversed_start}")
                break
        
        # 如果没找到，尝试更宽松的模式，但需要确保是独立的REVERSED（前后有空格或换行）
        if reversed_start < 0:
            # 查找独立的REVERSED（前后有空格、换行或标点，且是大写）
            match = re.search(r'(?<![a-z])\s+REVERSED\s+(?=\n|$|[A-Z])', full_text, re.MULTILINE)
            if match:
                reversed_start = match.start()
                reversed_pattern = '独立REVERSED'
                logger.debug(f"找到逆位标记（独立REVERSED）在位置 {reversed_start}")
        
        if reversed_start >= 0:
            # 分离逆位含义
            reversed_text = full_text[reversed_start:]
            
            # 移除"REVERSED"标记本身
            reversed_text = re.sub(r'^.*?REVERSED\s*', '', reversed_text, flags=re.IGNORECASE | re.MULTILINE).strip()
            
            # 提取逆位含义（到下一章节或结束）
            # 清理：移除下一章节的文本
            # 注意：避免移除内容中的花色名称（如"SWORDS"可能出现在句子中）
            next_chapter_markers = ['KING', 'QUEEN', 'KNIGHT', 'PAGE', 'ACE', 'TWO', 'THREE', 'FOUR',
                                   'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN', 'Chapter', 'Figure']
            # 花色标记需要更严格的检查（独立行或前后有空行）
            suit_markers = ['WANDS', 'CUPS', 'SWORDS', 'PENTACLES']
            
            for marker in next_chapter_markers:
                if marker in reversed_text:
                    # 查找marker的位置，如果它在文本开头附近（前100字符），则截断
                    marker_pos = reversed_text.find(marker)
                    if marker_pos > 0 and marker_pos < 100:
                        reversed_text = reversed_text[:marker_pos].strip()
                        break
            
            # 检查花色标记（需要更严格：独立行或前后有空行/标点）
            for marker in suit_markers:
                if marker in reversed_text:
                    marker_pos = reversed_text.find(marker)
                    # 检查是否是独立的花色标题（前后有空格、换行或标点）
                    if marker_pos > 0 and marker_pos < 150:
                        # 检查前后是否有空格或换行
                        before = reversed_text[max(0, marker_pos-10):marker_pos]
                        after = reversed_text[marker_pos+len(marker):marker_pos+len(marker)+10]
                        # 如果是独立的花色标题（前后有空格或换行），则截断
                        if (not before.strip() or before.strip() in [' ', '\n', '.', ')']) and \
                           (not after.strip() or after.strip() in [' ', '\n', '.', '(', 'Chapter']):
                            reversed_text = reversed_text[:marker_pos].strip()
                            break
            
            reversed_meaning = reversed_text
            
            # 主文本（逆位之前的部分）
            main_text = full_text[:reversed_start].strip()
        else:
            main_text = full_text.strip()
            logger.debug(f"未找到REVERSED标记，卡片: {card_name}")
        
        # 从主文本中分离描述和正位含义
        # 78 Degrees格式：描述通常在开头，正位含义可能混合在描述中
        # 尝试查找"In readings"或其他占卜含义标记
        readings_markers = [
            r'\bIn readings\b',
            r'\bdivinatory\b',
            r'\breading\b',
        ]
        
        readings_start = -1
        for pattern in readings_markers:
            match = re.search(pattern, main_text, re.IGNORECASE)
            if match:
                readings_start = match.start()
                logger.debug(f"找到占卜含义标记（模式: {pattern}）在位置 {readings_start}")
                break
        
        if readings_start >= 0:
            # 分离描述和正位含义
            desc_text = main_text[:readings_start].strip()
            upright_text = main_text[readings_start:].strip()
            
            # 移除"In readings"标记
            upright_text = re.sub(r'^.*?In readings.*?:', '', upright_text, flags=re.IGNORECASE).strip()
            
            # 分离描述和正位含义
            sentences = [s.strip() for s in desc_text.split('.') if s.strip()]
            if len(sentences) > 3:
                # 前2/3作为描述
                desc_end = len(sentences) * 2 // 3
                description = '. '.join(sentences[:desc_end]).strip()
                # 剩余部分作为额外描述（如果有）
                if desc_end < len(sentences):
                    desc_extra = '. '.join(sentences[desc_end:]).strip()
                    if desc_extra and len(desc_extra) > 20:
                        description += '. ' + desc_extra
            else:
                description = desc_text
            
            # 正位含义
            upright_sentences = [s.strip() for s in upright_text.split('.') if s.strip()]
            upright_filtered = [s for s in upright_sentences if len(s) > 10]
            upright_meaning = '. '.join(upright_filtered).strip()
        else:
            # 没有"In readings"标记，尝试按句子分割
            sentences = [s.strip() for s in main_text.split('.') if s.strip()]
            if len(sentences) > 5:
                # 前2/3作为描述，后1/3作为正位含义
                desc_end = len(sentences) * 2 // 3
                description = '. '.join(sentences[:desc_end]).strip()
                upright_meaning = '. '.join(sentences[desc_end:]).strip()
            elif len(sentences) > 2:
                # 如果句子较少，至少尝试分离出一些正位含义
                # 前2/3作为描述，后1/3作为正位含义
                desc_end = len(sentences) * 2 // 3
                if desc_end < len(sentences):
                    description = '. '.join(sentences[:desc_end]).strip()
                    upright_meaning = '. '.join(sentences[desc_end:]).strip()
                else:
                    description = '. '.join(sentences).strip()
                    upright_meaning = ""
            elif len(sentences) > 0:
                # 如果只有1-2个句子，至少尝试分离
                if len(sentences) == 1:
                    description = main_text
                    upright_meaning = ""
                else:
                    # 2个句子：第一个作为描述，第二个作为正位
                    description = sentences[0]
                    upright_meaning = sentences[1]
            else:
                # 如果句子太少，全部作为描述
                description = main_text
                upright_meaning = ""
        
        # 如果描述太短（少于100字符）且主文本较长，可能是提取逻辑有问题
        # 尝试重新分配：如果主文本长度合理，将更多内容作为正位含义
        # 注意：只有在描述确实太短且正位含义缺失时才重新分配
        if (len(description) < 100 or not description) and len(main_text) > 200 and (not upright_meaning or len(upright_meaning) < 50):
            # 重新分配：前1/3作为描述，后2/3作为正位含义
            sentences = [s.strip() for s in main_text.split('.') if s.strip()]
            if len(sentences) > 3:
                desc_end = len(sentences) // 3
                if not description or len(description) < 50:
                    description = '. '.join(sentences[:desc_end]).strip()
                if not upright_meaning or len(upright_meaning) < 50:
                    upright_meaning = '. '.join(sentences[desc_end:]).strip()
        
        # 如果正位含义仍然为空，且主文本有足够长度，尝试更激进的分割
        if not upright_meaning and len(main_text) > 300:
            # 将主文本的中间部分作为正位含义
            sentences = [s.strip() for s in main_text.split('.') if s.strip()]
            if len(sentences) > 5:
                # 前1/4作为描述，中间1/2作为正位含义，最后1/4作为额外描述
                desc_end = len(sentences) // 4
                upright_end = len(sentences) * 3 // 4
                if not description or len(description) < 50:
                    description = '. '.join(sentences[:desc_end]).strip()
                upright_meaning = '. '.join(sentences[desc_end:upright_end]).strip()
        
        # 如果正位含义仍然为空，且主文本有足够长度，最后尝试一次
        if not upright_meaning and len(main_text) > 300:
            sentences = [s.strip() for s in main_text.split('.') if s.strip()]
            if len(sentences) > 5:
                # 前1/4作为描述，中间1/2作为正位含义
                desc_end = len(sentences) // 4
                upright_end = len(sentences) * 3 // 4
                if not description or len(description) < 50:
                    description = '. '.join(sentences[:desc_end]).strip()
                upright_meaning = '. '.join(sentences[desc_end:upright_end]).strip()
        
        # 清理文本
        description = self._clean_text(description)
        upright_meaning = self._clean_text(upright_meaning)
        reversed_meaning = self._clean_text(reversed_meaning)
        
        return {
            "card_name_en": card_name,
            "card_number": card_number,
            "suit": suit.lower(),
            "arcana": "minor",
            "description": description,
            "upright_meaning": upright_meaning,
            "reversed_meaning": reversed_meaning
        }
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        
        # 移除多余空格
        text = re.sub(r'\s+', ' ', text)
        # 移除页码引用（只在行首或行尾的独立数字，避免移除句子中的数字）
        # 例如：移除"83"这样的页码，但保留"Eight of Swords"中的"Eight"
        text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)  # 移除独立行的数字
        text = re.sub(r'\b\d+\b(?=\s*$)', '', text)  # 移除行尾的独立数字
        # 移除章节引用
        text = re.sub(r'Chapter \d+', '', text)
        
        return text.strip()
    
    def _create_empty_card(self, card_name: str, card_number: int, arcana: str, suit: str = "major") -> Dict[str, Any]:
        """创建空卡片（用于占位）"""
        return {
            "card_name_en": card_name,
            "card_number": card_number,
            "suit": suit.lower() if arcana == "minor" else "major",
            "arcana": arcana,
            "description": "",
            "symbolic_meaning": "" if arcana == "major" else None,
            "upright_meaning": "",
            "reversed_meaning": ""
        }
    
    def extract_single_card_test(self, card_name: str, card_number: int, arcana: str = "major") -> Dict[str, Any]:
        """测试提取单张卡片"""
        if arcana == "major":
            return self.extract_major_arcana_card(card_name, card_number)
        else:
            suit = card_name.split(" of ")[1] if " of " in card_name else "wands"
            return self.extract_minor_arcana_card(card_name, card_number, suit)


    def extract_all_cards(self) -> List[Dict[str, Any]]:
        """提取所有78张卡牌"""
        all_cards = []
        
        # 大阿卡纳配置（22张）
        major_cards_config = [
            ("The Fool", 0),
            ("The Magician", 1),
            ("The High Priestess", 2),
            ("The Empress", 3),
            ("The Emperor", 4),
            ("The Hierophant", 5),
            ("The Lovers", 6),
            ("The Chariot", 7),
            ("Strength", 8),
            ("The Hermit", 9),
            ("Wheel of Fortune", 10),
            ("Justice", 11),
            ("The Hanged Man", 12),
            ("Death", 13),
            ("Temperance", 14),
            ("The Devil", 15),
            ("The Tower", 16),
            ("The Star", 17),
            ("The Moon", 18),
            ("The Sun", 19),
            ("Judgement", 20),
            ("The World", 21),
        ]
        
        logger.info("=" * 60)
        logger.info("提取大阿卡纳（22张）...")
        logger.info("=" * 60)
        
        for card_name, card_number in major_cards_config:
            try:
                card_data = self.extract_major_arcana_card(card_name, card_number)
                all_cards.append(card_data)
                logger.info(f"  ✓ {card_name} (#{card_number}) - 描述: {len(card_data['description'])} 字符, "
                          f"正位: {len(card_data['upright_meaning'])} 字符, "
                          f"逆位: {len(card_data['reversed_meaning'])} 字符")
            except Exception as e:
                logger.error(f"  ✗ {card_name}: {e}")
                all_cards.append(self._create_empty_card(card_name, card_number, "major"))
        
        # 小阿卡纳配置（56张）
        minor_ranks = ["King", "Queen", "Knight", "Page", "Ten", "Nine", "Eight", 
                      "Seven", "Six", "Five", "Four", "Three", "Two", "Ace"]
        suits = ["Wands", "Cups", "Swords", "Pentacles"]
        
        # 编号映射
        rank_to_number = {
            "King": 14, "Queen": 13, "Knight": 12, "Page": 11,
            "Ten": 10, "Nine": 9, "Eight": 8, "Seven": 7,
            "Six": 6, "Five": 5, "Four": 4, "Three": 3,
            "Two": 2, "Ace": 1
        }
        
        logger.info("\n" + "=" * 60)
        logger.info("提取小阿卡纳（56张）...")
        logger.info("=" * 60)
        
        for suit in suits:
            logger.info(f"\n提取 {suit} 花色...")
            for rank in minor_ranks:
                card_name = f"{rank} of {suit}"
                card_number = rank_to_number[rank]
                try:
                    card_data = self.extract_minor_arcana_card(card_name, card_number, suit)
                    all_cards.append(card_data)
                    logger.info(f"  ✓ {card_name} - 描述: {len(card_data['description'])} 字符, "
                              f"正位: {len(card_data['upright_meaning'])} 字符, "
                              f"逆位: {len(card_data['reversed_meaning'])} 字符")
                except Exception as e:
                    logger.error(f"  ✗ {card_name}: {e}")
                    all_cards.append(self._create_empty_card(card_name, card_number, "minor", suit))
        
        return all_cards
    
    def generate_chinese_names(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成中文名称"""
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
            "Judgement": "审判",
            "The World": "世界",
        }
        
        for card in cards:
            card_name_en = card["card_name_en"]
            if card_name_en in chinese_names:
                card["card_name_cn"] = chinese_names[card_name_en]
            else:
                # 小阿卡纳翻译
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
        """插入卡片到数据库（添加source字段）"""
        logger.info(f"插入 {len(cards)} 张卡片到数据库...")
        
        card_data = []
        for card in cards:
            # 添加source字段，使用78degrees作为来源
            card_entry = {
                "source": "78degrees",
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
            }
            card_data.append(card_entry)
        
        try:
            # 使用 (source, card_name_en) 作为唯一约束
            result = self.supabase.table("tarot_cards").upsert(
                card_data,
                on_conflict="source,card_name_en"
            ).execute()
            
            inserted_count = len(result.data) if result.data else 0
            logger.info(f"✅ 成功插入/更新 {inserted_count} 张卡片")
            return inserted_count
        except Exception as e:
            logger.error(f"❌ 插入失败: {e}")
            raise


def main():
    """主函数"""
    doc_path = Path(__file__).parent.parent / "docs" / "78_degrees_of_wisdom.txt"
    
    if not doc_path.exists():
        logger.error(f"文档不存在: {doc_path}")
        return
    
    logger.info("=" * 60)
    logger.info("从78 Degrees of Wisdom提取所有78张塔罗牌")
    logger.info("=" * 60)
    
    extractor = SeventyEightDegreesExtractor(doc_path)
    
    # 提取所有卡牌
    all_cards = extractor.extract_all_cards()
    
    # 生成中文名称
    logger.info("\n生成中文名称...")
    all_cards = extractor.generate_chinese_names(all_cards)
    
    # 保存到JSON
    output_path = Path(__file__).parent.parent / "database" / "data" / "78degrees_tarot_cards.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_cards, f, indent=2, ensure_ascii=False)
    logger.info(f"\n保存提取数据到: {output_path}")
    
    # 插入数据库
    logger.info("\n插入数据库...")
    inserter = DatabaseInserter()
    inserted_count = inserter.insert_cards(all_cards)
    
    # 统计
    logger.info("\n" + "=" * 60)
    logger.info("提取完成!")
    logger.info(f"总卡片数: {len(all_cards)}")
    logger.info(f"大阿卡纳: {len([c for c in all_cards if c['arcana'] == 'major'])}")
    logger.info(f"小阿卡纳: {len([c for c in all_cards if c['arcana'] == 'minor'])}")
    
    # 数据质量统计
    major_with_desc = len([c for c in all_cards if c['arcana'] == 'major' and c.get('description')])
    major_with_meaning = len([c for c in all_cards if c['arcana'] == 'major' and c.get('upright_meaning')])
    minor_with_desc = len([c for c in all_cards if c['arcana'] == 'minor' and c.get('description')])
    minor_with_meaning = len([c for c in all_cards if c['arcana'] == 'minor' and c.get('upright_meaning')])
    
    logger.info(f"\n数据质量:")
    logger.info(f"大阿卡纳 - 有描述: {major_with_desc}/22, 有占卜含义: {major_with_meaning}/22")
    logger.info(f"小阿卡纳 - 有描述: {minor_with_desc}/56, 有占卜含义: {minor_with_meaning}/56")
    logger.info(f"数据库插入: {inserted_count} 张")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

