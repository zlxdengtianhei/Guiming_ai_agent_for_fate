#!/usr/bin/env python3
"""
脚本：将处理后的文档上传到 Supabase RAG 数据库
使用 RAG service 处理文档并生成嵌入向量
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
# 脚本位于 rag/scripts/，需要向上两级到达项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.services.rag import rag_service
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_documents_from_json(file_path: str) -> List[Dict[str, Any]]:
    """
    从 JSON 文件加载文档
    
    Args:
        file_path: JSON 文件路径
        
    Returns:
        文档列表
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        documents = json.load(f)
    
    logger.info(f"从 {file_path} 加载了 {len(documents)} 个文档")
    return documents


async def upload_documents(documents: List[Dict[str, Any]]) -> int:
    """
    上传文档到 Supabase RAG 数据库
    
    Args:
        documents: 文档列表
        
    Returns:
        成功上传的块数量
    """
    logger.info(f"开始上传 {len(documents)} 个文档到 Supabase...")
    
    try:
        # 使用 RAG service 处理文档
        # 这会自动进行分块、生成嵌入向量并存储到数据库
        count = await rag_service.seed_documents(documents)
        
        logger.info(f"✅ 成功上传 {count} 个文档块到 Supabase")
        return count
        
    except Exception as e:
        logger.error(f"❌ 上传失败: {e}", exc_info=True)
        raise


async def get_rag_stats():
    """获取 RAG 数据库统计信息"""
    try:
        stats = await rag_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return {}


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="上传文档到 Supabase RAG 数据库")
    parser.add_argument(
        '--file',
        type=str,
        default=None,
        help='要上传的 JSON 文档文件路径（默认: rag/data/pkt_documents.json）'
    )
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='仅显示统计信息，不上传文档'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Supabase RAG 上传脚本")
    logger.info("=" * 60)
    
    # 检查配置
    logger.info("\n配置检查:")
    logger.info(f"  Supabase URL: {settings.supabase_url}")
    logger.info(f"  OpenAI Embed Model: {settings.openai_embed_model}")
    logger.info(f"  Chunk Size: {settings.rag_chunk_size}")
    logger.info(f"  Chunk Overlap: {settings.rag_chunk_overlap}")
    
    # 显示当前统计信息
    logger.info("\n当前数据库统计:")
    stats = await get_rag_stats()
    if stats:
        logger.info(f"  总块数: {stats.get('total_chunks', 0)}")
        logger.info(f"  唯一来源: {stats.get('unique_sources', 0)}")
        logger.info(f"  最新块: {stats.get('latest_chunk', 'N/A')}")
    else:
        logger.info("  数据库为空或无法连接")
    
    if args.stats_only:
        logger.info("\n仅显示统计信息模式，退出")
        return
    
    # 确定文件路径
    if args.file is None:
        # 默认使用 rag/data/pkt_documents.json
        script_dir = Path(__file__).parent
        data_dir = script_dir.parent / "data"
        file_path = data_dir / "pkt_documents.json"
    else:
        file_path = Path(args.file)
    
    # 检查文件是否存在
    if not file_path.exists():
        logger.error(f"❌ 文件不存在: {file_path}")
        logger.info("请先运行 process_pkt_file.py 生成文档文件")
        sys.exit(1)
    
    try:
        # 加载文档
        logger.info(f"\n加载文档: {file_path}")
        documents = await load_documents_from_json(str(file_path))
        
        if not documents:
            logger.error("❌ 文档列表为空")
            sys.exit(1)
        
        # 验证文档格式
        required_keys = ['text', 'source', 'chunk_id']
        for i, doc in enumerate(documents[:3]):  # 只检查前3个
            missing_keys = [key for key in required_keys if key not in doc]
            if missing_keys:
                logger.error(f"❌ 文档 {i} 缺少必需的键: {missing_keys}")
                sys.exit(1)
        
        logger.info(f"✅ 文档格式验证通过")
        
        # 上传文档
        logger.info("\n开始上传...")
        count = await upload_documents(documents)
        
        # 显示更新后的统计信息
        logger.info("\n更新后的数据库统计:")
        stats = await get_rag_stats()
        if stats:
            logger.info(f"  总块数: {stats.get('total_chunks', 0)}")
            logger.info(f"  唯一来源: {stats.get('unique_sources', 0)}")
            logger.info(f"  最新块: {stats.get('latest_chunk', 'N/A')}")
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 上传完成！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 处理失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

