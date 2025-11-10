#!/usr/bin/env python3
"""
使用 GPT-5 Image Mini 批量生成塔罗牌图片脚本
为 pkt_tarot_cards.json 中每张卡片的 description 生成图片
每个卡牌生成3张图片供挑选
"""

import os
import sys
import json
import time
import logging
import shutil
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

# 配置日志 - 使用绝对路径确保日志文件在项目根目录
log_file_path = project_root / 'card_generation_new.log'
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
    force=True  # Python 3.8+ 支持强制重新配置
)
logger = logging.getLogger(__name__)
logger.info(f"日志文件路径: {log_file_path}")


# 归档配置：根据表格数据，定义哪些卡牌需要归档（跳过生成）
# 格式: {card_name: [selected_image_numbers]}
ARCHIVED_CARDS: Dict[str, List[int]] = {
    "The High Priestess": [1],
    "The Devil": [1],
    "The Last Judgment": [1],
    "The World": [1],
    "Page of Cups": [1],
    "The Emperor": [2],
    "The Hierophant": [2],
    "The Hermit": [2],
    "The Moon": [2],
    "Three of Wands": [2],
    "Page of Wands": [2],
    "The Chariot": [3],
    "Wheel of Fortune": [3],
    "Justice": [3],
    "The Tower": [3],
    "Two of Wands": [3],
    "Seven of Wands": [3],
    "Eight of Wands": [3],
    "Queen of Wands": [3],
}

# 需要重置（删除）的卡牌列表
RESET_CARDS: Set[str] = {
    "The Fool",
    "The Empress",
    "Strength",  # 这个会被重命名为 Fortitude
    "Death",
    "Temperance",
    "Ten of Wands",
}


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


