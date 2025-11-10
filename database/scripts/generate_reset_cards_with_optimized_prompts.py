#!/usr/bin/env python3
"""
为 reset 标记的卡片生成两次额外图像，并优化特定卡片的 prompt
优化卡片：The Lovers, The Star, The Moon, The Hanged Man
"""

import os
import sys
import json
import time
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Set

try:
    import openai
except ImportError:
    print("❌ 需要安装 openai 库")
    print("   运行: pip install openai")
    sys.exit(1)

# 添加backend目录到路径
project_root = Path(__file__).parent.parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

# 加载环境变量
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️  警告: .env 文件不存在，使用环境变量")

# 配置日志
log_file_path = project_root / 'reset_cards_generation.log'
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
logger.info(f"日志文件路径: {log_file_path}")


def get_openai_org_id() -> Optional[str]:
    """从环境变量或 .env 文件读取 OpenAI Organization ID"""
    org_id = os.getenv("OPENAI_ORG_ID", "").strip()
    
    if not org_id and env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'^OPENAI_ORG_ID=(.+)$', content, re.MULTILINE)
        if match:
            org_id = match.group(1).strip().strip('"').strip("'")
    
    return org_id if org_id else None


def number_to_roman(num: int) -> str:
    """将数字转换为罗马数字"""
    if num == 0:
        return "0"
    
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    
    roman_num = ''
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syb[i]
            num -= val[i]
        i += 1
    return roman_num


