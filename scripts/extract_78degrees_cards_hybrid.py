#!/usr/bin/env python3
"""
从78 Degrees of Wisdom文档提取所有78张塔罗牌信息（混合方法）

提取策略：
1. 使用代码分割找到每张牌的章节范围（精确行号定位）
2. 在每个章节范围内使用LLM识别和提取不同部分：
   - description（描述）
   - symbolic_meaning（象征意义，仅大阿卡纳）
   - upright_meaning（正位含义）
   - reversed_meaning（逆位含义）

优势：
- 代码分割提供准确的章节边界，避免LLM处理整个文档
- LLM处理复杂的内容识别和提取，提高准确性
- 使用便宜的模型（gpt-4o-mini）降低成本

输出：
- JSON文件：database/data/78degrees_tarot_cards.json
- Supabase数据库：tarot_cards表（使用upsert更新，基于card_name_en）

使用方法：
    python scripts/extract_78degrees_cards_hybrid.py
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
    """使用LLM提取卡牌信息的各个部分"""
    
    def __init__(self):
        """初始化OpenAI/OpenRouter客户端"""
        if settings.use_openrouter and settings.openrouter_api_key:
            api_key = settings.openrouter_api_key
            base_url = "https://openrouter.ai/api/v1"
            default_headers = {
                "HTTP-Referer": "https://github.com/tarot_agent",
                "X-Title": "Tarot Agent Hybrid Extractor"
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
        self.temperature = 0.1  # 低温度确保一致性
    
    async def extract_card_parts(
        self, 
        card_name: str, 
        card_section_text: str, 
        arcana: str
    ) -> Dict[str, str]:
        """
        使用LLM从章节文本中提取卡牌的各个部分
        
        Args:
            card_name: 卡牌名称
            card_section_text: 章节文本
            arcana: "major" 或 "minor"
            
        Returns:
            包含description, symbolic_meaning, upright_meaning, reversed_meaning的字典
        """
        # 限制文本长度，避免token过多
        # 但不要过度截断，因为我们需要逆位含义
        max_text_length = 10000  # 增加到10000字符，约7000 tokens
        if len(card_section_text) > max_text_length:
            logger.warning(f"章节文本过长 ({len(card_section_text)} 字符)，使用智能截断")
            # 智能截断：保留开头和结尾部分（因为逆位含义通常在结尾）
            # 计算前后各保留多少
            front_part = max_text_length // 2  # 前5000字符
            back_part = max_text_length - front_part  # 后5000字符
            
            # 保留开头和结尾
            if len(card_section_text) > max_text_length:
                card_section_text = card_section_text[:front_part] + "\n\n[...中间部分已省略，保留开头和结尾...]\n\n" + card_section_text[-back_part:]
                logger.debug(f"智能截断: 保留前{front_part}字符和后{back_part}字符")
        
        # 构建提示词
        is_major = arcana == "major"
        
        system_prompt = """You are an expert at extracting structured information from Tarot card descriptions.
Your task is to extract specific parts from the given text about a Tarot card.
Return ONLY valid JSON with the following structure:
{
  "description": "...",
  "symbolic_meaning": "...",
  "upright_meaning": "...",
  "reversed_meaning": "..."
}

Rules:
- Extract ONLY the text that corresponds to each field from the original document
- Do NOT add your own interpretation or modern interpretations
- Use the original text from the document verbatim
- If a field is not found in the text, return an empty string ""
- For symbolic_meaning: only include if this is a Major Arcana card, otherwise return ""
- For upright_meaning: Look for sections starting with phrases like "In readings", "In divinatory readings", "When the card appears upright", etc. Extract the divinatory meaning when the card is upright.
- For reversed_meaning: Look for sections starting with phrases like "reversed", "reversal", "when reversed", "For [card name] a reversal means", "Reversed, the card", etc. Extract the divinatory meaning when the card is reversed.
- Keep the original wording from the document as much as possible
- Return ONLY the JSON object, no additional text or explanation
- Each field should contain meaningful content extracted from the text, not empty or placeholder text"""
        
        user_prompt = f"""Extract information about the card "{card_name}" from the following text.

Card type: {"Major Arcana" if is_major else "Minor Arcana"}

Text:
{card_section_text}

Extract the following parts:

1. description: The visual description and general information about the card. This is usually at the beginning of the text, before any divinatory meanings.

2. symbolic_meaning: The deeper symbolic meaning and interpretation (ONLY for Major Arcana cards, otherwise return empty string ""). This usually comes after the description but before divinatory meanings.

