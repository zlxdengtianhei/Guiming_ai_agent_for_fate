#!/usr/bin/env python3
"""
为特定的几张大阿卡纳牌（The Lovers, The Star, The Sun）生成图像，
使用经过特别优化的、更谨慎的prompt，以避免被安全系统拒绝。
"""

import os
import sys
import json
import time
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import openai
except ImportError:
    print("❌ 需要安装 openai 库")
    print("   运行: pip install openai")
    sys.exit(1)

# --- 基本设置 ---
project_root = Path(__file__).parent.parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

# 加载环境变量
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# 配置日志
log_file_path = project_root / 'specific_card_generation.log'
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

# --- 工具函数 ---

def get_openai_org_id() -> Optional[str]:
    return os.getenv("OPENAI_ORG_ID", "").strip() or None

def number_to_roman(num: int) -> str:
    if num == 0: return "0"
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

# --- 核心类和函数 ---

class GPT5ImageGenerator:
    """OpenAI GPT-5 Image Mini 生成器"""
    def __init__(self, model: str = "gpt-5-mini"):
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("需要设置 OPENAI_API_KEY 环境变量")
        
        org_id = get_openai_org_id()
        client_kwargs = {"api_key": api_key}
        if org_id:
            client_kwargs["organization"] = org_id
        
        self.client = openai.OpenAI(**client_kwargs)
        self.model = model

    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
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
                tools=[{"type": "image_generation", "size": size, "quality": quality}]
            )
            
            image_data = next((o.result for o in response.output if o.type == "image_generation_call"), None)
            
            if not image_data:
                raise Exception(f"第 {i+1} 张图片生成失败：未找到生成的图片数据")
            
            images_base64.append(image_data)
            logger.info(f"   ✅ 第 {i+1}/{n} 张图片生成完成")

        if n == 1:
            return {"b64_json": images_base64[0], "type": "base64"}
        else:
            return {"b64_json_list": images_base64, "type": "base64_multiple", "count": len(images_base64)}

    def download_image(self, image_data: Any, save_path_base: Path) -> bool:
        import base64
        
        images_base64 = []
        if isinstance(image_data, dict) and image_data.get("type") == "base64_multiple":
            images_base64 = image_data.get("b64_json_list", [])
        elif isinstance(image_data, dict) and image_data.get("type") == "base64":
             images_base64.append(image_data.get("b64_json"))

        if not images_base64:
            logger.error("   ❌ 下载失败：没有找到图片数据。")
            return False
        
        parent_dir = save_path_base.parent
        base_name = save_path_base.name
        parent_dir.mkdir(parents=True, exist_ok=True)
        
        # 确定新文件的起始编号
        existing_images = list(parent_dir.glob(f"{base_name}_*.png"))
        start_index = len(existing_images) + 1
        
        for i, image_b64 in enumerate(images_base64):
            if not image_b64: continue
            try:
                image_bytes = base64.b64decode(image_b64)
                new_index = start_index + i
                multi_path = parent_dir / f"{base_name}_{new_index}.png"
                with open(multi_path, 'wb') as f:
                    f.write(image_bytes)
                logger.info(f"   💾 已保存: {multi_path.name}")
            except Exception as e:
                logger.error(f"   ❌ 保存第 {i+1} 张图片时出错: {e}")
        return True

def cautious_optimize_description(card_name_en: str) -> str:
    """
    为特定卡片创建极其谨慎的描述，以避免安全策略问题。
    """
    if card_name_en == "The Lovers":
        logger.info("    (使用 The Lovers 的新版高度谨慎 prompt)")
        return (
            "In a symbolic garden under a bright sun, a magnificent winged entity bestows a blessing from above. "
            "The scene is defined by two prominent trees: one is an apple tree with a serpent coiled around its trunk, representing knowledge and choices. "
            "The other is a tree of vibrant flames, symbolizing passion and vitality. At the center, two streams of energy, one golden (solar) and one silver (lunar), "
            "flow and intertwine, representing the harmonious union of duality. The overall image is an allegory for a pivotal choice, "
            "balance, and the powerful connection of complementary forces. The atmosphere is one of purity and profound spiritual significance."
        )
    
    elif card_name_en == "The Star":
        logger.info("    (使用 The Star 的超安全抽象版 prompt)")
        return (
            "The night sky is dominated by a magnificent central star with eight brilliant rays, "
            "surrounded by seven smaller stars, each also displaying eight rays, forming a celestial constellation pattern. "
            "At the center of the composition, a radiant form of pure light and energy manifests as an abstract, flowing shape "
            "positioned at the boundary between land and water—one part touches the earth, another extends into the water. "
            "Two large, ornate ewers float in the air, pouring streams of luminous Water of Life: one stream cascades onto the land, "
            "the other flows into the sea, symbolizing the nourishment and renewal of all creation. "
            "The entire scene is composed of light, energy, and symbolic elements rather than human forms. "
            "In the background, a small bird perches on a tree branch, symbolizing the soul's journey toward higher realms. "
            "The composition radiates with a sense of peace, hope, renewal, and profound spiritual inspiration. "
            "All elements are highly stylized, abstract, and symbolic, focusing on the celestial and elemental forces rather than physical forms."
        )

    elif card_name_en == "The Sun":
        logger.info("    (使用 The Sun 的高度谨慎 prompt)")
        return (
            "A joyful child, symbolizing innocence and new beginnings, is featured prominently on a gentle white horse. "
            "The child holds a vibrant red banner, representing action and passion. "
            "Above, a glorious, personified sun shines down with benevolent rays upon the scene. "
            "In the background, a simple wall stands, from which the child has emerged, signifying a departure from the past. "
            "This card represents happiness, contentment, and the dawning of a higher consciousness."
        )
    return ""