class GPT5ImageGenerator:
    """OpenAI GPT-5 Image Mini 生成器（使用 Responses API）"""
    
    def __init__(self, model: str = "gpt-5-mini"):
        """初始化 GPT-5 Image 生成器"""
        if not openai:
            raise ValueError("需要安装 openai 库")
        
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        
        if not api_key:
            import re
            env_file = backend_dir / ".env"
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                match = re.search(r'^OPENAI_API_KEY=(.+)$', content, re.MULTILINE)
                if match:
                    api_key = match.group(1).strip().strip('"').strip("'")
        
        if not api_key:
            raise ValueError(
                "需要设置 OPENAI_API_KEY\n"
                "请在 backend/.env 文件中添加：OPENAI_API_KEY=your_key_here\n"
                "或者设置为系统环境变量：export OPENAI_API_KEY=your_key_here"
            )
        
        org_id = get_openai_org_id()
        client_kwargs = {"api_key": api_key}
        if org_id:
            client_kwargs["organization"] = org_id
        
        self.client = openai.OpenAI(**client_kwargs)
        self.model = model
    
    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成图片（使用 Responses API）"""
        size = kwargs.get("size", "1024x1536")
        quality = kwargs.get("quality", "high")
        n = kwargs.get("n", 1)
        
        images_base64 = []
        for i in range(n):
            if n > 1:
                logger.info(f"   📸 正在生成第 {i+1}/{n} 张图片...")
            
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                tools=[{
                    "type": "image_generation",
                    "size": size,
                    "quality": quality
                }]
            )
            
            image_data = [
                output.result
                for output in response.output
                if output.type == "image_generation_call"
            ]
            
            if not image_data:
                raise Exception(f"第 {i+1} 张图片生成失败：未找到生成的图片数据")
            
            images_base64.append(image_data[0])
            logger.info(f"   ✅ 第 {i+1}/{n} 张图片生成完成")
        
        if n == 1:
            return {
                "b64_json": images_base64[0],
                "type": "base64"
            }
        else:
            return {
                "b64_json_list": images_base64,
                "type": "base64_multiple",
                "count": len(images_base64)
            }
    
    def download_image(self, image_data: Any, save_path: Path) -> bool:
        """保存 base64 图片（支持单张或多张）"""
        import base64
        
        if isinstance(image_data, dict) and image_data.get("type") == "base64_multiple":
            images_base64 = image_data.get("b64_json_list", [])
            if not images_base64:
                return False
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            base_name = save_path.stem
            extension = save_path.suffix
            parent_dir = save_path.parent
            
            for idx, image_base64 in enumerate(images_base64):
                image_bytes = base64.b64decode(image_base64)
                multi_path = parent_dir / f"{base_name}_{idx+1}{extension}"
                with open(multi_path, 'wb') as f:
                    f.write(image_bytes)
                logger.info(f"   💾 已保存: {multi_path.name}")
            return True
        
        image_base64 = image_data.get("b64_json") if isinstance(image_data, dict) else image_data
        if not image_base64:
            return False
        
        import base64
        image_bytes = base64.b64decode(image_base64)
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"   💾 已保存: {save_path.name}")
        return True


def optimize_description(card_name_en: str, original_description: str) -> str:
    """
    优化特定卡片的描述，避免被 OpenAI 拒绝
    
    Args:
        card_name_en: 卡片英文名
        original_description: 原始描述
    
    Returns:
        优化后的描述
    """
    if card_name_en == "The Lovers":
        # 优化：移除 "unveiled" 等可能被拒绝的词汇，改为更抽象的表述
        optimized = original_description.replace(
            "unveiled before each other, as if Adam and Eve when they first occupied the paradise of the earthly body",
            "standing together in harmony, representing the union of complementary forces in a symbolic garden setting"
        ).replace(
            "The figures suggest youth, virginity, innocence and love before it is contaminated by gross material desire",
            "The figures suggest youth, purity, innocence and spiritual love, representing the ideal union of souls"
        )
        return optimized
    
    elif card_name_en == "The Star":
        # 优化：移除 "entirely naked"，改为更抽象的表述
        optimized = original_description.replace(
            "The female figure in the foreground is entirely naked",
            "The female figure in the foreground is depicted in a flowing, ethereal form, symbolizing purity and natural beauty"
        )
        return optimized
    
    elif card_name_en == "The Moon":
        # 优化：移除 "hideous" 等负面词汇，改为更中性的表述
        optimized = original_description.replace(
            "the nameless and hideous tendency which is lower than the savage beast",
            "the mysterious and primal force emerging from the depths, representing the subconscious realm"
        ).replace(
            "It strives to attain manifestation, symbolized by crawling from the abyss of water to the land",
            "It seeks manifestation, symbolized by emerging from the depths of water toward the land"
        )
        return optimized
    
    elif card_name_en == "The Hanged Man":
        # 优化：强调倒吊的姿态
        optimized = original_description.replace(
            "The gallows from which he is suspended",
            "The figure is suspended upside down, hanging by one foot from a living tree"
        ).replace(
            "the figure--from the position of the legs--forms a fylfot cross",
            "the figure hangs inverted, with legs forming a sacred geometric pattern"
        )
        # 添加更明确的倒吊描述
        if "hanging" not in optimized.lower() or "upside down" not in optimized.lower():
            optimized = "A figure hanging upside down by one foot from a living tree. " + optimized
        return optimized
    
    elif card_name_en == "The Sun":
        # 优化：移除 "naked child"，改为更抽象的表述
        optimized = original_description.replace(
            "The naked child mounted on a white horse",
            "A child figure in pure, radiant form mounted on a white horse"
        )
        return optimized
    
    else:
        return original_description


def get_suit_item_name(suit: str, card_number: int) -> str:
    """
    根据花色和数字返回具体的物品名称
    
    Args:
        suit: 花色 (wands, cups, swords, pentacles)
        card_number: 卡牌数字
    
    Returns:
        物品名称（如 "wands", "cups", "swords", "pentacles"）
    """
    suit_mapping = {
        "wands": "wands",
        "cups": "cups", 
        "swords": "swords",
        "pentacles": "pentacles"
    }
    return suit_mapping.get(suit.lower(), suit.lower())


def build_prompt(description: str, card_name_en: str, card_number: int, suit: str, is_major_arcana: bool) -> str:
    """
    构建生成图片的 prompt
    
    Args:
        description: 卡牌描述（已优化）
        card_name_en: 卡牌英文名
        card_number: 卡牌编号
        suit: 卡牌花色
        is_major_arcana: 是否为大阿卡纳牌
    
    Returns:
        完整的 prompt 字符串
    """
    # 基础风格描述
    original_style_prompt = "Tarot card illustration with a light, thin border, in a highly abstract, mystical, and fantastical 2D art style. Features stylized and symbolic figures, avoiding any realistic human features. The scene is imbued with a surreal, dreamlike quality and a magical, arcane atmosphere. The composition seamlessly fuses geometric patterns, esoteric symbols, and otherworldly elements, while maintaining a moderate complexity and a clear, balanced structure. Use minimal yet dramatic lighting to create an ethereal glow. The emphasis is on symbolic representation to evoke a sense of wonder, fantasy, and profound mystery."
    
    # 新的风格描述
    new_style_prompt = "The overall style is deep blue, with other colors used as accents. The outer border of the card is yellow with very low saturation, making it subtle and barely noticeable."

    # 判断是否需要罗马数字和数量指令
    need_roman_numeral = False
    text_instruction = ""
    quantity_instruction = ""
    
    if is_major_arcana:
        need_roman_numeral = True
    else:
        if card_number <= 10:
            need_roman_numeral = True
            # 为小阿卡纳牌添加明确的数量说明
            suit_item = get_suit_item_name(suit, card_number)
            quantity_instruction = f"The central theme of the image must clearly and prominently show exactly {card_number} {suit_item}. These {card_number} {suit_item} should be the focal point of the composition, clearly visible and distinctly represented."
    
    # 根据是否需要罗马数字，设置文字说明
    if need_roman_numeral:
        roman_num = number_to_roman(card_number)
        text_instruction = f"Important: At the top center of the card, display only the Roman numeral '{roman_num}'. At the bottom center, display only the text '{card_name_en}'. The image should have a light, thin border. Do not include any other text, letters, or numbers anywhere else in the image."
    else:
        text_instruction = f"Important: At the bottom center of the card, display only the text '{card_name_en}'. The image should have a light, thin border. Do not include any other text, letters, or numbers anywhere else in the image."
    
    # 组合完整的 prompt
    parts = [description, quantity_instruction, original_style_prompt, new_style_prompt, text_instruction]
    
    full_prompt = " ".join(filter(None, parts))
    
    return full_prompt


def parse_selection_md(selection_path: Path) -> Set[str]:
    """
    解析 selection.md 文件，找出标记为 reset 的卡片
    
    Returns:
        reset 卡片名称集合
    """
    reset_cards = set()
    
    if not selection_path.exists():
        logger.warning(f"⚠️  selection.md 文件不存在: {selection_path}")
        return reset_cards
    
    with open(selection_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 跳过表头
    for line in lines[2:]:
        line = line.strip()
        if not line or not line.startswith('|'):
            continue
        
        # 解析表格行：| Card Name | 1 | 2 | 3 | reset |
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 6:
            card_name = parts[1]
            reset_value = parts[5]  # reset 列是第6列（索引5）
            
            if reset_value == "1":
                reset_cards.add(card_name)
    
    return reset_cards


def generate_reset_cards():
    """为 reset 标记的卡片生成图像（优先处理的大阿卡纳牌生成2张，其他生成1张）"""
    logger.info("="*60)
    logger.info("为 reset 标记的卡片生成图像")
    logger.info("="*60)
    
    # 优先处理的大阿卡纳牌列表（生成2张）
    priority_major_cards = {
        "The Lovers",
        "The Sun",
        "The Star",
        "The Hanged Man",
        "The Fool",
        "The Empress",
        "Temperance",
        "Wheel of Fortune",
        "The Last Judgment"
    }
    
    # 初始化 GPT-5 Image Mini 生成器
    try:
        generator = GPT5ImageGenerator(model="gpt-5-mini")
        logger.info("✅ GPT-5 Image Mini 生成器初始化成功")
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        return
    
    # 读取 selection.md
    selection_path = project_root / "database" / "selection.md"
    reset_cards = parse_selection_md(selection_path)
    
    if not reset_cards:
        logger.warning("⚠️  没有找到标记为 reset 的卡片")
        return
    
    logger.info(f"📋 找到 {len(reset_cards)} 张标记为 reset 的卡片")
    
    # 分离优先处理和其他卡片
    priority_cards = []
    other_cards = []
    
    for card_name in reset_cards:
        if card_name in priority_major_cards:
            priority_cards.append(card_name)
        else:
            other_cards.append(card_name)
    
    logger.info(f"⭐ 优先处理的大阿卡纳牌 ({len(priority_cards)} 张，生成2张):")
    for card_name in sorted(priority_cards):
        logger.info(f"   - {card_name}")
    
    logger.info(f"📝 其他 reset 卡片 ({len(other_cards)} 张，生成1张):")
    for card_name in sorted(other_cards):
        logger.info(f"   - {card_name}")
    
    # 读取JSON文件
    json_path = project_root / "database" / "data" / "pkt_tarot_cards.json"
    if not json_path.exists():
        logger.error(f"❌ 文件不存在: {json_path}")
        return
    
    logger.info(f"\n📖 读取卡片数据: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    # 创建卡片名称到卡片对象的映射
    card_dict = {card.get("card_name_en"): card for card in cards}
    
    # 准备保存目录
    output_base_dir = project_root / "database" / "images"
    output_base_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"\n📁 图片保存目录: {output_base_dir}")
    
    # 统计信息
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    # 先处理优先卡片（生成2张）
    all_cards_to_process = [(card_name, 2) for card_name in sorted(priority_cards)] + \
                          [(card_name, 1) for card_name in sorted(other_cards)]
    
    # 处理每张 reset 卡片
    for card_name_en, num_images in all_cards_to_process:
        card = card_dict.get(card_name_en)
        if not card:
            logger.warning(f"⚠️  在 JSON 中未找到卡片: {card_name_en}")
            skipped_count += 1
            continue
        
        card_name_cn = card.get("card_name_cn", "未知")
        card_number = card.get("card_number", 0)
        description = card.get("description", "")
        suit = card.get("suit", "")
        arcana = card.get("arcana", "").lower()
        is_major_arcana = arcana == "major"
        
        logger.info("")
        logger.info("="*60)
        logger.info(f"处理卡片: {card_name_en} ({card_name_cn})")
        logger.info("="*60)
        
        # 优化描述（如果是需要优化的卡片）
        optimized_description = optimize_description(card_name_en, description)
        if optimized_description != description:
            logger.info("✨ 已优化描述以避免被拒绝")
            logger.info(f"   原始: {description[:100]}...")
            logger.info(f"   优化: {optimized_description[:100]}...")
        
        # 为每张卡牌创建子文件夹
        safe_name = card_name_en.replace(" ", "_").replace("'", "").replace("/", "_")
        card_dir = output_base_dir / safe_name
        card_dir.mkdir(parents=True, exist_ok=True)
        
        # 检查已存在的图片数量
        existing_images = list(card_dir.glob("*.png"))
        logger.info(f"📊 当前已有 {len(existing_images)} 张图片")
        
        if not optimized_description:
            logger.warning(f"⚠️  卡片没有描述信息，跳过")
            skipped_count += 1
            continue
        
        try:
            # 构建 prompt
            full_prompt = build_prompt(
                optimized_description,
                card_name_en,
                card_number,
                suit,
                is_major_arcana
            )
            
            logger.info(f"📤 生成 {num_images} 张图片...")
            logger.info(f"   Prompt 长度: {len(full_prompt)} 字符")
            
            # 生成指定数量的图片
            result = generator.generate_image(
                prompt=full_prompt,
                size="1024x1536",
                quality="high",
                n=num_images
            )
            
            # 保存图片
            base_filename = f"{safe_name}.png"
            save_path = card_dir / base_filename
            
            if generator.download_image(result, save_path):
                saved_images = list(card_dir.glob("*.png"))
                logger.info(f"✅ 成功！已保存 {len(saved_images)} 张图片到: {card_dir}")
                success_count += 1
            else:
                logger.error(f"❌ 保存失败")
                fail_count += 1
            
            # 避免请求过快，添加延迟
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
    generate_reset_cards()