3. upright_meaning: The divinatory meaning when the card is upright. Look for sections starting with phrases like:
   - "In readings"
   - "In divinatory readings"
   - "When the card appears upright"
   - Similar divinatory context markers
   Extract all the text that describes what the card means when upright.

4. reversed_meaning: The divinatory meaning when the card is reversed. Look for sections starting with phrases like:
   - "reversed" or "Reversed"
   - "reversal" or "reversal means"
   - "when reversed"
   - "For [card name] a reversal means"
   - "The card reversed"
   Extract all the text that describes what the card means when reversed.

IMPORTANT: Make sure to extract actual content for each field. If you cannot find a specific section, return empty string "" for that field only.

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
                
                # 调试：打印提取结果
                logger.debug(f"LLM原始响应长度: {len(result_text)} 字符")
                logger.debug(f"提取的JSON字段: {list(result.keys())}")
                
                # 确保所有字段都存在
                extracted = {
                    "description": result.get("description", "").strip(),
                    "symbolic_meaning": result.get("symbolic_meaning", "").strip() if is_major else "",
                    "upright_meaning": result.get("upright_meaning", "").strip(),
                    "reversed_meaning": result.get("reversed_meaning", "").strip()
                }
                
                # 如果正位含义为空，尝试从description中查找
                if not extracted["upright_meaning"] and "In readings" in card_section_text:
                    logger.warning(f"{card_name}: 正位含义为空，但文本中包含'In readings'，可能需要调整提示词")
                
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


