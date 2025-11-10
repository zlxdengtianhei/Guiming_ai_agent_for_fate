"""
从78 Degrees of Wisdom文档提取占卜方法和解读相关章节用于RAG

提取内容：
1. 占卜方法相关章节（Chapter 5, 6）
   - Chapter 5: Introduction to Tarot Divination
   - Chapter 6: Types of Readings
     - THE CELTIC CROSS
     - THE WORK CYCLE  
     - THE TREE OF LIFE
2. 解读相关章节（Chapter 7, 8）
   - Chapter 7: How to Use Tarot Readings
   - Chapter 8: What We Learn from Tarot Readings

每个方法分为不同的chunk，便于RAG检索。
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_DIR = PROJECT_ROOT / "rag" / "data"

# 78 Degrees文档位置
DOC_78DEGREES = DOCS_DIR / "78_degrees_of_wisdom.txt"


def extract_text_section(lines: List[str], start_line: int, end_line: int) -> str:
    """提取指定行号范围的文本"""
    # 转换为0-based索引
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)
    
    text = "\n".join(lines[start_idx:end_idx])
    # 清理多余的空行：将3个或更多连续换行符替换为最多2个换行符
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def find_section_start(lines: List[str], marker: str, start_from: int = 0) -> int:
    """查找章节开始位置（返回行号，1-based）"""
    for i in range(start_from, len(lines)):
        if marker.lower() in lines[i].lower():
            return i + 1  # 返回1-based行号
    return -1


def find_section_end(lines: List[str], start_line: int, end_markers: List[str]) -> int:
    """查找章节结束位置（返回行号，1-based）"""
    start_idx = start_line - 1
    for i in range(start_idx + 1, len(lines)):
        line = lines[i].strip()
        # 检查是否为章节标题（全大写或Chapter开头）
        if line and (line.isupper() or line.startswith("Chapter")):
            # 检查是否是下一个章节的开始
            for marker in end_markers:
                if marker.lower() in line.lower():
                    return i  # 返回结束行号（1-based）
    return len(lines)


def extract_divination_methods() -> List[Dict[str, Any]]:
    """
    提取占卜方法相关章节
    
    - Chapter 5: Introduction to Tarot Divination (行 11440-12200左右)
    - Chapter 6: Types of Readings (行 12225开始)
      - THE CELTIC CROSS (行 12225-13120左右)
      - THE WORK CYCLE (行 13124-13627左右)
      - THE TREE OF LIFE (行 13627-14245左右)
    """
    logger.info("提取占卜方法相关章节...")
    
    if not DOC_78DEGREES.exists():
        logger.error(f"78 Degrees文档不存在: {DOC_78DEGREES}")
        return []
    
    with open(DOC_78DEGREES, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    documents = []
    
    # Chapter 5: Introduction to Tarot Divination
    chapter5_start = find_section_start(lines, "Chapter 5")
    chapter5_end = find_section_end(lines, chapter5_start, ["Chapter 6", "THE CELTIC CROSS", "TYPES OF READINGS"])
    
    if chapter5_start > 0:
        chapter5_text = extract_text_section(lines, chapter5_start, chapter5_end)
        if chapter5_text:
            documents.append({
                "chunk_id": "78degrees-intro-divination",
                "text": chapter5_text,
                "source": "78 Degrees of Wisdom - Chapter 5",
                "metadata": {
                    "type": "divination_method",
                    "method_type": "introduction",
                    "chapter": "Chapter 5",
                    "title": "Introduction to Tarot Divination",
                    "lines": f"{chapter5_start}-{chapter5_end}"
                }
            })
    
    # Chapter 6: Types of Readings - 通用占卜方法（选择Significator、洗牌、切牌等）
    # 这部分在"TYPES OF READINGS"标题之后，THE CELTIC CROSS之前
    # 需要找到正确的"TYPES OF READINGS"位置（在Chapter 5之后，且包含Significator相关内容）
    celtic_cross_start = find_section_start(lines, "THE CELTIC CROSS")
    
    # 从Chapter 5结束位置开始查找，找到第一个包含Significator的"TYPES OF READINGS"部分
    chapter5_end = find_section_end(lines, chapter5_start, ["Chapter 6", "THE CELTIC CROSS", "TYPES OF READINGS"])
    types_start = -1
    
    # 在Chapter 5结束和Celtic Cross开始之间查找包含Significator的TYPES OF READINGS
    if chapter5_end > 0 and celtic_cross_start > 0:
        for i in range(chapter5_end - 1, min(celtic_cross_start, len(lines))):
            if "TYPES OF READINGS" in lines[i]:
                # 检查接下来的内容是否包含Significator
                check_range = min(i + 50, len(lines))
                next_text = " ".join(lines[i:check_range]).lower()
                if "significator" in next_text or "chinese people" in next_text:
                    types_start = i + 1
                    break
    
    if types_start > 0 and celtic_cross_start > 0 and types_start < celtic_cross_start:
        general_methods_text = extract_text_section(lines, types_start, celtic_cross_start)
        if general_methods_text and "Significator" in general_methods_text:
            documents.append({
                "chunk_id": "78degrees-general-reading-methods",
                "text": general_methods_text,
                "source": "78 Degrees of Wisdom - Chapter 6",
                "metadata": {
                    "type": "divination_method",
                    "method_type": "general_methods",
                    "chapter": "Chapter 6",
                    "title": "General Reading Methods - Significator, Shuffling, Cutting",
                    "lines": f"{types_start}-{celtic_cross_start}"
                }
            })
    
    # Chapter 6: Types of Readings - THE CELTIC CROSS
    celtic_cross_end = find_section_end(lines, celtic_cross_start, ["THE WORK CYCLE", "THE TREE OF LIFE"])
    
    if celtic_cross_start > 0:
        celtic_cross_text = extract_text_section(lines, celtic_cross_start, celtic_cross_end)
        if celtic_cross_text:
            documents.append({
                "chunk_id": "78degrees-celtic-cross-method",
                "text": celtic_cross_text,
                "source": "78 Degrees of Wisdom - Chapter 6",
                "metadata": {
                    "type": "divination_method",
                    "method_type": "celtic_cross",
                    "chapter": "Chapter 6",
                    "title": "THE CELTIC CROSS",
                    "lines": f"{celtic_cross_start}-{celtic_cross_end}",
                    "card_count": 10
                }
            })
    
    # Chapter 6: Types of Readings - THE WORK CYCLE
    work_cycle_start = find_section_start(lines, "THE WORK CYCLE")
    work_cycle_end = find_section_end(lines, work_cycle_start, ["THE TREE OF LIFE", "Chapter 7"])
    
    if work_cycle_start > 0:
        work_cycle_text = extract_text_section(lines, work_cycle_start, work_cycle_end)
        if work_cycle_text:
            documents.append({
                "chunk_id": "78degrees-work-cycle-method",
                "text": work_cycle_text,
                "source": "78 Degrees of Wisdom - Chapter 6",
                "metadata": {
                    "type": "divination_method",
                    "method_type": "work_cycle",
                    "chapter": "Chapter 6",
                    "title": "THE WORK CYCLE",
                    "lines": f"{work_cycle_start}-{work_cycle_end}",
                    "card_count": "variable"
                }
            })
    
    # Chapter 6: Types of Readings - THE TREE OF LIFE
    # 将Tree of Life分为多个chunks：Introduction, Structure, Layout, 以及每个Sephirah
    # 先找到Work Cycle结束位置，Tree of Life应该在其后
    work_cycle_start = find_section_start(lines, "THE WORK CYCLE")
    work_cycle_end = find_section_start(lines, "THE TREE OF LIFE", work_cycle_start) if work_cycle_start > 0 else -1
    
    tree_life_start = work_cycle_end if work_cycle_end > 0 else find_section_start(lines, "THE TREE OF LIFE")
    tree_life_end = find_section_end(lines, tree_life_start, ["Chapter 7", "How to Use"])
    
    if tree_life_start > 0:
        # 1. Introduction
        intro_start = tree_life_start
        structure_start = find_section_start(lines, "THE STRUCTURE OF THE TREE", tree_life_start)
        intro_end = structure_start if structure_start > 0 else tree_life_end
        intro_text = extract_text_section(lines, intro_start, intro_end)
        if intro_text:
            documents.append({
                "chunk_id": "78degrees-tree-of-life-introduction",
                "text": intro_text,
                "source": "78 Degrees of Wisdom - Chapter 6",
                "metadata": {
                    "type": "divination_method",
                    "method_type": "tree_of_life",
                    "chapter": "Chapter 6",
                    "title": "THE TREE OF LIFE - Introduction",
                    "lines": f"{intro_start}-{intro_end}",
                    "section": "introduction"
                }
            })
        
        # 2. Structure
        if structure_start > 0:
            layout_start = find_section_start(lines, "THE LAYOUT", structure_start)
            structure_end = layout_start if layout_start > 0 else tree_life_end
            structure_text = extract_text_section(lines, structure_start, structure_end)
            if structure_text:
                documents.append({
                    "chunk_id": "78degrees-tree-of-life-structure",
                    "text": structure_text,
                    "source": "78 Degrees of Wisdom - Chapter 6",
                    "metadata": {
                        "type": "divination_method",
                        "method_type": "tree_of_life",
                        "chapter": "Chapter 6",
                        "title": "THE TREE OF LIFE - The Structure of the Tree",
                        "lines": f"{structure_start}-{structure_end}",
                        "section": "structure"
                    }
                })
        
        # 3. Layout
        if layout_start > 0:
            layout_end = find_section_end(lines, layout_start, ["THE POSITIONS AND MEANINGS", "What then are"])
            layout_text = extract_text_section(lines, layout_start, layout_end)
            if layout_text:
                documents.append({
                    "chunk_id": "78degrees-tree-of-life-layout",
                    "text": layout_text,
                    "source": "78 Degrees of Wisdom - Chapter 6",
                    "metadata": {
                        "type": "divination_method",
                        "method_type": "tree_of_life",
                        "chapter": "Chapter 6",
                        "title": "THE TREE OF LIFE - The Layout",
                        "lines": f"{layout_start}-{layout_end}",
                        "section": "layout"
                    }
                })
        
        # 4. Positions and Meanings - 每个Sephirah作为单独的chunk
        positions_start = find_section_start(lines, "THE POSITIONS AND MEANINGS")
        if positions_start == -1:
            positions_start = find_section_start(lines, "What then are the specific")
        
        if positions_start > 0:
            # 定义10个Sephirah的位置
            sephiroth_markers = [
                ("1 Kether", "Kether or Crown"),
                ("2 Hokmah", "Hokmah or Wisdom"),
                ("3 Binah", "Binah or Understanding"),
                ("4 Gevurah", "Gevurah or Judgement"),
                ("5 Hesed", "Hesed or Mercy"),
                ("6 Tifereth", "Tifereth or Beauty"),
                ("7 Netzach", "Netzach or Eternity"),
                ("8 Hod", "Hod or Reverberation"),
                ("9 Yesod", "Yesod or Foundation"),
                ("10 Malkuth", "Malkuth or Kingdom")
            ]
            
            for i, (marker1, marker2) in enumerate(sephiroth_markers):
                sephiroth_start = find_section_start(lines, marker1, positions_start)
                if sephiroth_start == -1:
                    sephiroth_start = find_section_start(lines, marker2, positions_start)
                
                if sephiroth_start > 0:
                    # 下一个Sephirah的开始位置，或章节结束
                    if i < len(sephiroth_markers) - 1:
                        next_sephiroth_start = find_section_start(lines, sephiroth_markers[i+1][0], sephiroth_start)
                        if next_sephiroth_start == -1:
                            next_sephiroth_start = find_section_start(lines, sephiroth_markers[i+1][1], sephiroth_start)
                        sephiroth_end = next_sephiroth_start if next_sephiroth_start > 0 else tree_life_end
                    else:
                        sephiroth_end = tree_life_end
                    
                    sephiroth_text = extract_text_section(lines, sephiroth_start, sephiroth_end)
                    if sephiroth_text:
                        sephiroth_name = marker2.split(" or ")[1] if " or " in marker2 else marker2
                        documents.append({
                            "chunk_id": f"78degrees-tree-of-life-sephiroth-{i+1}-{sephiroth_name.lower().replace(' ', '-')}",
                            "text": sephiroth_text,
                            "source": "78 Degrees of Wisdom - Chapter 6",
                            "metadata": {
                                "type": "divination_method",
                                "method_type": "tree_of_life",
                                "chapter": "Chapter 6",
                                "title": f"THE TREE OF LIFE - {marker2}",
                                "lines": f"{sephiroth_start}-{sephiroth_end}",
                                "section": "sephiroth",
                                "sephiroth_number": i + 1,
                                "sephiroth_name": sephiroth_name
                            }
                        })
    
    logger.info(f"提取了 {len(documents)} 个占卜方法文档块")
    return documents


def extract_interpretation_chapters() -> List[Dict[str, Any]]:
    """
    提取解读相关章节
    
    - Chapter 7: How to Use Tarot Readings (行 14245-15055左右)
    - Chapter 8: What We Learn from Tarot Readings (行 15055-文档结束)
    
    策略：每个章节作为一个chunk，因为内容相对集中且相互关联
    """
    logger.info("提取解读相关章节...")
    
    if not DOC_78DEGREES.exists():
        logger.error(f"78 Degrees文档不存在: {DOC_78DEGREES}")
        return []
    
    with open(DOC_78DEGREES, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    documents = []
    
    # Chapter 7: How to Use Tarot Readings
    chapter7_start = find_section_start(lines, "Chapter 7")
    chapter7_end = find_section_end(lines, chapter7_start, ["Chapter 8", "What We Learn"])
    
    if chapter7_start > 0:
        chapter7_text = extract_text_section(lines, chapter7_start, chapter7_end)
        if chapter7_text:
            documents.append({
                "chunk_id": "78degrees-how-to-use-readings",
                "text": chapter7_text,
                "source": "78 Degrees of Wisdom - Chapter 7",
                "metadata": {
                    "type": "interpretation",
                    "interpretation_type": "how_to_use",
                    "chapter": "Chapter 7",
                    "title": "How to Use Tarot Readings",
                    "lines": f"{chapter7_start}-{chapter7_end}"
                }
            })
    
    # Chapter 8: What We Learn from Tarot Readings
    chapter8_start = find_section_start(lines, "Chapter 8")
    # 文档结束位置
    chapter8_end = len(lines)
    
    if chapter8_start > 0:
        chapter8_text = extract_text_section(lines, chapter8_start, chapter8_end)
        if chapter8_text:
            documents.append({
                "chunk_id": "78degrees-what-we-learn-readings",
                "text": chapter8_text,
                "source": "78 Degrees of Wisdom - Chapter 8",
                "metadata": {
                    "type": "interpretation",
                    "interpretation_type": "what_we_learn",
                    "chapter": "Chapter 8",
                    "title": "What We Learn from Tarot Readings",
                    "lines": f"{chapter8_start}-{chapter8_end}"
                }
            })
    
    logger.info(f"提取了 {len(documents)} 个解读文档块")
    return documents


def main():
    """主函数：提取所有占卜方法和解读相关内容"""
    logger.info("开始提取78 Degrees of Wisdom文档中的占卜方法和解读相关内容...")
    
    all_documents = []
    
    # 1. 提取占卜方法
    all_documents.extend(extract_divination_methods())
    
    # 2. 提取解读章节
    all_documents.extend(extract_interpretation_chapters())
    
    # 保存到JSON文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / "78degrees_methods_and_interpretation.json"
    
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