def build_prompt(description: str, card_name_en: str, card_number: int) -> str:
    """构建最终的 prompt"""
    # 基础风格描述
    original_style_prompt = (
        "Tarot card illustration with a light, thin border, in a highly abstract, mystical, and fantastical 2D art style. "
        "Features stylized and symbolic figures, avoiding any realistic human features. The scene is imbued with a surreal, dreamlike quality and a magical, arcane atmosphere. "
        "The composition seamlessly fuses geometric patterns, esoteric symbols, and otherworldly elements, while maintaining a moderate complexity and a clear, balanced structure. "
        "Use minimal yet dramatic lighting to create an ethereal glow. The emphasis is on symbolic representation to evoke a sense of wonder, fantasy, and profound mystery."
    )
    
    # 颜色风格描述
    new_style_prompt = (
        "The overall style is deep blue, with other colors used as accents. "
        "The outer border of the card is yellow with very low saturation, making it subtle and barely noticeable."
    )

    # 数字象征意义
    number_symbolism = ""
    if card_name_en == "The Lovers":
        number_symbolism = "This card is numbered VI, reflecting harmony, union, and balance."
    elif card_name_en == "The Star":
        number_symbolism = "This card is numbered XVII, symbolizing hope, inspiration, and celestial guidance."
    elif card_name_en == "The Sun":
        number_symbolism = "This card is numbered XIX, representing success, new beginnings, and enlightenment."
    
    roman_num = number_to_roman(card_number)
    text_instruction = (
        f"Important: At the top center of the card, display only the Roman numeral '{roman_num}'. "
        f"At the bottom center, display only the text '{card_name_en}'. "
        "Do not include any other text, letters, or numbers anywhere else."
    )
    
    final_description = f"{number_symbolism} {description}"
    return " ".join([final_description, original_style_prompt, new_style_prompt, text_instruction])

def generate_specific_cards():
    """主函数，生成指定的卡片"""
    target_cards = ["The Star"]  # 只处理 The Star
    
    logger.info("="*60)
    logger.info("为特定卡片生成图像（高度谨慎模式）")
    logger.info(f"目标卡片: {', '.join(target_cards)}")
    logger.info("="*60)
    
    try:
        generator = GPT5ImageGenerator()
    except Exception as e:
        logger.error(f"❌ 初始化生成器失败: {e}")
        return

    json_path = project_root / "database" / "data" / "pkt_tarot_cards.json"
    if not json_path.exists():
        logger.error(f"❌ 卡片数据文件不存在: {json_path}")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        all_cards = json.load(f)
    card_dict = {card.get("card_name_en"): card for card in all_cards}
    
    output_base_dir = project_root / "database" / "images"

    for card_name in target_cards:
        card_data = card_dict.get(card_name)
        if not card_data:
            logger.warning(f"⚠️  在JSON数据中未找到卡片: {card_name}，跳过")
            continue

        logger.info("\n" + "="*50)
        logger.info(f"处理卡片: {card_name}")
        logger.info("="*50)

        description = cautious_optimize_description(card_name)
        
        full_prompt = build_prompt(
            description=description,
            card_name_en=card_data.get("card_name_en", ""),
            card_number=card_data.get("card_number", 0)
        )
        
        logger.info(f"   Prompt 长度: {len(full_prompt)} 字符")

        try:
            logger.info("   📤 开始生成 2 张图片...")
            result = generator.generate_image(prompt=full_prompt, n=2)
            logger.info("   ✅ 2 张图片生成完毕")
            
            safe_name = card_name.replace(" ", "_").replace("'", "")
            card_dir = output_base_dir / safe_name
            save_path_base = card_dir / safe_name

            logger.info(f"   📥 下载并保存图片到: {card_dir}")
            if generator.download_image(result, save_path_base):
                logger.info(f"   ✅ 图片保存成功！")
            else:
                logger.error("   ❌ 图片保存失败。")

        except Exception as e:
            logger.error(f"❌ 处理卡片 {card_name} 时发生错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        logger.info("   ⏸️  等待 2 秒...")
        time.sleep(2)
        
    logger.info("\n" + "="*60)
    logger.info("所有指定卡片处理完成。")
    logger.info("="*60)

if __name__ == "__main__":
    generate_specific_cards()
