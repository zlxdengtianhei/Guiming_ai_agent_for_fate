#!/usr/bin/env python3
"""
脚本：处理 pkt.txt 文件并准备 RAG 数据
将文本文件分割成适合 RAG 的文档块
"""

import re
import logging
from typing import List, Dict, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    清理文本，移除多余空白和格式问题
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文本
    """
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text)
    # 移除开头的空白
    text = text.strip()
    return text


def split_into_sections(text: str) -> List[str]:
    """
    将文本分割成有意义的章节
    
    Args:
        text: 完整文本
        
    Returns:
        章节列表
    """
    sections = []
    
    # 尝试按多个换行符分割（段落）
    paragraphs = re.split(r'\n\s*\n+', text)
    
    current_section = []
    min_section_length = 200  # 最小章节长度（字符）
    
    for para in paragraphs:
        para = clean_text(para)
        
        # 跳过太短的段落
        if len(para) < 50:
            continue
        
        # 如果当前章节加上这个段落太长，先保存当前章节
        if current_section and len(' '.join(current_section)) + len(para) > 2000:
            section_text = ' '.join(current_section)
            if len(section_text) >= min_section_length:
                sections.append(section_text)
            current_section = [para]
        else:
            current_section.append(para)
    
    # 添加最后一个章节
    if current_section:
        section_text = ' '.join(current_section)
        if len(section_text) >= min_section_length:
            sections.append(section_text)
    
    return sections


def extract_card_names(text: str) -> Dict[str, str]:
    """
    尝试从文本中提取卡牌名称（用于元数据）
    
    Args:
        text: 文本内容
        
    Returns:
        包含卡牌名称的字典（如果找到）
    """
    metadata = {}
    
    # 常见的大阿卡纳名称模式
    major_arcana_patterns = [
        r'(?:THE\s+)?(?:FOOL|MAGICIAN|HIGH\s+PRIESTESS|EMPRESS|EMPEROR|HIEROPHANT|LOVERS|CHARIOT|STRENGTH|HERMIT|WHEEL\s+OF\s+FORTUNE|JUSTICE|HANGED\s+MAN|DEATH|TEMPERANCE|DEVIL|TOWER|STAR|MOON|SUN|JUDGEMENT|WORLD)',
        # 小阿卡纳
        r'(?:ACE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|PAGE|KNIGHT|QUEEN|KING)\s+OF\s+(?:WANDS|CUPS|SWORDS|PENTACLES)',
    ]
    
    for pattern in major_arcana_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            card_name = match.group(0).strip()
            metadata['card_name'] = card_name
            break
    
    return metadata


def process_pkt_file(file_path: str) -> List[Dict[str, Any]]:
    """
    处理 pkt.txt 文件，将其转换为 RAG 文档格式
    
    Args:
        file_path: pkt.txt 文件路径
        
    Returns:
        文档列表，每个文档包含 text, source, chunk_id, metadata
    """
    file_path_obj = Path(file_path)
    
    if not file_path_obj.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    logger.info(f"读取文件: {file_path}")
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    logger.info(f"文件大小: {len(content)} 字符")
    
    # 分割成章节
    sections = split_into_sections(content)
    logger.info(f"分割成 {len(sections)} 个章节")
    
    # 转换为文档格式
    documents = []
    source = "pkt.txt"
    
    for i, section_text in enumerate(sections, 1):
        # 提取元数据（如果有卡牌名称）
        metadata = extract_card_names(section_text)
        metadata['section_number'] = i
        metadata['source_file'] = 'pkt.txt'
        
        # 创建文档
        doc = {
            'text': section_text,
            'source': source,
            'chunk_id': f"pkt-section-{i:04d}",
            'metadata': metadata
        }
        documents.append(doc)
    
    logger.info(f"处理完成，生成了 {len(documents)} 个文档")
    return documents


def save_documents_json(documents: List[Dict[str, Any]], output_path: str = None) -> str:
    """保存文档为 JSON 文件
    
    Returns:
        保存的文件路径
    """
    import json
    
    # 默认保存到 rag/data/ 目录
    if output_path is None:
        script_dir = Path(__file__).parent
        data_dir = script_dir.parent / "data"
        data_dir.mkdir(exist_ok=True)
        output_path = str(data_dir / "pkt_documents.json")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)
    
    logger.info(f"文档已保存到: {output_path}")
    return output_path


def main():
    """主函数"""
    import sys
    
    # 默认文件路径
    default_path = "/Users/lexuanzhang/code/tarot_agent/pkt.txt"
    
    # 允许命令行参数指定文件路径
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = default_path
    
    logger.info("=" * 60)
    logger.info("PKT 文件处理脚本")
    logger.info("=" * 60)
    
    try:
        # 处理文件
        documents = process_pkt_file(file_path)
        
        # 保存为 JSON（默认保存到 rag/data/ 目录）
        output_file = save_documents_json(documents)
        
        # 打印统计信息
        logger.info("\n" + "=" * 60)
        logger.info("处理统计:")
        logger.info(f"  总文档数: {len(documents)}")
        logger.info(f"  总字符数: {sum(len(doc['text']) for doc in documents)}")
        logger.info(f"  平均文档长度: {sum(len(doc['text']) for doc in documents) // len(documents) if documents else 0} 字符")
        
        # 显示示例文档
        if documents:
            logger.info("\n示例文档:")
            sample = documents[0]
            logger.info(f"  Chunk ID: {sample['chunk_id']}")
            logger.info(f"  Source: {sample['source']}")
            logger.info(f"  Metadata: {sample['metadata']}")
            logger.info(f"  文本预览: {sample['text'][:200]}...")
        
        logger.info("\n" + "=" * 60)
        logger.info("下一步:")
        logger.info(f"  1. 检查生成的文档文件")
        logger.info(f"  2. 运行 cd rag/scripts && python upload_to_supabase.py 上传到 Supabase")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"处理失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