class SeventyEightDegreesHybridExtractor:
    """混合提取器：代码分割 + LLM处理"""
    
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
    
    def find_card_section(self, card_name: str, start_line: int = 0) -> Optional[Tuple[int, int]]:
        """查找卡牌章节的起始和结束行号（复用原有逻辑）"""
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
        
        start_idx = -1
        end_idx = len(self.lines)
        
        # 查找章节标题
        for i in range(start_line, len(self.lines)):
            line = self.lines[i].strip()
            
            for pattern in card_name_patterns:
                if line == pattern:
                    prev_empty = i == 0 or not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")
                    next_empty = i == len(self.lines) - 1 or not self.lines[i+1].strip() or self.lines[i+1].strip().startswith("Figure")
                    has_chapter_marker = i > 0 and ("Chapter" in self.lines[i-1] or "THE " in self.lines[i-1].upper())
                    
                    if prev_empty or next_empty or has_chapter_marker:
                        start_idx = i
                        logger.debug(f"找到卡牌标题 '{pattern}' 在行 {i+1}")
                        break
            
            if start_idx >= 0:
                break
        
        if start_idx < 0:
            logger.warning(f"未找到卡牌章节: {card_name}")
            return None
        
        # 查找章节结束位置
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
        
        # 如果没找到结束位置，使用默认限制（避免提取整个文档）
        if end_idx == len(self.lines) or end_idx - start_idx > 300:
            # 限制在最合理的范围内：300行或搜索结束位置
            end_idx = min(start_idx + 300, search_end)
            logger.warning(f"未找到章节结束位置，使用默认限制: {start_idx} -> {end_idx} (共{end_idx - start_idx}行)")
        
        logger.debug(f"章节边界: {start_idx} -> {end_idx} (共{end_idx - start_idx}行)")
        return (start_idx, end_idx)
    
    def extract_text_section(self, start_line: int, end_line: int) -> str:
        """提取指定行号范围内的文本"""
        text_lines = []
        
        minor_ranks = ["KING", "QUEEN", "KNIGHT", "PAGE", "ACE", "TWO", "THREE", "FOUR",
                      "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN"]
        
        for i in range(start_line, end_line):
            line = self.lines[i].strip()
            
            if not line:
                continue
            
            if re.match(r'^\d+$', line):
                continue
            
            if line.upper() in minor_ranks and i == start_line:
                prev_empty = i == 0 or not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")
                next_empty = i == len(self.lines) - 1 or not self.lines[i+1].strip() or self.lines[i+1].strip().startswith("Figure")
                if prev_empty or next_empty:
                    continue
            
            if line.startswith("Chapter"):
                if i > start_line + 10:
                    continue
            
            text_lines.append(line)
        
        return ' '.join(text_lines)
    
    async def extract_major_arcana_card(self, card_name: str, card_number: int) -> Dict[str, Any]:
        """提取大阿卡纳牌的信息（混合方法）"""
        logger.info(f"提取大阿卡纳: {card_name} (#{card_number})")
        
        # 步骤1: 使用代码分割找到章节范围
        section = self.find_card_section(card_name)
        if not section:
            return self._create_empty_card(card_name, card_number, "major")
        
        start_line, end_line = section
        
        # 步骤2: 提取章节文本
        section_text = self.extract_text_section(start_line, end_line)
        
        if not section_text.strip():
            logger.warning(f"章节文本为空: {card_name}")
            return self._create_empty_card(card_name, card_number, "major")
        
        logger.debug(f"提取章节文本: {len(section_text)} 字符")
        
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
    
    def find_minor_arcana_section(self, card_rank: str, suit: str, start_search_line: int = 0) -> Optional[Tuple[int, int]]:
        """查找小阿卡纳牌的位置（在指定花色区域内）"""
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
        
        rank_start = -1
        rank_end = len(self.lines)
        
        search_end = min(suit_start + 1500, len(self.lines))
        next_suits = ["WANDS", "CUPS", "SWORDS", "PENTACLES"]
        minor_ranks = ["KING", "QUEEN", "KNIGHT", "PAGE", "ACE", "TWO", "THREE", "FOUR",
                      "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN"]
        
        for i in range(suit_start + 10, search_end):
            line = self.lines[i].strip()
            line_upper = line.upper()
            
            if line_upper == search_rank:
                prev_empty = i == 0 or not self.lines[i-1].strip() or self.lines[i-1].strip().startswith("Figure")
                next_empty = i == len(self.lines) - 1 or not self.lines[i+1].strip() or self.lines[i+1].strip().startswith("Figure")
                
                if prev_empty or next_empty:
                    rank_start = i
                    logger.debug(f"找到rank标题 '{search_rank}' 在行 {i+1} (花色: {suit})")
                    
                    for j in range(i + 5, min(i + 250, len(self.lines))):
                        next_line = self.lines[j].strip()
                        next_line_upper = next_line.upper()
                        
                        if next_line_upper in minor_ranks and next_line_upper != search_rank:
                            if j > 0 and (not self.lines[j-1].strip() or self.lines[j-1].strip().startswith("Figure")):
                                rank_end = j
                                logger.debug(f"找到下一个rank '{next_line_upper}' 在行 {j+1}，结束位置: {rank_end}")
                                break
                        
                        if next_line_upper in next_suits and next_line_upper != suit_upper:
                            if j > 0 and (not self.lines[j-1].strip() or self.lines[j-1].strip().startswith("Figure")):
                                rank_end = j
                                logger.debug(f"找到下一个花色 '{next_line_upper}' 在行 {j+1}，结束位置: {rank_end}")
                                break
                        
                        if next_line.startswith("Chapter"):
                            rank_end = j
                            logger.debug(f"找到章节标记在行 {j+1}，结束位置: {rank_end}")
                            break
                    
                    if rank_end == len(self.lines):
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
        
        logger.debug(f"章节边界: {rank_start} -> {rank_end} (共{rank_end - rank_start}行)")
        return (rank_start, rank_end)
    
    async def extract_minor_arcana_card(self, card_name: str, card_number: int, suit: str) -> Dict[str, Any]:
        """提取小阿卡纳牌的信息（混合方法）"""
        logger.info(f"提取小阿卡纳: {card_name} ({suit})")
        
        card_rank = card_name.split(" of ")[0].strip()
        
        # 步骤1: 使用代码分割找到章节范围
        section = self.find_minor_arcana_section(card_rank, suit)
        
        if not section:
            return self._create_empty_card(card_name, card_number, "minor", suit)
        
        start_line, end_line = section
        
        # 步骤2: 提取章节文本
        section_text = self.extract_text_section(start_line, end_line)
        
        if not section_text.strip():
            logger.warning(f"提取的文本为空: {card_name}")
            return self._create_empty_card(card_name, card_number, "minor", suit)
        
        # 移除开头的rank标题
        rank_upper = card_rank.upper()
        if section_text.startswith(rank_upper + " "):
            section_text = section_text[len(rank_upper) + 1:].strip()
        elif section_text.startswith(rank_upper):
            section_text = section_text[len(rank_upper):].strip()
        
        logger.debug(f"提取章节文本: {len(section_text)} 字符")
        
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
    logger.info("从78 Degrees of Wisdom提取所有78张塔罗牌（混合方法）")
    logger.info("=" * 60)
    
    start_time = time.time()
    
    extractor = SeventyEightDegreesHybridExtractor(doc_path)
    
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

