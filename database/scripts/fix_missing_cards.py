#!/usr/bin/env python3
"""
修复未找到的卡片：Fortitude 和 The Last Judgment
"""
import os
import sys
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# 添加backend目录到路径
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# 加载环境变量
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    root_env = Path(__file__).parent.parent.parent / ".env"
    if root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

# 获取Supabase配置
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("请设置SUPABASE_URL和SUPABASE_SERVICE_ROLE_KEY环境变量")

# 创建Supabase客户端
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 图片目录路径
SCRIPT_DIR = Path(__file__).parent
IMAGES_DIR = SCRIPT_DIR.parent / "images" / "tarot_card"
BUCKET_NAME = "tarot-cards"

def upload_image_to_storage(card_name: str, image_path: Path) -> str:
    """上传图片到Supabase Storage并返回公开URL"""
    storage_path = f"{card_name}/{image_path.name}"
    
    try:
        with open(image_path, 'rb') as f:
            file_data = f.read()
        
        result = supabase.storage.from_(BUCKET_NAME).upload(
            storage_path,
            file_data,
            file_options={"content-type": "image/png", "upsert": "true"}
        )
        
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
        return public_url
    except Exception as e:
        print(f"  上传图片失败 {image_path.name}: {e}")
        return None

def update_card_image_url(card_name_en: str, image_url: str):
    """更新数据库中的image_url字段"""
    try:
        result = supabase.table("tarot_cards").update({
            "image_url": image_url
        }).eq("card_name_en", card_name_en).eq("source", "pkt").execute()
        
        if result.data:
            return True
        else:
            print(f"  警告: 未找到卡片 {card_name_en}")
            return False
    except Exception as e:
        print(f"  更新数据库失败 {card_name_en}: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("修复未找到的卡片")
    print("=" * 60)
    
    # 需要修复的卡片列表
    # 格式: (文件夹名称, 数据库中的卡片名称)
    cards_to_fix = [
        ("Fortitude", "Strength"),  # 数据库中名称是 Strength
        ("The_Last_Judgment", "Judgement"),  # 数据库中名称是 Judgement
    ]
    
    for folder_name, card_name_en in cards_to_fix:
        print(f"\n处理卡片: {card_name_en} (文件夹: {folder_name})")
        
        card_dir = IMAGES_DIR / folder_name
        if not card_dir.exists():
            print(f"  错误: 文件夹不存在: {card_dir}")
            continue
        
        # 查找PNG图片
        png_files = list(card_dir.glob("*.png"))
        if not png_files:
            print(f"  跳过: 未找到PNG图片")
            continue
        
        # 优先选择与文件夹名称匹配的PNG文件
        image_file = None
        preferred_name = f"{folder_name}.png"
        for png_file in png_files:
            if png_file.name == preferred_name:
                image_file = png_file
                break
        
        if not image_file:
            image_file = sorted(png_files)[0]
        
        print(f"  上传图片: {image_file.name}")
        
        # 上传到Storage
        image_url = upload_image_to_storage(folder_name, image_file)
        
        if image_url:
            print(f"  上传成功: {image_url}")
            
            # 更新数据库
            if update_card_image_url(card_name_en, image_url):
                print(f"  数据库更新成功")
            else:
                # 尝试查找数据库中可能的名称变体
                print(f"  尝试查找数据库中的变体...")
                # 查找所有可能的匹配
                all_cards = supabase.table("tarot_cards").select("card_name_en").eq("source", "pkt").execute()
                matching = [c for c in all_cards.data if card_name_en.lower() in c['card_name_en'].lower() or c['card_name_en'].lower() in card_name_en.lower()]
                if matching:
                    print(f"  找到可能的匹配: {[c['card_name_en'] for c in matching]}")
                    # 尝试更新第一个匹配
                    if update_card_image_url(matching[0]['card_name_en'], image_url):
                        print(f"  使用变体名称更新成功: {matching[0]['card_name_en']}")
        else:
            print(f"  上传失败")
    
    print("\n" + "=" * 60)
    print("修复完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()

