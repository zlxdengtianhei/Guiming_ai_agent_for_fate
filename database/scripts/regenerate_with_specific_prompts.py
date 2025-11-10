#!/usr/bin/env python3
"""
使用专属 Prompts 重新生成指定的塔罗牌图片脚本
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
scripts_dir = Path(__file__).parent
sys.path.insert(0, str(scripts_dir))
from generate_all_cards_gpt5_mini import GPT5ImageGenerator, number_to_roman

# 加载环境变量
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️  警告: .env 文件不存在，使用环境变量")

# 配置日志
log_file_path = project_root / 'card_generation_specific.log'
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


# 专属 Prompts 字典（小阿卡纳牌）
SPECIFIC_MINOR_PROMPTS = {
    "Five of Swords": "A disdainful man looks after two retreating and dejected figures. Their swords lie upon the ground. He carries two others on his left shoulder, and a third sword is in his right hand, point to earth. He is the master in possession of the field. CRITICAL: The image must clearly and prominently show exactly 5 swords. The arrangement of the swords is crucial: two swords lie on the ground near the retreating figures, the disdainful man holds two swords on his left shoulder, and he holds one more sword in his right hand, with its point towards the ground. All 5 swords must be distinctly visible and countable.",
    
    "Five of Wands": "A posse of youths, who are brandishing staves, as if in sport or strife. It is mimic warfare. CRITICAL: The image must clearly and prominently show a group of youths brandishing exactly 5 wands (staves or rods) in total. The youths are engaged in a dynamic, chaotic scene that resembles a playful fight or competition. All 5 wands must be distinctly visible and countable, actively used by the figures in their brandishing gestures.",
    
    "Five of Cups": "A dark, cloaked figure, looking sideways at three prone cups two others stand upright behind him; a bridge is in the background, leading to a small keep or holding. CRITICAL: The image must clearly and prominently show exactly 5 cups (chalices or goblets). The arrangement of the cups is crucial: three cups are overturned and lying prone in front of the cloaked figure, while two other cups are standing upright behind the figure. All 5 cups must be distinctly visible and countable, with the distinction between the fallen and standing cups being very clear.",
    
    "Nine of Swords": "One seated on her couch in lamentation, with the swords over her. She is as one who knows no sorrow which is like unto hers. It is a card of utter desolation. CRITICAL: The image must clearly and prominently show exactly 9 swords. The arrangement of the swords is crucial: all 9 swords are positioned horizontally above the lamenting figure, as if hanging in the air or mounted on the wall behind the couch. They should form a distinct, orderly row or pattern. All 9 swords must be distinctly visible and countable.",
    
    "Seven of Cups": "Strange chalices of vision, but the images are more especially those of the fantastic spirit. CRITICAL: The image must clearly and prominently show exactly 7 cups (chalices or goblets). These cups are presented as \"chalices of vision,\" meaning each cup should contain or project a different fantastic, dreamlike, or symbolic image. The 7 cups and the visions they hold are the central focus of the scene. All 7 cups must be distinctly visible and countable.",
    
    "Seven of Pentacles": "A young man, leaning on his staff, looks intently at seven pentacles attached to a clump of greenery on his right; one would say that these were his treasures and that his heart was there. CRITICAL: The image must clearly and prominently show exactly 7 pentacles (coins or disks). The arrangement is crucial: all 7 pentacles are attached to a single clump of greenery (like a bush or plant), which is located to the right side of the young man. The young man is depicted leaning on his staff and looking intently at this group of 7 pentacles. All 7 pentacles must be distinctly visible and countable.",
    
    "Six of Cups": "Children in an old garden, their cups filled with flowers. CRITICAL: The image must clearly and prominently show exactly 6 cups (chalices or goblets). The scene depicts children in an old garden, and all 6 cups are filled with flowers. The cups can be held by the children or placed around them, but the presence of flowers within each of the 6 cups is a mandatory element. All 6 cups must be distinctly visible and countable.",
    
    "Six of Swords": "A ferryman carrying passengers in his punt to the further shore. The course is smooth, and seeing that the freight is light, it may be noted that the work is not beyond his strength. CRITICAL: The image must clearly and prominently show exactly 6 swords. The arrangement of the swords is crucial: all 6 swords are standing upright in the front part of the punt (boat), blade-down. They are part of the cargo being transported by the ferryman along with the passengers. All 6 swords must be distinctly visible and countable.",
    
    "Six of Wands": "A laurelled horseman bears one staff adorned with a laurel crown; footmen with staves are at his side. CRITICAL: The image must clearly and prominently show exactly 6 wands (staves or rods). The arrangement of the wands is crucial: one wand, adorned with a laurel crown, is held by the horseman. The other 5 wands are held by the footmen who are walking alongside the horse. All 6 wands must be distinctly visible and countable.",
    
    "Ten of Cups": "Appearance of Cups in a rainbow; it is contemplated in wonder and ecstacy by a man and woman below, evidently husband and wife. His right arm is about her; his left is raised upward; she raises her right arm. The two children dancing near them have not observed the prodigy but are happy after their own manner. There is a home-scene beyond. CRITICAL: The image must clearly and prominently show exactly 10 cups (chalices or goblets). The arrangement of the cups is crucial: all 10 cups appear together in the sky, arranged in the arc of a rainbow. Below, a man and woman are looking up at this rainbow of cups in wonder. All 10 cups must be distinctly visible and countable within the rainbow formation.",
    
    "Ten of Swords": "A prostrate figure, pierced by swords. CRITICAL: The image must clearly and prominently show exactly 10 swords. The arrangement of the swords is crucial: 8 swords are piercing the back of a single prostrate (lying face down) figure. The figure also holds one sword in each hand, for a total of 10. The hilts of the two swords held in the hands should be detailed and clearly visible. All 10 swords must be distinctly visible and countable.",
    
    "Ten of Wands": "A man oppressed by the weight of the staves which he is carrying. CRITICAL: The image must clearly and prominently show exactly 10 wands (staves or rods). The arrangement of the wands is crucial: 8 wands are strapped to the back of a single man who is shown to be oppressed and burdened by their weight. He also holds one wand in each hand, for a total of 10. The tops or heads of the two wands held in the hands should be detailed and clearly visible. All 10 wands must be distinctly visible and countable.",
}


def build_major_arcana_prompt(description: str, card_name_en: str, card_number: int) -> str:
    """
    构建大阿卡纳牌的 prompt
    
    Args:
        description: 卡牌描述
        card_name_en: 卡牌英文名
        card_number: 卡牌编号
    
    Returns:
        完整的 prompt 字符串
    """
    # 基础风格描述
    original_style_prompt = "Tarot card illustration with a light, thin border, in a highly abstract, mystical, and fantastical 2D art style. Features stylized and symbolic figures, avoiding any realistic human features. The scene is imbued with a surreal, dreamlike quality and a magical, arcane atmosphere. The composition seamlessly fuses geometric patterns, esoteric symbols, and otherworldly elements, while maintaining a moderate complexity and a clear, balanced structure. Use minimal yet dramatic lighting to create an ethereal glow. The emphasis is on symbolic representation to evoke a sense of wonder, fantasy, and profound mystery."
    
    # 新的风格描述
    new_style_prompt = "The overall style is deep blue, with other colors used as accents. The outer border of the card is yellow with very low saturation, making it subtle and barely noticeable."
    
    # 罗马数字
    roman_num = number_to_roman(card_number)
    
    # 文字说明（添加黄色要求）
    text_instruction = f"Important: At the top center of the card, display only the Roman numeral '{roman_num}'. At the bottom center, display only the text '{card_name_en}' in yellow color. The image should have a light, thin border. Do not include any other text, letters, or numbers anywhere else in the image."
    
    # 组合完整的 prompt
    parts = [description, original_style_prompt, new_style_prompt, text_instruction]
    full_prompt = " ".join(filter(None, parts))
    
    return full_prompt


def build_minor_arcana_prompt(specific_prompt: str, card_name_en: str, card_number: int) -> str:
    """
    构建小阿卡纳牌的 prompt（使用专属prompt）
    
    Args:
        specific_prompt: 专属的prompt（包含描述和数量指令）
        card_name_en: 卡牌英文名
        card_number: 卡牌编号
    
    Returns:
        完整的 prompt 字符串
    """
    # 基础风格描述
    original_style_prompt = "Tarot card illustration with a light, thin border, in a highly abstract, mystical, and fantastical 2D art style. Features stylized and symbolic figures, avoiding any realistic human features. The scene is imbued with a surreal, dreamlike quality and a magical, arcane atmosphere. The composition seamlessly fuses geometric patterns, esoteric symbols, and otherworldly elements, while maintaining a moderate complexity and a clear, balanced structure. Use minimal yet dramatic lighting to create an ethereal glow. The emphasis is on symbolic representation to evoke a sense of wonder, fantasy, and profound mystery."
    
    # 新的风格描述
    new_style_prompt = "The overall style is deep blue, with other colors used as accents. The outer border of the card is yellow with very low saturation, making it subtle and barely noticeable."
    
    # 罗马数字
    roman_num = number_to_roman(card_number)
    
    # 文字说明（添加黄色要求）
    text_instruction = f"Important: At the top center of the card, display only the Roman numeral '{roman_num}'. At the bottom center, display only the text '{card_name_en}' in yellow color. The image should have a light, thin border. Do not include any other text, letters, or numbers anywhere else in the image."
    
    # 组合完整的 prompt
    parts = [specific_prompt, original_style_prompt, new_style_prompt, text_instruction]
    full_prompt = " ".join(filter(None, parts))
    
    return full_prompt


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
        stem = img_file.stem
        parts = stem.split("_")
        
        image_number = None
        if len(parts) > 1:
            try:
                image_number = int(parts[-1])
            except ValueError:
                pass
        
        if image_number is None:
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


def regenerate_with_specific_prompts(card_names: List[str], num_images: int = 2):
    """
    使用专属 prompts 重新生成指定的卡牌图片
    
    Args:
        card_names: 要重新生成的卡牌名称列表
        num_images: 每张卡牌生成的图片数量（默认2张）
    """
    logger.info("="*60)
    logger.info("使用专属 Prompts 重新生成指定的塔罗牌图片")
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
            if is_major_arcana:
                # 大阿卡纳牌：使用标准构建方式
                full_prompt = build_major_arcana_prompt(description, card_name_en, card_number)
                logger.info(f"📝 使用大阿卡纳标准 prompt")
            else:
                # 小阿卡纳牌：使用专属 prompt
                specific_prompt = SPECIFIC_MINOR_PROMPTS.get(card_name_en)
                if specific_prompt:
                    full_prompt = build_minor_arcana_prompt(specific_prompt, card_name_en, card_number)
                    logger.info(f"📝 使用专属 prompt")
                else:
                    logger.warning(f"⚠️  未找到专属 prompt，跳过: {card_name_en}")
                    skipped_count += 1
                    continue
            
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
            import base64
            
            if isinstance(result, dict):
                images_base64 = []
                
                # 处理多张图片的情况
                if result.get("type") == "base64_multiple":
                    images_base64 = result.get("b64_json_list", [])
                # 处理单张图片的情况
                elif result.get("type") == "base64":
                    images_base64 = [result.get("b64_json")]
                
                if images_base64:
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
            else:
                logger.error(f"❌ 返回数据格式错误")
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
        # 小阿卡纳牌（使用专属prompts）
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
        # 大阿卡纳牌（使用标准prompt）
        "The Last Judgment",
        "Wheel of Fortune",
    ]
    
    import argparse
    parser = argparse.ArgumentParser(description="使用专属 Prompts 重新生成指定的塔罗牌图片")
    parser.add_argument("--num", type=int, default=2, help="每张卡牌生成的图片数量（默认2张）")
    parser.add_argument("--cards", nargs="+", default=None, help="要重新生成的卡牌名称列表（默认使用内置列表）")
    
    args = parser.parse_args()
    
    # 如果指定了卡牌列表，使用指定的；否则使用内置列表
    card_list = args.cards if args.cards else cards_to_regenerate
    
    regenerate_with_specific_prompts(card_list, num_images=args.num)

