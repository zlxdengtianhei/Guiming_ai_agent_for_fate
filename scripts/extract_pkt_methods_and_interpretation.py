"""
从PKT文档提取占卜方法和解读相关章节用于RAG

提取内容：
1. 占卜方法相关章节（Section 6, 7, 8, 9）
2. 解读相关章节（Section 3, 4, 5）

每个方法分为不同的chunk，便于RAG检索。
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_DIR = PROJECT_ROOT / "rag" / "data"

# PKT文档位置
PKT_DOC = DOCS_DIR / "pkt.txt"


def extract_text_section(lines: List[str], start_line: int, end_line: int) -> str:
    """提取指定行号范围的文本"""
    # 转换为0-based索引
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)
    
    text = "\n".join(lines[start_idx:end_idx])
    # 清理多余的空行：将3个或更多连续换行符替换为最多2个换行符
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def extract_divination_methods() -> List[Dict[str, Any]]:
    """
    提取占卜方法相关章节
    
    - Section 6: THE ART OF TAROT DIVINATION (行 1853-1856)
    - Section 7: AN ANCIENT CELTIC METHOD OF DIVINATION (行 1866-1933)
    - Section 8: AN ALTERNATIVE METHOD (行 1943-1992)
    - Section 9: 35 CARDS METHOD (行 2002-2028)
    """
    logger.info("提取占卜方法相关章节...")
    
    if not PKT_DOC.exists():
        logger.error(f"PKT文档不存在: {PKT_DOC}")
        return []
    
    with open(PKT_DOC, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    documents = []
    
    # Section 6: The Art of Tarot Divination
    section6_text = extract_text_section(lines, 1853, 1856)
    if section6_text:
        documents.append({
            "chunk_id": "pkt-art-of-divination",
            "text": section6_text,
            "source": "PKT - The Pictorial Key to the Tarot, Part III, Section 6",
            "metadata": {
                "type": "divination_method",
                "method_type": "general_principles",
                "section": "Part III, Section 6",
                "title": "THE ART OF TAROT DIVINATION",
                "lines": "1853-1856"
            }
        })
    
    # Section 7: Celtic Cross Method
    section7_text = extract_text_section(lines, 1866, 1933)
    if section7_text:
        documents.append({
            "chunk_id": "pkt-celtic-cross-method",
            "text": section7_text,
            "source": "PKT - The Pictorial Key to the Tarot, Part III, Section 7",
            "metadata": {
                "type": "divination_method",
                "method_type": "celtic_cross",
                "section": "Part III, Section 7",
                "title": "AN ANCIENT CELTIC METHOD OF DIVINATION",
                "lines": "1866-1933",
                "card_count": 10
            }
        })
    
    # Section 8: Alternative Method (42 cards)
    section8_text = extract_text_section(lines, 1943, 1992)
    if section8_text:
        documents.append({
            "chunk_id": "pkt-alternative-method-42",
            "text": section8_text,
            "source": "PKT - The Pictorial Key to the Tarot, Part III, Section 8",
            "metadata": {
                "type": "divination_method",
                "method_type": "alternative_42",
                "section": "Part III, Section 8",
                "title": "AN ALTERNATIVE METHOD OF READING THE TAROT CARDS",
                "lines": "1943-1992",
                "card_count": 42
            }
        })
    
    # Section 9: 35 Cards Method
    section9_text = extract_text_section(lines, 2002, 2028)
    if section9_text:
        documents.append({
            "chunk_id": "pkt-35-cards-method",
            "text": section9_text,
            "source": "PKT - The Pictorial Key to the Tarot, Part III, Section 9",
            "metadata": {
                "type": "divination_method",
                "method_type": "thirty_five_cards",
                "section": "Part III, Section 9",
                "title": "THE METHOD OF READING BY MEANS OF THIRTY-FIVE CARDS",
                "lines": "2002-2028",
                "card_count": 35
            }
        })
    
    logger.info(f"提取了 {len(documents)} 个占卜方法文档块")
    return documents


def extract_interpretation_major_arcana() -> List[Dict[str, Any]]:
    """
    提取大阿卡纳占卜含义（Section 3）
    
    Section 3: THE GREATER ARCANA AND THEIR DIVINATORY MEANINGS (行 1600-1648)
    
    策略：整体作为一个chunk，因为内容相对集中且相互关联
    """
    logger.info("提取大阿卡纳占卜含义...")
    
    if not PKT_DOC.exists():
        logger.error(f"PKT文档不存在: {PKT_DOC}")
        return []
    
    with open(PKT_DOC, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    section_text = extract_text_section(lines, 1600, 1648)
    
    documents = []
    
    if section_text:
        documents.append({
            "chunk_id": "pkt-major-arcana-divinatory-meanings",
            "text": section_text,
            "source": "PKT - The Pictorial Key to the Tarot, Part III, Section 3",
            "metadata": {
                "type": "interpretation",
                "arcana_type": "major",
                "section": "Part III, Section 3",
                "title": "THE GREATER ARCANA AND THEIR DIVINATORY MEANINGS",
                "lines": "1600-1648",
                "card_count": 22
            }
        })
    
    logger.info(f"提取了 {len(documents)} 个大阿卡纳解读文档块")
    return documents


def extract_interpretation_minor_arcana() -> List[Dict[str, Any]]:
    """
    提取小阿卡纳额外占卜含义（Section 4）
    
    Section 4: SOME ADDITIONAL MEANINGS OF THE LESSER ARCANA (行 1655-1768)
    
    策略：按花色分为4个chunk（Wands, Cups, Swords, Pentacles）
    """
    logger.info("提取小阿卡纳额外占卜含义...")
    
    if not PKT_DOC.exists():
        logger.error(f"PKT文档不存在: {PKT_DOC}")
        return []
    
    with open(PKT_DOC, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    section_text = extract_text_section(lines, 1655, 1768)
    
    documents = []
    
    if not section_text:
        return documents
    
    # 按花色分割
    suits = {
        "WANDS": {
            "start_marker": "WANDS.",
            "end_marker": "Cups.",
            "chunk_id": "pkt-minor-arcana-wands-additional",
            "suit": "Wands"
        },
        "CUPS": {
            "start_marker": "Cups.",
            "end_marker": "SWORDS.",
            "chunk_id": "pkt-minor-arcana-cups-additional",
            "suit": "Cups"
        },
        "SWORDS": {
            "start_marker": "SWORDS.",
            "end_marker": "PENTACLES.",
            "chunk_id": "pkt-minor-arcana-swords-additional",
            "suit": "Swords"
        },
        "PENTACLES": {
            "start_marker": "PENTACLES.",
            "end_marker": "It will be observed",  # 章节结束标记
            "chunk_id": "pkt-minor-arcana-pentacles-additional",
            "suit": "Pentacles"
        }
    }
    
    for suit_name, suit_info in suits.items():
        start_idx = section_text.find(suit_info["start_marker"])
        if start_idx == -1:
            logger.warning(f"未找到 {suit_name} 的开始标记")
            continue
        
        end_idx = section_text.find(suit_info["end_marker"], start_idx + len(suit_info["start_marker"]))
        if end_idx == -1:
            # 如果是最后一个花色，取到文本末尾
            if suit_name == "PENTACLES":
                suit_text = section_text[start_idx:]
            else:
                logger.warning(f"未找到 {suit_name} 的结束标记")
                continue
        else:
            suit_text = section_text[start_idx:end_idx]
        
        suit_text = suit_text.strip()
        if suit_text:
            documents.append({
                "chunk_id": suit_info["chunk_id"],
                "text": suit_text,
                "source": "PKT - The Pictorial Key to the Tarot, Part III, Section 4",
                "metadata": {
                    "type": "interpretation",
                    "arcana_type": "minor",
                    "suit": suit_info["suit"],
                    "section": "Part III, Section 4",
                    "title": f"SOME ADDITIONAL MEANINGS OF THE LESSER ARCANA - {suit_name}",
                    "lines": "1655-1768"
                }
            })
    
    logger.info(f"提取了 {len(documents)} 个小阿卡纳解读文档块")
    return documents


def extract_recurrence_of_cards() -> List[Dict[str, Any]]:
    """
    提取重复牌的含义（Section 5）
    
    Section 5: THE RECURRENCE OF CARDS IN DEALING (行 1778-1846)
    
    策略：分为两个chunk（自然位置和逆位）
    """
    logger.info("提取重复牌含义...")
    
    if not PKT_DOC.exists():
        logger.error(f"PKT文档不存在: {PKT_DOC}")
        return []
    
    with open(PKT_DOC, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    section_text = extract_text_section(lines, 1778, 1846)
    
    documents = []
    
    if not section_text:
        return documents
    
    # 分割为自然位置和逆位两部分
    reversed_marker = "Reversed"
    reversed_idx = section_text.find(reversed_marker)
    
    if reversed_idx != -1:
        # 自然位置部分
        natural_text = section_text[:reversed_idx].strip()
        if natural_text:
            documents.append({
                "chunk_id": "pkt-recurrence-natural-position",
                "text": natural_text,
                "source": "PKT - The Pictorial Key to the Tarot, Part III, Section 5",
                "metadata": {
                    "type": "interpretation",
                    "interpretation_type": "recurrence",
                    "position": "natural",
                    "section": "Part III, Section 5",
                    "title": "THE RECURRENCE OF CARDS IN DEALING - In the Natural Position",
                    "lines": "1778-1846"
                }
            })
        
        # 逆位部分
        reversed_text = section_text[reversed_idx:].strip()
        if reversed_text:
            documents.append({
                "chunk_id": "pkt-recurrence-reversed",
                "text": reversed_text,
                "source": "PKT - The Pictorial Key to the Tarot, Part III, Section 5",
                "metadata": {
                    "type": "interpretation",
                    "interpretation_type": "recurrence",
                    "position": "reversed",
                    "section": "Part III, Section 5",
                    "title": "THE RECURRENCE OF CARDS IN DEALING - Reversed",
                    "lines": "1778-1846"
                }
            })
    else:
        # 如果找不到分割标记，整个作为一个chunk
        documents.append({
            "chunk_id": "pkt-recurrence-cards",
            "text": section_text,
            "source": "PKT - The Pictorial Key to the Tarot, Part III, Section 5",
            "metadata": {
                "type": "interpretation",
                "interpretation_type": "recurrence",
                "section": "Part III, Section 5",
                "title": "THE RECURRENCE OF CARDS IN DEALING",
                "lines": "1778-1846"
            }
        })
    
    logger.info(f"提取了 {len(documents)} 个重复牌解读文档块")
    return documents


def main():
    """主函数：提取所有占卜方法和解读相关内容"""
    logger.info("开始提取PKT文档中的占卜方法和解读相关内容...")
    
    all_documents = []
    
    # 1. 提取占卜方法
    all_documents.extend(extract_divination_methods())
    
    # 2. 提取大阿卡纳占卜含义
    all_documents.extend(extract_interpretation_major_arcana())
    
    # 3. 提取小阿卡纳额外占卜含义
    all_documents.extend(extract_interpretation_minor_arcana())
    
    # 4. 提取重复牌含义
    all_documents.extend(extract_recurrence_of_cards())
    
    # 保存到JSON文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "pkt_methods_and_interpretation.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_documents, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ 提取完成！")
    logger.info(f"   - 总文档块数: {len(all_documents)}")
    logger.info(f"   - 输出文件: {output_file}")
    
    # 统计信息
    by_type = {}
    for doc in all_documents:
        doc_type = doc.get('metadata', {}).get('type', 'unknown')
        by_type[doc_type] = by_type.get(doc_type, 0) + 1
    
    logger.info(f"\n按类型分类统计:")
    for doc_type, count in by_type.items():
        logger.info(f"   - {doc_type}: {count} 个文档块")
    
    # 方法类型统计
    method_types = {}
    for doc in all_documents:
        if doc.get('metadata', {}).get('type') == 'divination_method':
            method_type = doc.get('metadata', {}).get('method_type', 'unknown')
            method_types[method_type] = method_types.get(method_type, 0) + 1
    
    if method_types:
        logger.info(f"\n占卜方法类型统计:")
        for method_type, count in method_types.items():
            logger.info(f"   - {method_type}: {count} 个文档块")
    
    return all_documents


if __name__ == "__main__":
    main()

