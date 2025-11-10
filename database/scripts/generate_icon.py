#!/usr/bin/env python3
"""
使用 GPT-5 Image Mini 生成占卜代理图标
生成一个包含太极、无限循环和眼睛的图标
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional

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
log_file_path = project_root / 'icon_generation.log'
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
    
    def generate_image(self, prompt: str, **kwargs):
        """
        生成图片（使用 Responses API）
        
        Args:
            prompt: 文本提示词
            **kwargs: 额外参数
                - size: 图片尺寸，支持 "1024x1024", "1024x1536", "1536x1024"（默认: "1024x1024"）
                - quality: 图片质量，"low", "medium", "high"（默认: "high"）
                - n: 生成图片数量（默认: 1）
        """
        size = kwargs.get("size", "1024x1024")  # 图标使用正方形
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
            
            # 从响应中提取图片数据
            image_data = [
                output.result
                for output in response.output
                if output.type == "image_generation_call"
            ]
            
            if not image_data:
                raise Exception(f"第 {i+1} 张图片生成失败：未找到生成的图片数据")
            
            images_base64.append(image_data[0])
            logger.info(f"   ✅ 第 {i+1}/{n} 张图片生成完成")
        
        # 如果只生成一张，返回单张格式；否则返回多张格式
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
    
    def download_image(self, image_data, save_path: Path) -> bool:
        """保存 base64 图片（支持单张或多张）"""
        import base64
        
        # 处理多张图片的情况
        if isinstance(image_data, dict) and image_data.get("type") == "base64_multiple":
            images_base64 = image_data.get("b64_json_list", [])
            if not images_base64:
                return False
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            # 保存多张图片，文件名添加序号
            base_name = save_path.stem
            extension = save_path.suffix
            parent_dir = save_path.parent
            
            for idx, image_base64 in enumerate(images_base64):
                image_bytes = base64.b64decode(image_base64)
                # 多张图片：添加序号（从1开始）
                multi_path = parent_dir / f"{base_name}_{idx+1}{extension}"
                with open(multi_path, 'wb') as f:
                    f.write(image_bytes)
                logger.info(f"   💾 已保存: {multi_path.name}")
            return True
        
        # 处理单张图片的情况
        image_base64 = image_data.get("b64_json") if isinstance(image_data, dict) else image_data
        if not image_base64:
            return False
        
        image_bytes = base64.b64decode(image_base64)
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"   💾 已保存: {save_path.name}")
        return True


def generate_icon(
    prompt: str,
    output_dir: Path,
    num_variations: int = 3
):
    """
    生成图标
    
    Args:
        prompt: 图标描述提示词
        output_dir: 输出目录
        num_variations: 生成几个变体（默认3个）
    """
    logger.info("="*60)
    logger.info("生成占卜代理图标 - GPT-5 Image Mini")
    logger.info("="*60)
    
    # 初始化 GPT-5 Image Mini 生成器
    try:
        generator = GPT5ImageGenerator(model="gpt-5-mini")
        logger.info("✅ GPT-5 Image Mini 生成器初始化成功")
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        return
    
    # 准备输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 图片保存目录: {output_dir}")
    
    logger.info("")
    logger.info("="*60)
    logger.info("开始生成图标")
    logger.info("="*60)
    logger.info(f"📝 Prompt: {prompt}")
    logger.info(f"📤 生成 {num_variations} 个变体...")
    
    try:
        # 生成图片
        result = generator.generate_image(
            prompt=prompt,
            size="1536x1024",  # 横屏格式 (3:2 比例)
            quality="high",
            n=num_variations
        )
        
        # 保存图片
        base_filename = "tarot_card_illustration.png"
        save_path = output_dir / base_filename
        
        if generator.download_image(result, save_path):
            # 统计保存的图片数量
            saved_images = list(output_dir.glob("*.png"))
            logger.info(f"✅ 成功！已保存 {len(saved_images)} 张图片到: {output_dir}")
            
            # 列出所有保存的文件
            for img in saved_images:
                logger.info(f"   📄 {img.name}")
        else:
            logger.error(f"❌ 保存失败")
    
    except Exception as e:
        logger.error(f"❌ 处理失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("")
    logger.info("="*60)
    logger.info("处理完成")
    logger.info("="*60)
    logger.info(f"📁 图片保存目录: {output_dir}")


if __name__ == "__main__":
    import argparse
    
    # 默认提示词
    default_prompt = (
        "A Tarot card illustration featuring a split composition. On the left side, a female Tarot reader is depicted in primary blue tones. Her background is predominantly deep blue, adorned with shimmering golden Tarot elements and esoteric symbols. On the right side, an ancient Chinese sage in a traditional golden robe is depicted. His background is primarily a warm yellow hue, embellished with elegant blue Chinese-style elements and patterns. "
        "The overall art style is highly abstract, mystical, and fantastical 2D. Both figures are stylized and symbolic, intentionally avoiding any realistic human features. The scene is imbued with a surreal, dreamlike quality and a magical, arcane atmosphere. The composition seamlessly fuses geometric patterns and otherworldly elements, while maintaining a moderate complexity and a clear, balanced structure. "
        "The overall color palette is dominated by deep blue, with gold and yellow used as significant accents. Lighting is minimal yet dramatic, creating an ethereal glow that highlights the figures and symbols. The entire card is framed by a very subtle, thin, and barely noticeable outer border of low-saturation yellow. The emphasis is on symbolic representation to evoke a sense of wonder, fantasy, and profound mystery. "
        "IMPORTANT: The two figures (the female Tarot reader and the ancient Chinese sage) should occupy only half of the vertical height of the composition. They should be positioned in a way that they take up approximately 1/2 of the vertical edge height, leaving the other half of the vertical space for other elements or background."
    )
    
    parser = argparse.ArgumentParser(description="使用 GPT-5 Image Mini 生成占卜代理图标")
    parser.add_argument("--prompt", type=str, default=default_prompt, help="图标描述提示词")
    parser.add_argument("--output-dir", type=str, default=None, help="输出目录（默认: profile）")
    parser.add_argument("--num-variations", type=int, default=3, help="生成几个变体（默认: 3）")
    
    args = parser.parse_args()
    
    # 确定输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # 默认输出到项目根目录的 profile 文件夹
        output_dir = project_root / "profile"
    
    generate_icon(
        prompt=args.prompt,
        output_dir=output_dir,
        num_variations=args.num_variations
    )

