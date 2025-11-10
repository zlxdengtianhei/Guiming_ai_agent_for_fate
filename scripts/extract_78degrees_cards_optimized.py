#!/usr/bin/env python3
"""
从78 Degrees of Wisdom文档提取所有78张塔罗牌信息（优化版本）

优化策略：
1. 使用模糊边界：找到卡牌名称后，提取更大的文本块（前后各300-500行）
2. LLM智能识别：改进提示词，让LLM更智能地识别和分离各部分
   - 对于小阿卡纳，正位含义可能就在描述中，需要智能识别
   - 识别各种格式的"REVERSED"标记
   - 从描述中提取占卜相关的部分作为正位含义

优势：
- 不依赖精确的章节边界，更灵活
- LLM可以处理格式变体
- 提高小阿卡纳正位含义的提取率

输出：
- JSON文件：database/data/78degrees_tarot_cards.json
- Supabase数据库：tarot_cards表
"""

import re
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import openai
from dotenv import load_dotenv
import time

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.core.database import get_supabase_service

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LLMExtractor:
    """使用LLM提取卡牌信息的各个部分（优化版本）"""
    
    def __init__(self):
        """初始化OpenAI/OpenRouter客户端"""
        if settings.use_openrouter and settings.openrouter_api_key:
            api_key = settings.openrouter_api_key
            base_url = "https://openrouter.ai/api/v1"
            default_headers = {
                "HTTP-Referer": "https://github.com/tarot_agent",
                "X-Title": "Tarot Agent Optimized Extractor"
            }
            logger.info("Using OpenRouter for LLM extraction")
        else:
            api_key = settings.openai_api_key
            base_url = None
            default_headers = {}
            logger.info("Using OpenAI for LLM extraction")
        
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers if default_headers else None
        )
        self.model = settings.openai_chat_model
        self.temperature = 0.1
    
    async def extract_card_parts(
        self, 
        card_name: str, 
        card_section_text: str, 
        arcana: str
    ) -> Dict[str, str]:
        """
        使用LLM从章节文本中提取卡牌的各个部分（优化版本）
        
        改进点：
        1. 更智能地识别正位含义（即使没有"In readings"标记）
        2. 对于小阿卡纳，从描述中提取占卜相关的部分
        3. 识别各种格式的REVERSED标记
        """
        # 限制文本长度，但保留更多上下文
        max_text_length = 12000  # 增加到12000字符
        if len(card_section_text) > max_text_length:
            logger.warning(f"章节文本过长 ({len(card_section_text)} 字符)，使用智能截断")
            # 智能截断：保留开头和结尾部分
            front_part = max_text_length // 2  # 前6000字符
            back_part = max_text_length - front_part  # 后6000字符
            
            card_section_text = card_section_text[:front_part] + "\n\n[...中间部分已省略，保留开头和结尾...]\n\n" + card_section_text[-back_part:]
            logger.debug(f"智能截断: 保留前{front_part}字符和后{back_part}字符")
        
        is_major = arcana == "major"
        
        # 优化的系统提示词
        system_prompt = """You are an expert at extracting structured information from Tarot card descriptions from "78 Degrees of Wisdom" by Rachel Pollack.

Your task is to extract specific parts from the given text about a Tarot card.
Return ONLY valid JSON with the following structure:
{
  "description": "...",
  "symbolic_meaning": "...",
  "upright_meaning": "...",
  "reversed_meaning": "..."
}

CRITICAL RULES FOR 78 DEGREES OF WISDOM:
1. Extract ONLY the text that corresponds to each field from the original document
2. Do NOT add your own interpretation or modern interpretations
3. Use the original text from the document verbatim
4. If a field is not found in the text, return an empty string ""
5. For symbolic_meaning: only include if this is a Major Arcana card, otherwise return ""

SPECIAL HANDLING FOR UPRIGHT MEANING:
- For Major Arcana: Look for sections starting with "In readings", "In divinatory readings", etc.
- For Minor Arcana: The upright meaning may be embedded in the description. Look for:
  * Divinatory interpretations within the description
  * Phrases like "In a reading", "In readings", "The card means", "This card indicates"
  * Descriptions of what the card represents in divination (not just visual description)
  * If the description contains both visual description AND divinatory meaning, extract ONLY the divinatory part as upright_meaning
  * If you cannot separate them, include the entire description in description and leave upright_meaning empty

SPECIAL HANDLING FOR REVERSED MEANING:
- Look for sections starting with:
  * "REVERSED" (as a standalone word or heading)
  * "reversed" or "Reversed" (in sentences like "Reversed, the card means...")
  * "reversal" or "reversal means"
  * "when reversed"
  * "For [card name] a reversal means"
  * "The card reversed"
  * "Turned around" or "Turned around the image"
- Extract ALL text that describes what the card means when reversed, until the next card section or end of text

Keep the original wording from the document as much as possible.
Return ONLY the JSON object, no additional text or explanation."""
        
        user_prompt = f"""Extract information about the card "{card_name}" from the following text.

Card type: {"Major Arcana" if is_major else "Minor Arcana"}

Text:
{card_section_text}

Extract the following parts:

1. description: 
   - For Major Arcana: The visual description and general information about the card, before any divinatory meanings
   - For Minor Arcana: The visual description and general information. If divinatory meaning is mixed in, try to separate it (see upright_meaning below)

2. symbolic_meaning: 
   - ONLY for Major Arcana cards, otherwise return empty string ""
   - The deeper symbolic meaning and interpretation
   - Usually comes after the description but before divinatory meanings

3. upright_meaning: 
   - For Major Arcana: Look for sections starting with "In readings", "In divinatory readings", etc.
   - For Minor Arcana: This is CRITICAL - the upright meaning may be embedded in the description!
     * Look for divinatory interpretations within the description text
     * Phrases like "In a reading", "The card means", "This card indicates", "Romantically", etc.
     * If the description contains both visual AND divinatory content, extract ONLY the divinatory part here
     * If you cannot clearly separate them, put everything in description and leave this empty
   - Extract all text that describes what the card means when upright in divination

4. reversed_meaning: 
   - Look for sections starting with "REVERSED" (as heading), "reversed", "reversal", "when reversed", "For [card name] a reversal means", "The card reversed", "Turned around", etc.
   - Extract ALL text that describes what the card means when reversed
   - Continue until you reach the next card section or end of text

IMPORTANT: 
- For Minor Arcana, be especially careful to identify divinatory meanings that may be embedded in the description
- If you find phrases like "In a reading", "The card means", "This indicates", etc. in the description, extract that part as upright_meaning
- Make sure to extract actual content for each field. If you cannot find a specific section, return empty string "" for that field only.

Return ONLY valid JSON with the exact structure shown above."""
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"调用LLM提取 {card_name} (尝试 {attempt + 1}/{max_retries})")
                start_time = time.time()
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                    response_format={"type": "json_object"} if "gpt-4o" in self.model.lower() or "gpt-4" in self.model.lower() else None
                )
                
                elapsed = time.time() - start_time
                logger.debug(f"LLM响应时间: {elapsed:.2f}秒")
                
                result_text = response.choices[0].message.content.strip()
                
                # 尝试解析JSON
                if result_text.startswith("```json"):
                    result_text = result_text.replace("```json", "").replace("```", "").strip()
                elif result_text.startswith("```"):
                    result_text = result_text.replace("```", "").strip()
                
                result = json.loads(result_text)
                
                # 确保所有字段都存在
                extracted = {
                    "description": result.get("description", "").strip(),
                    "symbolic_meaning": result.get("symbolic_meaning", "").strip() if is_major else "",
                    "upright_meaning": result.get("upright_meaning", "").strip(),
                    "reversed_meaning": result.get("reversed_meaning", "").strip()
                }
                
                # 后处理：如果小阿卡纳的正位含义为空，但描述中包含占卜相关内容，尝试提取
                if not is_major and not extracted["upright_meaning"]:
                    # 检查描述中是否包含占卜相关内容
                    divinatory_keywords = [
                        "in a reading", "in readings", "the card means", "this card indicates",
                        "romantically", "the card signifies", "this indicates", "the card represents"
                    ]
                    desc_lower = extracted["description"].lower()
                    if any(keyword in desc_lower for keyword in divinatory_keywords):
                        logger.debug(f"{card_name}: 描述中包含占卜关键词，但LLM未提取正位含义，可能需要调整")
                
                logger.debug(f"成功提取 {card_name}: 描述={len(extracted['description'])} 字符, "
                           f"正位={len(extracted['upright_meaning'])} 字符, "
                           f"逆位={len(extracted['reversed_meaning'])} 字符")
                return extracted
                
            except json.JSONDecodeError as e:
                logger.warning(f"JSON解析失败 ({card_name}, 尝试 {attempt + 1}/{max_retries}): {e}")
                logger.debug(f"响应内容: {result_text[:500]}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return {
                        "description": "",
                        "symbolic_meaning": "",
                        "upright_meaning": "",
                        "reversed_meaning": ""
                    }
            except Exception as e:
                logger.warning(f"提取失败 ({card_name}, 尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return {
                        "description": "",
                        "symbolic_meaning": "",
                        "upright_meaning": "",
                        "reversed_meaning": ""
                    }
        
        return {
            "description": "",
            "symbolic_meaning": "",
            "upright_meaning": "",
            "reversed_meaning": ""
        }