def number_to_roman(num: int) -> str:
    """
    将数字转换为罗马数字
    
    Args:
        num: 阿拉伯数字 (0-21)
    
    Returns:
        罗马数字字符串
    """
    if num == 0:
        return "0"  # 愚人牌特殊处理
    
    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syb = [
        "M", "CM", "D", "CD",
        "C", "XC", "L", "XL",
        "X", "IX", "V", "IV",
        "I"
    ]
    
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
    
    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成图片（使用 Responses API）
        
        Args:
            prompt: 文本提示词
            **kwargs: 额外参数
                - size: 图片尺寸，支持 "1024x1024", "1024x1536", "1536x1024"（默认: "1024x1536"）
                - quality: 图片质量，"low", "medium", "high"（默认: "high"）
                - n: 生成图片数量（默认: 1）
                注意：GPT-5 Image 系列使用 Responses API，一次请求只能生成一张图片
                如需生成多张，需要多次调用
        """
        size = kwargs.get("size", "1024x1536")  # 默认使用竖屏 2:3 比例
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
    
    def download_image(self, image_data: Any, save_path: Path) -> bool:
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
        
        import base64
        image_bytes = base64.b64decode(image_base64)
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"   💾 已保存: {save_path.name}")
        return True


def archive_selected_images(card_name_en: str, selected_numbers: List[int], images_dir: Path, archive_dir: Optional[Path] = None) -> bool:
    """
    归档选中的图像：保留指定编号的图像，删除其他图像，并可选地复制到归档文件夹
    
    Args:
        card_name_en: 卡牌英文名
        selected_numbers: 选中的图像编号列表（如 [1, 2]）
        images_dir: 图像目录路径
        archive_dir: 归档目录路径（可选，如果提供则复制归档图像到此目录）
    
    Returns:
        是否成功归档
    """
    if not images_dir.exists():
        logger.warning(f"⚠️  目录不存在，跳过归档: {images_dir}")
        return False
    
    safe_name = card_name_en.replace(" ", "_").replace("'", "").replace("/", "_")
    card_dir = images_dir / safe_name
    
    if not card_dir.exists():
        logger.warning(f"⚠️  卡牌目录不存在，跳过归档: {card_dir}")
        return False
    
    # 获取所有PNG图像
    all_images = sorted(card_dir.glob("*.png"))
    
    if not all_images:
        logger.warning(f"⚠️  没有找到图像文件，跳过归档: {card_dir}")
        return False
    
    # 确定要保留和删除的文件
    files_to_keep = []
    files_to_delete = []
    
    for img_file in all_images:
        # 提取文件名中的编号（如 "CardName_1.png" -> 1）
        stem = img_file.stem  # 不含扩展名的文件名
        parts = stem.split("_")
        
        # 尝试从文件名中提取编号
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
        
        if image_number in selected_numbers:
            files_to_keep.append(img_file)
        else:
            files_to_delete.append(img_file)
    
    # 复制到归档文件夹（如果指定）
    if archive_dir and files_to_keep:
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_card_dir = archive_dir / safe_name
        archive_card_dir.mkdir(parents=True, exist_ok=True)
        
        for img_file in files_to_keep:
            archive_file = archive_card_dir / img_file.name
            try:
                shutil.copy2(img_file, archive_file)
                logger.info(f"   📦 已复制到归档文件夹: {archive_file.name}")
            except Exception as e:
                logger.error(f"   ❌ 复制到归档文件夹失败 {img_file.name}: {e}")
    
    # 删除不需要的文件
    deleted_count = 0
    for img_file in files_to_delete:
        try:
            img_file.unlink()
            deleted_count += 1
            logger.info(f"   🗑️  已删除: {img_file.name}")
        except Exception as e:
            logger.error(f"   ❌ 删除失败 {img_file.name}: {e}")
    
    logger.info(f"✅ 归档完成: {card_name_en}")
    logger.info(f"   📦 保留: {len(files_to_keep)} 张")
    logger.info(f"   🗑️  删除: {deleted_count} 张")
    if archive_dir:
        logger.info(f"   📁 归档文件夹: {archive_dir / safe_name}")
    
    return True


def cleanup_reset_cards(images_dir: Path, reset_cards: Set[str]) -> int:
    """
    清理需要重置的卡牌文件夹
    
    Args:
        images_dir: 图像目录路径
        reset_cards: 需要重置的卡牌名称集合
    
    Returns:
        删除的文件夹数量
    """
    deleted_count = 0
    
    for card_name in reset_cards:
        safe_name = card_name.replace(" ", "_").replace("'", "").replace("/", "_")
        card_dir = images_dir / safe_name
        
        if card_dir.exists() and card_dir.is_dir():
            try:
                shutil.rmtree(card_dir)
                logger.info(f"🗑️  已删除重置卡牌文件夹: {safe_name}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ 删除失败 {safe_name}: {e}")
    
    return deleted_count


def cleanup_unarchived_cards(images_dir: Path, archived_cards: Dict[str, List[int]], reset_cards: Set[str], all_card_names: List[str]) -> int:
    """
    清理未归档的卡牌文件夹（表格中没有记录的卡牌）
    
    Args:
        images_dir: 图像目录路径
        archived_cards: 已归档的卡牌字典
        reset_cards: 需要重置的卡牌集合
        all_card_names: 所有卡牌名称列表
    
    Returns:
        删除的文件夹数量
    """
    deleted_count = 0
    
    # 创建需要保留的卡牌集合（已归档的卡牌）
    keep_cards = set(archived_cards.keys())
    # 将卡牌名转换为文件夹名格式
    keep_folders = {name.replace(" ", "_").replace("'", "").replace("/", "_") for name in keep_cards}
    
    # 创建重置卡牌的文件夹名集合（这些已经在步骤3中删除了，但这里作为检查）
    reset_folders = {name.replace(" ", "_").replace("'", "").replace("/", "_") for name in reset_cards}
    
    # 遍历所有文件夹
    for card_dir in images_dir.iterdir():
        if not card_dir.is_dir():
            continue
        
        folder_name = card_dir.name
        
        # 跳过归档文件夹本身
        if folder_name == "archived":
            continue
        
        # 跳过已归档的卡牌文件夹
        if folder_name in keep_folders:
            continue
        
        # 跳过重置卡牌文件夹（这些已经在步骤3中处理了）
        if folder_name in reset_folders:
            continue
        
        # 检查是否是已归档卡牌（可能有不同的命名格式，如Fortitude）
        is_archived = False
        for archived_name in archived_cards.keys():
            archived_folder = archived_name.replace(" ", "_").replace("'", "").replace("/", "_")
            if archived_folder == folder_name:
                is_archived = True
                break
        
        if not is_archived:
            # 这是一个未归档的卡牌文件夹，需要删除
            try:
                shutil.rmtree(card_dir)
                logger.info(f"🗑️  已删除未归档卡牌文件夹: {folder_name}")
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ 删除失败 {folder_name}: {e}")
    
    return deleted_count


def rename_strength_to_fortitude(images_dir: Path, json_path: Path) -> bool:
    """
    将 Strength 重命名为 Fortitude
    
    Args:
        images_dir: 图像目录路径
        json_path: JSON文件路径
    
    Returns:
        是否成功重命名
    """
    success = True
    
    # 重命名文件夹
    strength_dir = images_dir / "Strength"
    fortitude_dir = images_dir / "Fortitude"
    
    if strength_dir.exists() and strength_dir.is_dir():
        try:
            if fortitude_dir.exists():
                logger.warning(f"⚠️  Fortitude 文件夹已存在，先删除")
                shutil.rmtree(fortitude_dir)
            strength_dir.rename(fortitude_dir)
            logger.info(f"✅ 文件夹重命名成功: Strength -> Fortitude")
        except Exception as e:
            logger.error(f"❌ 文件夹重命名失败: {e}")
            success = False
    
    # 更新JSON文件
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            cards = json.load(f)
        
        updated = False
        for card in cards:
            if card.get("card_name_en") == "Strength":
                card["card_name_en"] = "Fortitude"
                updated = True
                logger.info(f"✅ JSON中已更新: Strength -> Fortitude")
                break
        
        if updated:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(cards, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ JSON文件已保存")
    except Exception as e:
        logger.error(f"❌ JSON更新失败: {e}")
        success = False
    
    return success


def build_prompt(description: str, card_name_en: str, card_number: int, suit: str, is_major_arcana: bool, card_index: int) -> str:
    """
    构建生成图片的 prompt
    
    Args:
        description: 卡牌描述
        card_name_en: 卡牌英文名
        card_number: 卡牌编号
        suit: 卡牌花色
        is_major_arcana: 是否为大阿卡纳牌
        card_index: 卡牌在JSON中的索引（0开始）
    
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
        # 大阿卡纳牌：都需要罗马数字
        need_roman_numeral = True
    else:
        # 小阿卡纳牌：只有 card_number <= 10 才需要罗马数字和数量指令
        if card_number <= 10:
            need_roman_numeral = True
            # 添加详细的数量指令
            suit_name = suit.capitalize()
            # 根据花色确定物体名称
            suit_object_map = {
                "Wands": "wands (staves or rods)",
                "Cups": "cups (chalices or goblets)",
                "Swords": "swords",
                "Pentacles": "pentacles (coins or disks)"
            }
            suit_object = suit_object_map.get(suit_name, suit_name.lower())
            
            # 构建详细的数量指令
            quantity_instruction = (
                f"CRITICAL: The image must clearly and prominently show exactly {card_number} {suit_object}. "
                f"Each of the {card_number} {suit_object} must be distinctly visible and countable. "
                f"The number {card_number} is the central theme of this card, and all {card_number} {suit_object} should be "
                f"clearly depicted in the composition, whether they are held, displayed, arranged, or scattered in the scene. "
                f"Make sure the count is unambiguous and visually clear."
            )
    
    # 根据是否需要罗马数字，设置文字说明
    if need_roman_numeral:
        roman_num = number_to_roman(card_number)
        # 如果需要罗马数字和卡牌名：
        text_instruction = f"Important: At the top center of the card, display only the Roman numeral '{roman_num}'. At the bottom center, display only the text '{card_name_en}'. The image should have a light, thin border. Do not include any other text, letters, or numbers anywhere else in the image."
    else:
        # 如果只需要卡牌名：
        text_instruction = f"Important: At the bottom center of the card, display only the text '{card_name_en}'. The image should have a light, thin border. Do not include any other text, letters, or numbers anywhere else in the image."
    
    # 组合完整的 prompt
    parts = [description, quantity_instruction, original_style_prompt, new_style_prompt, text_instruction]
    
    full_prompt = " ".join(filter(None, parts))  # filter(None, parts) 会移除空字符串
    
    return full_prompt


