#!/usr/bin/env python3
"""
使用 GPT-5 Image Mini 生成塔罗牌背景图片
生成1张1:1正方形图片，使用递增后缀，跳过已有文件
"""

import os
import sys
import time
import logging
import base64
from pathlib import Path
from typing import Optional, Dict, Any

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
log_file_path = project_root / 'background_generation.log'
# 清除现有的日志配置
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
        import re
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'^OPENAI_ORG_ID=(.+)$', content, re.MULTILINE)
        if match:
            org_id = match.group(1).strip().strip('"').strip("'")
    
    return org_id if org_id else None


class GPT5ImageGenerator:
    """OpenAI GPT-5 Image Mini 生成器（使用 Responses API）"""
    
    def __init__(self, model: str = "gpt-5-mini"):
        """
        初始化 GPT-5 Image 生成器
        
        Args:
            model: 模型名称，默认 "gpt-5-mini"
        """
        if not openai:
            raise ValueError("需要安装 openai 库")
        
        # 尝试从环境变量读取 OPENAI_API_KEY
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        
        # 如果环境变量中没有，尝试直接从 .env 文件读取
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
        
        # 读取 organization ID
        org_id = get_openai_org_id()
        client_kwargs = {"api_key": api_key}
        if org_id:
            client_kwargs["organization"] = org_id
        
        self.client = openai.OpenAI(**client_kwargs)
        self.model = model
    
    def generate_image(self, prompt: str, size: str = "1024x1536", quality: str = "high") -> Dict[str, Any]:
        """
        生成图片（使用 Responses API）
        
        Args:
            prompt: 文本提示词
            size: 图片尺寸，支持 "1024x1024", "1024x1536", "1536x1024"
            quality: 图片质量，"low", "medium", "high"（默认: "high"）
        
        Returns:
            包含 base64 图片数据的字典
        """
        logger.info(f"   📸 正在生成图片 (尺寸: {size})...")
        
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            tools=[{
                "type": "image_generation",
                "size": size,
                "quality": quality
            }]
        )
        
        # 从响应中提取图片数据
        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]
        
        if not image_data:
            raise Exception("图片生成失败：未找到生成的图片数据")
        
        logger.info(f"   ✅ 图片生成完成")
        
        return {
            "b64_json": image_data[0],
            "type": "base64"
        }
    
    def download_image(self, image_data: Dict[str, Any], save_path: Path) -> bool:
        """保存 base64 图片"""
        image_base64 = image_data.get("b64_json")
        if not image_base64:
            return False
        
        image_bytes = base64.b64decode(image_base64)
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"   💾 已保存: {save_path.name}")
        return True