class SeventyEightDegreesOptimizedExtractor:
    """优化提取器：模糊边界 + LLM智能识别"""
    
    def __init__(self, doc_path: Path):
        self.doc_path = doc_path
        with open(doc_path, 'r', encoding='utf-8') as f:
            self.content = f.read()
        self.lines = self.content.split('\n')
        logger.info(f"加载文档: {len(self.lines)} 行")
        
        # 初始化LLM提取器
        self.llm_extractor = LLMExtractor()
        
        # 缓存花色起始位置
        self.suit_positions = {}
        self._find_suit_positions()
    
    def _find_suit_positions(self):
        """查找并缓存所有花色的起始位置"""
        suits = ["WANDS", "CUPS", "SWORDS", "PENTACLES"]
        for suit in suits:
            for i, line in enumerate(self.lines):
                if line.strip() == suit:
                    if i > 0 and (not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")):
                        self.suit_positions[suit] = i
                        logger.debug(f"找到花色 {suit} 在行 {i+1}")
                        break
    
    def find_card_anchor(self, card_name: str, start_line: int = 0) -> Optional[int]:
        """
        找到卡牌名称的锚点位置（模糊边界策略）
        返回行号，不返回精确边界
        """
        card_name_patterns = []
        
        if not card_name.startswith("The "):
            card_name_with_the = "The " + card_name
            card_name_patterns.extend([
                card_name_with_the,
                card_name_with_the.upper(),
                card_name_with_the.lower(),
                card_name_with_the.title(),
            ])
        
        card_name_patterns.extend([
            card_name,
            card_name.upper(),
            card_name.lower(),
            card_name.title(),
        ])
        
        if card_name.startswith("The "):
            name_without_the = card_name[4:].strip()
            card_name_patterns.extend([
                name_without_the,
                name_without_the.upper(),
                name_without_the.lower(),
                name_without_the.title(),
            ])
        
        # 查找章节标题
        for i in range(start_line, len(self.lines)):
            line = self.lines[i].strip()
            
            for pattern in card_name_patterns:
                if line == pattern:
                    prev_empty = i == 0 or not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")
                    next_empty = i == len(self.lines) - 1 or not self.lines[i+1].strip() or self.lines[i+1].strip().startswith("Figure")
                    has_chapter_marker = i > 0 and ("Chapter" in self.lines[i-1] or "THE " in self.lines[i-1].upper())
                    
                    if prev_empty or next_empty or has_chapter_marker:
                        logger.debug(f"找到卡牌锚点 '{pattern}' 在行 {i+1}")
                        return i
        
        logger.warning(f"未找到卡牌锚点: {card_name}")
        return None
    
    def extract_fuzzy_section(self, anchor_line: int, arcana: str) -> str:
        """
        使用模糊边界提取文本块
        策略：找到锚点后，提取前后各一定范围的行
        """
        # 对于大阿卡纳，使用更大的范围（因为章节较长）
        # 对于小阿卡纳，使用较小的范围（但也要足够大以包含REVERSED部分）
        if arcana == "major":
            before_lines = 50  # 锚点前50行（可能包含一些上下文）
            after_lines = 400  # 锚点后400行（确保包含逆位含义）
        else:
            before_lines = 30  # 锚点前30行
            after_lines = 300  # 锚点后300行（确保包含REVERSED部分）
        
        start_line = max(0, anchor_line - before_lines)
        end_line = min(len(self.lines), anchor_line + after_lines)
        
        logger.debug(f"模糊边界提取: 行 {start_line+1} 到 {end_line+1} (锚点: {anchor_line+1})")
        
        # 提取文本，清理空行和页码
        text_lines = []
        for i in range(start_line, end_line):
            line = self.lines[i].strip()
            
            # 跳过空行、页码、纯数字行
            if not line:
                continue
            if re.match(r'^\d+$', line):
                continue
            if line.startswith("Figure"):
                continue
            
            # 跳过章节标题（但保留内容）
            if i == anchor_line and line in ["KING", "QUEEN", "KNIGHT", "PAGE", "ACE", "TWO", "THREE", "FOUR",
                                              "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN"]:
                # 这是小阿卡纳的rank标题，跳过但继续
                continue
            
            text_lines.append(line)
        
        return ' '.join(text_lines)
    
    async def extract_major_arcana_card(self, card_name: str, card_number: int) -> Dict[str, Any]:
        """提取大阿卡纳牌的信息（优化版本）"""
        logger.info(f"提取大阿卡纳: {card_name} (#{card_number})")
        
        # 步骤1: 找到锚点
        anchor = self.find_card_anchor(card_name)
        if anchor is None:
            return self._create_empty_card(card_name, card_number, "major")
        
        # 步骤2: 使用模糊边界提取文本
        section_text = self.extract_fuzzy_section(anchor, "major")
        
        if not section_text.strip():
            logger.warning(f"提取的文本为空: {card_name}")
            return self._create_empty_card(card_name, card_number, "major")
        
        logger.debug(f"提取文本: {len(section_text)} 字符")
        
        # 步骤3: 使用LLM提取各个部分
        parts = await self.llm_extractor.extract_card_parts(card_name, section_text, "major")
        
        return {
            "card_name_en": card_name,
            "card_number": card_number,
            "suit": "major",
            "arcana": "major",
            "description": self._clean_text(parts["description"]),
            "symbolic_meaning": self._clean_text(parts["symbolic_meaning"]),
            "upright_meaning": self._clean_text(parts["upright_meaning"]),
            "reversed_meaning": self._clean_text(parts["reversed_meaning"])
        }
    
    def find_minor_arcana_anchor(self, card_rank: str, suit: str, start_search_line: int = 0) -> Optional[int]:
        """找到小阿卡纳牌的锚点位置"""
        suit_upper = suit.upper()
        
        if suit_upper in self.suit_positions:
            suit_start = self.suit_positions[suit_upper]
        else:
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
        
        rank_upper = card_rank.upper()
        rank_mapping = {
            "TEN": "TEN", "NINE": "NINE", "EIGHT": "EIGHT", "SEVEN": "SEVEN",
            "SIX": "SIX", "FIVE": "FIVE", "FOUR": "FOUR", "THREE": "THREE",
            "TWO": "TWO", "ACE": "ACE"
        }
        if rank_upper in rank_mapping:
            search_rank = rank_mapping[rank_upper]
        else:
            search_rank = rank_upper
        
        # 在花色区域内查找rank标题
        search_end = min(suit_start + 1500, len(self.lines))
        
        for i in range(suit_start + 10, search_end):
            line = self.lines[i].strip()
            line_upper = line.upper()
            
            if line_upper == search_rank:
                prev_empty = i == 0 or not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")
                next_empty = i == len(self.lines) - 1 or not self.lines[i+1].strip() or self.lines[i+1].strip().startswith("Figure")
                
                if prev_empty or next_empty:
                    logger.debug(f"找到rank锚点 '{search_rank}' 在行 {i+1} (花色: {suit})")
                    return i
        
        logger.warning(f"在 {suit} 花色中未找到 {card_rank} (搜索: {search_rank})")
        return None
    
    async def extract_minor_arcana_card(self, card_name: str, card_number: int, suit: str) -> Dict[str, Any]:
        """提取小阿卡纳牌的信息（优化版本）"""
        logger.info(f"提取小阿卡纳: {card_name} ({suit})")
        
        card_rank = card_name.split(" of ")[0].strip()
        
        # 步骤1: 找到锚点
        anchor = self.find_minor_arcana_anchor(card_rank, suit)
        
        if anchor is None:
            return self._create_empty_card(card_name, card_number, "minor", suit)
        
        # 步骤2: 使用模糊边界提取文本
        section_text = self.extract_fuzzy_section(anchor, "minor")
        
        if not section_text.strip():
            logger.warning(f"提取的文本为空: {card_name}")
            return self._create_empty_card(card_name, card_number, "minor", suit)
        
        # 移除开头的rank标题（如果存在）
        rank_upper = card_rank.upper()
        if section_text.startswith(rank_upper + " "):
            section_text = section_text[len(rank_upper) + 1:].strip()
        elif section_text.startswith(rank_upper):
            section_text = section_text[len(rank_upper):].strip()
        
        logger.debug(f"提取文本: {len(section_text)} 字符")
        
        # 步骤3: 使用LLM提取各个部分
        parts = await self.llm_extractor.extract_card_parts(card_name, section_text, "minor")
        
        return {
            "card_name_en": card_name,
            "card_number": card_number,
            "suit": suit.lower(),
            "arcana": "minor",
            "description": self._clean_text(parts["description"]),
            "upright_meaning": self._clean_text(parts["upright_meaning"]),
            "reversed_meaning": self._clean_text(parts["reversed_meaning"])
        }
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)
        text = re.sub(r'\b\d+\b(?=\s*$)', '', text)
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
    
    def generate_chinese_names(self, cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成中文名称"""
        chinese_names = {
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
    
    async def extract_all_cards(self, max_concurrent: int = 3) -> List[Dict[str, Any]]:
        """提取所有78张卡牌（带并发控制）"""
        all_cards = []
        
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
        logger.info(f"提取大阿卡纳（22张），并发数: {max_concurrent}...")
        logger.info("=" * 60)
        
        # 使用信号量限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_one_major(card_name, card_number):
            async with semaphore:
                try:
                    card_data = await self.extract_major_arcana_card(card_name, card_number)
                    logger.info(f"  ✓ {card_name} (#{card_number}) - 描述: {len(card_data['description'])} 字符, "
                              f"象征: {len(card_data.get('symbolic_meaning', ''))} 字符, "
                              f"正位: {len(card_data['upright_meaning'])} 字符, "
                              f"逆位: {len(card_data['reversed_meaning'])} 字符")
                    return card_data
                except Exception as e:
                    logger.error(f"  ✗ {card_name}: {e}", exc_info=True)
                    return self._create_empty_card(card_name, card_number, "major")
        
        # 并发提取大阿卡纳
        major_tasks = [extract_one_major(name, num) for name, num in major_cards_config]
        major_results = await asyncio.gather(*major_tasks)
        all_cards.extend(major_results)
        
        minor_ranks = ["King", "Queen", "Knight", "Page", "Ten", "Nine", "Eight", 
                      "Seven", "Six", "Five", "Four", "Three", "Two", "Ace"]
        suits = ["Wands", "Cups", "Swords", "Pentacles"]
        
        rank_to_number = {
            "King": 14, "Queen": 13, "Knight": 12, "Page": 11,
            "Ten": 10, "Nine": 9, "Eight": 8, "Seven": 7,
            "Six": 6, "Five": 5, "Four": 4, "Three": 3,
            "Two": 2, "Ace": 1
        }
        
        logger.info("\n" + "=" * 60)
        logger.info(f"提取小阿卡纳（56张），并发数: {max_concurrent}...")
        logger.info("=" * 60)
        
        async def extract_one_minor(card_name, card_number, suit):
            async with semaphore:
                try:
                    card_data = await self.extract_minor_arcana_card(card_name, card_number, suit)
                    logger.info(f"  ✓ {card_name} - 描述: {len(card_data['description'])} 字符, "
                              f"正位: {len(card_data['upright_meaning'])} 字符, "
                              f"逆位: {len(card_data['reversed_meaning'])} 字符")
                    return card_data
                except Exception as e:
                    logger.error(f"  ✗ {card_name}: {e}", exc_info=True)
                    return self._create_empty_card(card_name, card_number, "minor", suit)
        
        # 并发提取小阿卡纳
        minor_tasks = []
        for suit in suits:
            logger.info(f"\n提取 {suit} 花色...")
            for rank in minor_ranks:
                card_name = f"{rank} of {suit}"
                card_number = rank_to_number[rank]
                minor_tasks.append(extract_one_minor(card_name, card_number, suit))
        
        minor_results = await asyncio.gather(*minor_tasks)
        all_cards.extend(minor_results)
        
        return all_cards


class DatabaseInserter:
    """数据库插入器"""
    
    def __init__(self):
        self.supabase = get_supabase_service()
    
    def insert_cards(self, cards: List[Dict[str, Any]]) -> int:
        """插入卡片到数据库（添加source字段）"""
        logger.info(f"插入 {len(cards)} 张卡片到数据库...")
        
        card_data = []
        for card in cards:
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


async def main():
    """主函数"""
    doc_path = Path(__file__).parent.parent / "docs" / "78_degrees_of_wisdom.txt"
    
    if not doc_path.exists():
        logger.error(f"文档不存在: {doc_path}")
        return
    
    # 检查环境变量
    if settings.use_openrouter:
        if not settings.openrouter_api_key:
            logger.error("USE_OPENROUTER=true 但未设置 OPENROUTER_API_KEY")
            return
        logger.info(f"使用 OpenRouter，模型: {settings.openai_chat_model}")
    else:
        if not settings.openai_api_key:
            logger.error("未设置 OPENAI_API_KEY")
            return
        logger.info(f"使用 OpenAI，模型: {settings.openai_chat_model}")
    
    logger.info("=" * 60)
    logger.info("从78 Degrees of Wisdom提取所有78张塔罗牌（优化版本）")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    extractor = SeventyEightDegreesOptimizedExtractor(doc_path)
    
    # 提取所有卡牌（并发数设为3，避免API限流）
    logger.info("开始提取...")
    all_cards = await extractor.extract_all_cards(max_concurrent=3)
    
    extraction_time = time.time() - start_time
    logger.info(f"\n提取完成，耗时: {extraction_time:.2f}秒")
    
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
    try:
        inserter = DatabaseInserter()
        inserted_count = inserter.insert_cards(all_cards)
    except Exception as e:
        logger.error(f"插入数据库失败: {e}", exc_info=True)
        inserted_count = 0
    
    # 统计
    logger.info("\n" + "=" * 60)
    logger.info("提取完成!")
    logger.info(f"总卡片数: {len(all_cards)}")
    logger.info(f"大阿卡纳: {len([c for c in all_cards if c['arcana'] == 'major'])}")
    logger.info(f"小阿卡纳: {len([c for c in all_cards if c['arcana'] == 'minor'])}")
    
    major_with_desc = len([c for c in all_cards if c['arcana'] == 'major' and c.get('description')])
    major_with_meaning = len([c for c in all_cards if c['arcana'] == 'major' and c.get('upright_meaning')])
    minor_with_desc = len([c for c in all_cards if c['arcana'] == 'minor' and c.get('description')])
    minor_with_meaning = len([c for c in all_cards if c['arcana'] == 'minor' and c.get('upright_meaning')])
    
    logger.info(f"\n数据质量:")
    logger.info(f"大阿卡纳 - 有描述: {major_with_desc}/22, 有占卜含义: {major_with_meaning}/22")
    logger.info(f"小阿卡纳 - 有描述: {minor_with_desc}/56, 有占卜含义: {minor_with_meaning}/56")
    logger.info(f"数据库插入: {inserted_count} 张")
    logger.info(f"总耗时: {time.time() - start_time:.2f}秒")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())





