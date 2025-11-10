#!/usr/bin/env python3
"""
重新生成指定的塔罗牌图片脚本
图像编号接着之前的继续
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

# 添加backend目录到路径
project_root = Path(__file__).parent.parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

# 导入生成器类和相关函数
# 需要将当前目录添加到路径
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))
from generate_all_cards_gpt5_mini import GPT5ImageGenerator, build_prompt, number_to_roman

# 加载环境变量
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️  警告: .env 文件不存在，使用环境变量")

# 配置日志
log_file_path = project_root / 'card_generation_new.log'
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file_path), encoding='utf-8'),
        logging.StreamHandler()
    ],
    force=True
)
logger = logging.getLogger(__name__)


def get_next_image_number(card_dir: Path) -> int:
    """
    获取下一个图像编号
    
    Args:
        card_dir: 卡牌目录路径
    
    Returns:
        下一个图像编号（从1开始）
    """
    if not card_dir.exists():
        return 1
    
    # 获取所有PNG图像
    all_images = sorted(card_dir.glob("*.png"))
    
    if not all_images:
        return 1
    
    # 找出最大的编号
    max_number = 0
    for img_file in all_images:
        stem = img_file.stem  # 不含扩展名的文件名
        parts = stem.split("_")
        
        # 尝试从文件名中提取编号（格式：CardName_1.png）
        image_number = None
        if len(parts) > 1:
            try:
                image_number = int(parts[-1])
            except ValueError:
                pass
        
        # 如果文件名格式是 "CardName_1.png"，提取编号
        if image_number is None:
            # 尝试其他格式，如 "CardName1.png"
            for i in range(len(stem) - 1, -1, -1):
                if stem[i].isdigit():
                    try:
                        image_number = int(stem[i:])
                        break
                    except ValueError:
                        pass
        
        if image_number is not None and image_number > max_number:
            max_number = image_number
    
    return max_number + 1


def regenerate_specific_cards(card_names: List[str], num_images: int = 2):
    """
    重新生成指定的卡牌图片
    
    Args:
        card_names: 要重新生成的卡牌名称列表
        num_images: 每张卡牌生成的图片数量（默认2张）
    """
    logger.info("="*60)
    logger.info("重新生成指定的塔罗牌图片")
    logger.info("="*60)
    logger.info(f"目标卡牌: {', '.join(card_names)}")
    logger.info(f"每张卡牌生成 {num_images} 张图片")
    
    # 初始化 GPT-5 Image Mini 生成器
    try:
        generator = GPT5ImageGenerator(model="gpt-5-mini")
        logger.info("✅ GPT-5 Image Mini 生成器初始化成功")
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        return
    
    # 读取JSON文件
    json_path = project_root / "database" / "data" / "pkt_tarot_cards.json"
    if not json_path.exists():
        logger.error(f"❌ 文件不存在: {json_path}")
        return
    
    logger.info(f"📖 读取卡片数据: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    if not cards:
        logger.error("❌ JSON文件为空")
        return
    
    # 创建卡牌名称到卡牌信息的映射
    card_map = {card.get("card_name_en", ""): card for card in cards}
    
    # 准备保存目录
    output_base_dir = project_root / "database" / "images"
    output_base_dir.mkdir(exist_ok=True)
    logger.info(f"📁 图片保存目录: {output_base_dir}")
    
    # 统计信息
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    # 处理每张卡片
    for card_name_en in card_names:
        logger.info("")
        logger.info("="*60)
        logger.info(f"处理卡片: {card_name_en}")
        logger.info("="*60)
        
        # 查找卡牌信息
        card = card_map.get(card_name_en)
        if not card:
            logger.warning(f"⚠️  未找到卡牌: {card_name_en}，跳过")
            skipped_count += 1
            continue
        
        card_name_cn = card.get("card_name_cn", "未知")
        card_number = card.get("card_number", 0)
        description = card.get("description", "")
        suit = card.get("suit", "")
        arcana = card.get("arcana", "").lower()
        is_major_arcana = arcana == "major"
        
        # 获取卡牌在JSON中的索引
        card_index = next((i for i, c in enumerate(cards) if c.get("card_name_en") == card_name_en), 0)
        
        logger.info(f"卡牌编号: {card_number}, 类型: {'大阿卡纳' if is_major_arcana else '小阿卡纳'}")
        logger.info(f"花色: {suit}")
        
        # 为每张卡牌创建子文件夹
        safe_name = card_name_en.replace(" ", "_").replace("'", "").replace("/", "_")
        card_dir = output_base_dir / safe_name
        card_dir.mkdir(exist_ok=True)
        
        # 获取下一个图像编号
        next_number = get_next_image_number(card_dir)
        if next_number == 1:
            logger.info(f"📸 目录中没有现有图像，将从编号 1 开始生成")
        else:
            logger.info(f"📸 当前已有图像编号到: {next_number - 1}")
            logger.info(f"📸 将从编号 {next_number} 开始生成")
        
        if not description:
            logger.warning(f"⚠️  卡牌没有描述信息，跳过")
            skipped_count += 1
            continue
        
        try:
            # 构建 prompt
            full_prompt = build_prompt(description, card_name_en, card_number, suit, is_major_arcana, card_index)
            
            logger.info(f"📤 生成图片中...")
            logger.info(f"   Prompt 长度: {len(full_prompt)} 字符")
            logger.info(f"   开始生成 {num_images} 张图片...")
            
            # 生成图片
            result = generator.generate_image(
                prompt=full_prompt,
                size="1024x1536",  # 2:3 竖屏比例
                quality="high",
                n=num_images
            )
            
            # 保存图片（使用自定义编号）
            if isinstance(result, dict) and result.get("type") == "base64_multiple":
                images_base64 = result.get("b64_json_list", [])
                import base64
                
                saved_count = 0
                for idx, image_base64 in enumerate(images_base64):
                    image_number = next_number + idx
                    filename = f"{safe_name}_{image_number}.png"
                    save_path = card_dir / filename
                    
                    image_bytes = base64.b64decode(image_base64)
                    with open(save_path, 'wb') as f:
                        f.write(image_bytes)
                    
                    logger.info(f"   💾 已保存: {filename}")
                    saved_count += 1
                
                if saved_count > 0:
                    logger.info(f"✅ 成功！已保存 {saved_count} 张图片到: {card_dir}")
                    success_count += 1
                else:
                    logger.error(f"❌ 保存失败")
                    fail_count += 1
            else:
                logger.error(f"❌ 未找到图片数据")
                fail_count += 1
            
            # 避免请求过快，添加延迟
            if card_name_en != card_names[-1]:
                logger.info(f"⏸️  等待 2 秒后处理下一张...")
                time.sleep(2)
        
        except Exception as e:
            logger.error(f"❌ 处理失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            fail_count += 1
    
    # 显示最终统计
    logger.info("")
    logger.info("="*60)
    logger.info("处理完成统计")
    logger.info("="*60)
    logger.info(f"✅ 成功: {success_count} 张")
    logger.info(f"❌ 失败: {fail_count} 张")
    logger.info(f"⏭️  跳过: {skipped_count} 张")
    logger.info(f"📁 图片保存目录: {output_base_dir}")
    logger.info("="*60)


if __name__ == "__main__":
    # 要重新生成的卡牌列表
    cards_to_regenerate = [
        "Five of Swords",
        "Five of Wands",
        "Five of Cups",
        "Nine of Swords",
        "Seven of Cups",
        "Seven of Pentacles",
        "Six of Cups",
        "Six of Swords",
        "Six of Wands",
        "Ten of Cups",
        "Ten of Swords",
        "Ten of Wands",
        "The Last Judgment",
        "Wheel of Fortune",
    ]
    
    import argparse
    parser = argparse.ArgumentParser(description="重新生成指定的塔罗牌图片")
    parser.add_argument("--num", type=int, default=2, help="每张卡牌生成的图片数量（默认2张）")
    parser.add_argument("--cards", nargs="+", default=None, help="要重新生成的卡牌名称列表（默认使用内置列表）")
    
    args = parser.parse_args()
    
    # 如果指定了卡牌列表，使用指定的；否则使用内置列表
    card_list = args.cards if args.cards else cards_to_regenerate
    
    regenerate_specific_cards(card_list, num_images=args.num)