def archive_and_cleanup(images_dir: Path, json_path: Path, all_card_names: List[str], dry_run: bool = False, archive_dir: Optional[Path] = None) -> None:
    """
    执行归档和清理任务
    
    Args:
        images_dir: 图像目录路径
        json_path: JSON文件路径
        all_card_names: 所有卡牌名称列表
        dry_run: 是否为试运行模式（不实际执行）
        archive_dir: 归档目录路径（可选，如果提供则复制归档图像到此目录）
    """
    logger.info("="*60)
    logger.info("执行归档和清理任务")
    logger.info("="*60)
    
    if dry_run:
        logger.info("🧪 试运行模式：只显示将要执行的操作，不实际执行")
    
    if archive_dir:
        logger.info(f"📁 归档文件夹: {archive_dir}")
    
    # 1. 重命名 Strength 为 Fortitude
    logger.info("")
    logger.info("步骤 1: 重命名 Strength 为 Fortitude")
    logger.info("-" * 60)
    if not dry_run:
        rename_strength_to_fortitude(images_dir, json_path)
    else:
        logger.info("   [试运行] 将重命名 Strength 文件夹和 JSON 中的名称")
    
    # 2. 归档选中的图像
    logger.info("")
    logger.info("步骤 2: 归档选中的图像")
    logger.info("-" * 60)
    archived_count = 0
    for card_name, selected_numbers in ARCHIVED_CARDS.items():
        logger.info(f"归档: {card_name} (保留编号: {selected_numbers})")
        if not dry_run:
            if archive_selected_images(card_name, selected_numbers, images_dir, archive_dir):
                archived_count += 1
        else:
            logger.info(f"   [试运行] 将归档 {card_name}，保留编号 {selected_numbers} 的图像")
            if archive_dir:
                logger.info(f"   [试运行] 将复制到归档文件夹: {archive_dir}")
            archived_count += 1
    
    logger.info(f"✅ 归档完成: {archived_count} 张卡牌")
    
    # 3. 清理需要重置的卡牌
    logger.info("")
    logger.info("步骤 3: 清理需要重置的卡牌")
    logger.info("-" * 60)
    reset_cards_with_fortitude = RESET_CARDS.copy()
    reset_cards_with_fortitude.discard("Strength")  # Strength 已经重命名为 Fortitude
    reset_cards_with_fortitude.add("Fortitude")  # Fortitude 需要被删除（因为 Strength 在 reset 列表中）
    
    if not dry_run:
        deleted_reset = cleanup_reset_cards(images_dir, reset_cards_with_fortitude)
        logger.info(f"✅ 删除重置卡牌文件夹: {deleted_reset} 个")
    else:
        logger.info(f"   [试运行] 将删除重置卡牌文件夹: {reset_cards_with_fortitude}")
    
    # 4. 清理未归档的卡牌
    logger.info("")
    logger.info("步骤 4: 清理未归档的卡牌（表格中没有记录的）")
    logger.info("-" * 60)
    if not dry_run:
        deleted_unarchived = cleanup_unarchived_cards(images_dir, ARCHIVED_CARDS, reset_cards_with_fortitude, all_card_names)
        logger.info(f"✅ 删除未归档卡牌文件夹: {deleted_unarchived} 个")
    else:
        logger.info(f"   [试运行] 将删除未归档的卡牌文件夹")
    
    logger.info("")
    logger.info("="*60)
    logger.info("归档和清理任务完成")
    logger.info("="*60)