def generate_background_images():
    """生成背景图片"""
    logger.info("="*60)
    logger.info("生成塔罗牌背景图片 - GPT-5 Image Mini")
    logger.info("="*60)
    
    # 初始化 GPT-5 Image Mini 生成器
    try:
        generator = GPT5ImageGenerator(model="gpt-5-mini")
        logger.info("✅ GPT-5 Image Mini 生成器初始化成功")
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        return
    
    # 背景图片提示词
    background_prompt = """Create a seamless background pattern featuring classic tarot elements using highly abstract representation. The primary focus should be on tarot elements and esoteric symbols. The pattern should include stylized icons of swords, cups, wands, and pentacles rendered in an extremely abstract, symbolic manner. Also, incorporate other classic tarot symbols like a radiant sun, a crescent moon, a guiding star, an infinity symbol (lemniscate), and a mystical rose, all represented through highly abstract forms. Add abstract, minimalist symbols for the archetypes of King (a crown), Queen (a diadem), and Knight (a helmet). Include additional esoteric and mystical symbols such as alchemical symbols, sacred geometry patterns, and occult motifs. Decorative ornamental patterns and intricate filigree designs should be secondary, serving as supporting elements that complement but do not overshadow the primary tarot and esoteric symbols. All elements and decorative patterns should be very small in size, creating a dense, complex, and rich composition with many details. All elements should be evenly distributed across the image, creating a balanced and harmonious composition without any overlap. The art style should be a clean, 2D vector illustration with a strong sense of mystery and flowing, curvaceous design. Emphasize flowing curves, organic shapes, and sinuous lines throughout the composition to create a mystical and esoteric feel with pronounced curvilinear elements. All patterns, elements, and decorative ornaments must have low opacity and subtle, barely perceptible colors that blend seamlessly with the background. The elements should not be prominent or stand out, but rather remain subtle and unobtrusive, perfect for use as a background. The overall brightness should be low, with a dim, subdued appearance throughout. The color palette should be minimalist and harmonious, limited to two or three colors in total. IMPORTANT: The background must be completely opaque, not transparent. The main background color is a deep blue with rich saturation, and it must be a solid, opaque color covering the entire image with no transparency whatsoever. Use a muted gold as an accent color for emphasis, but keep it very subtle and low in opacity. The overall effect should be an elegant and symbolic wallpaper, suitable for a tarot-themed background that does not distract from foreground content. Do not include any text, numbers, or human figures."""
    
    # 准备保存目录
    output_dir = project_root / "database" / "images" / "background"
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 图片保存目录: {output_dir}")
    
    # 查找已存在的文件，确定起始编号
    existing_files = sorted(output_dir.glob("background_square*.png"))
    max_number = 0
    used_numbers = set()
    
    for file in existing_files:
        stem = file.stem  # background_square 或 background_square_1
        if stem == "background_square":
            # 无后缀的文件，视为编号0
            used_numbers.add(0)
        elif "_" in stem:
            parts = stem.split("_")
            if len(parts) >= 3 and parts[-1].isdigit():
                num = int(parts[-1])
                used_numbers.add(num)
                max_number = max(max_number, num)
    
    # 生成1张1:1正方形图片，使用递增后缀
    images_to_generate = []
    next_number = max_number + 1
    
    for i in range(1):  # 生成1张
        # 找到下一个未使用的编号
        while next_number in used_numbers:
            next_number += 1
        
        filename = f"background_square_{next_number}.png"
        
        # 再次检查文件是否已存在（双重保险）
        file_path = output_dir / filename
        if file_path.exists():
            logger.info(f"⏭️  文件已存在，跳过: {filename}")
            used_numbers.add(next_number)
            next_number += 1
            continue
        
        images_to_generate.append(("square", "1024x1024", filename))
        used_numbers.add(next_number)
        next_number += 1
    
    if not images_to_generate:
        logger.info("ℹ️  所有文件都已存在，无需生成新图片")
        return
    
    logger.info(f"📋 将生成 {len(images_to_generate)} 张新图片")
    
    success_count = 0
    fail_count = 0
    
    for image_type, size, filename in images_to_generate:
        logger.info("")
        logger.info("="*60)
        logger.info(f"生成 {image_type} 图片 ({size})")
        logger.info("="*60)
        
        try:
            # 生成图片
            logger.info(f"📤 生成图片中...")
            logger.info(f"   Prompt 长度: {len(background_prompt)} 字符")
            
            result = generator.generate_image(
                prompt=background_prompt,
                size=size,
                quality="high"
            )
            
            # 保存图片
            save_path = output_dir / filename
            
            if generator.download_image(result, save_path):
                logger.info(f"✅ 成功！已保存到: {save_path}")
                success_count += 1
            else:
                logger.error(f"❌ 保存失败")
                fail_count += 1
            
            # 避免请求过快，添加延迟
            if image_type != images_to_generate[-1][0]:
                logger.info(f"⏸️  等待 2 秒后生成下一张...")
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
    logger.info(f"📁 图片保存目录: {output_dir}")
    logger.info("="*60)


if __name__ == "__main__":
    generate_background_images()