def generate_all_card_images(
    start_index: int = 0,
    end_index: Optional[int] = None,
    test_mode: bool = False,
    skip_archived: bool = True
):
    """
    为所有卡片生成图片
    
    Args:
        start_index: 开始索引（用于断点续传）
        end_index: 结束索引（None表示处理到最后）
        test_mode: 测试模式，只处理第一张卡片
        skip_archived: 是否跳过已归档的卡牌
    """
    logger.info("="*60)
    logger.info("批量生成塔罗牌图片 - GPT-5 Image Mini")
    logger.info("="*60)
    
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
    
    total_cards = len(cards)
    logger.info(f"✅ 共找到 {total_cards} 张卡片")
    
    # 确定处理范围
    if test_mode:
        cards_to_process = cards[:1]
        logger.info("🧪 测试模式：只处理第一张卡片")
    else:
        if end_index is None:
            end_index = total_cards
        cards_to_process = cards[start_index:end_index]
        logger.info(f"📋 处理范围: 第 {start_index + 1} 到 {end_index} 张卡片")
        logger.info(f"   共 {len(cards_to_process)} 张卡片")
    
    # 准备保存目录
    output_base_dir = project_root / "database" / "images"
    output_base_dir.mkdir(exist_ok=True)
    logger.info(f"📁 图片保存目录: {output_base_dir}")
    
    # 统计信息
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    # 处理每张卡片
    for idx, card in enumerate(cards_to_process):
        card_index = start_index + idx  # 在原始数组中的索引
        card_name_en = card.get("card_name_en", "Unknown")
        card_name_cn = card.get("card_name_cn", "未知")
        card_number = card.get("card_number", 0)
        description = card.get("description", "")
        suit = card.get("suit", "")
        arcana = card.get("arcana", "").lower()
        is_major_arcana = arcana == "major"
        
        logger.info("")
        logger.info("="*60)
        logger.info(f"处理卡片 {card_index + 1}/{total_cards}: {card_name_en} ({card_name_cn})")
        logger.info(f"卡牌编号: {card_number}, 类型: {'大阿卡纳' if is_major_arcana else '小阿卡纳'}")
        logger.info("="*60)
        
        # 为每张卡牌创建子文件夹
        safe_name = card_name_en.replace(" ", "_").replace("'", "").replace("/", "_")
        card_dir = output_base_dir / safe_name
        
        # 检查是否已归档（需要跳过生成）
        if skip_archived and card_name_en in ARCHIVED_CARDS:
            logger.info(f"📦 卡牌已归档，跳过生成: {card_name_en}")
            skipped_count += 1
            continue
        
        card_dir.mkdir(exist_ok=True)
        
        # 检查是否已有图片，如果有任何图片就跳过
        existing_images = list(card_dir.glob("*.png"))
        if len(existing_images) > 0:
            logger.info(f"⏭️  图片已存在（{len(existing_images)}张），跳过: {safe_name}")
            skipped_count += 1
            continue
        
        if not description:
            logger.warning(f"⚠️  卡牌没有描述信息，跳过")
            skipped_count += 1
            continue
        
        try:
            # 构建 prompt
            full_prompt = build_prompt(description, card_name_en, card_number, suit, is_major_arcana, card_index)
            
            logger.info(f"📤 生成图片中...")
            logger.info(f"   Prompt 长度: {len(full_prompt)} 字符")
            
            # 生成2张图片
            logger.info(f"   开始生成 2 张图片...")
            result = generator.generate_image(
                prompt=full_prompt,
                size="1024x1536",  # 2:3 竖屏比例
                quality="high",
                n=2  # 每个卡牌生成2张
            )
            
            # 保存图片
            base_filename = f"{safe_name}.png"
            save_path = card_dir / base_filename
            
            if generator.download_image(result, save_path):
                # 统计保存的图片数量
                saved_images = list(card_dir.glob("*.png"))
                logger.info(f"✅ 成功！已保存 {len(saved_images)} 张图片到: {card_dir}")
                success_count += 1
            else:
                logger.error(f"❌ 保存失败")
                fail_count += 1
            
            # 避免请求过快，添加延迟
            if idx < len(cards_to_process) - 1:
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
    import argparse
    
    parser = argparse.ArgumentParser(description="使用 GPT-5 Image Mini 批量生成塔罗牌图片")
    parser.add_argument("--test", action="store_true", help="测试模式：只处理第一张卡片")
    parser.add_argument("--start", type=int, default=0, help="开始索引（用于断点续传）")
    parser.add_argument("--end", type=int, default=None, help="结束索引（默认处理到最后）")
    parser.add_argument("--archive", action="store_true", help="执行归档和清理任务")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式：只显示将要执行的操作，不实际执行")
    parser.add_argument("--no-skip-archived", action="store_true", help="不跳过已归档的卡牌（默认跳过）")
    parser.add_argument("--archive-dir", type=str, default=None, help="归档文件夹路径（可选，如果提供则复制归档图像到此目录）")
    
    args = parser.parse_args()
    
    # 如果指定了归档任务，执行归档和清理
    if args.archive:
        images_dir = project_root / "database" / "images"
        json_path = project_root / "database" / "data" / "pkt_tarot_cards.json"
        
        # 确定归档文件夹路径
        archive_dir = None
        if args.archive_dir:
            archive_dir = Path(args.archive_dir)
        else:
            # 默认归档文件夹：database/images/archived
            archive_dir = project_root / "database" / "images" / "archived"
        
        # 读取所有卡牌名称
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                cards = json.load(f)
            all_card_names = [card.get("card_name_en", "") for card in cards]
        else:
            logger.error(f"❌ JSON文件不存在: {json_path}")
            all_card_names = []
        
        archive_and_cleanup(images_dir, json_path, all_card_names, dry_run=args.dry_run, archive_dir=archive_dir)
    else:
        # 正常生成模式
        generate_all_card_images(
            start_index=args.start,
            end_index=args.end,
            test_mode=args.test,
            skip_archived=not args.no_skip_archived
        )

