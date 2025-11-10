#!/usr/bin/env python3
"""
上传塔罗牌图片到Supabase Storage并更新数据库
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
    # 构建存储路径：CardName/image_filename.png
    storage_path = f"{card_name}/{image_path.name}"
    
    try:
        # 读取图片文件
        with open(image_path, 'rb') as f:
            file_data = f.read()
        
        # 上传到Storage
        result = supabase.storage.from_(BUCKET_NAME).upload(
            storage_path,
            file_data,
            file_options={"content-type": "image/png", "upsert": "true"}
        )
        
        # 获取公开URL
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
        return public_url
    except Exception as e:
        print(f"  上传图片失败 {image_path.name}: {e}")
        return None

def folder_name_to_card_name(folder_name: str) -> str:
    """将文件夹名称转换为数据库中的卡片名称格式"""
    # 将下划线替换为空格，并保持首字母大写
    # 例如: "The_Magician" -> "The Magician"
    return folder_name.replace("_", " ")

def update_card_image_url(card_name_en: str, image_url: str):
    """更新数据库中的image_url字段"""
    try:
        # 查找对应的卡片（PKT源）
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
    print("开始上传塔罗牌图片")
    print("=" * 60)
    
    if not IMAGES_DIR.exists():
        print(f"错误: 图片目录不存在: {IMAGES_DIR}")
        return
    
    # 遍历tarot_card目录下的所有卡片文件夹
    uploaded_count = 0
    updated_count = 0
    skipped_count = 0
    
    for card_dir in sorted(IMAGES_DIR.iterdir()):
        if not card_dir.is_dir():
            continue
        
        folder_name = card_dir.name
        # 转换为数据库中的卡片名称格式
        card_name_en = folder_name_to_card_name(folder_name)
        print(f"\n处理卡片: {card_name_en} (文件夹: {folder_name})")
        
        # 查找该目录下的所有PNG图片
        png_files = list(card_dir.glob("*.png"))
        
        if not png_files:
            print(f"  跳过: 未找到PNG图片")
            skipped_count += 1
            continue
        
        # 优先选择与文件夹名称匹配的PNG文件（例如 Justice/Justice.png）
        # 如果没有匹配的，则选择第一个
        image_file = None
        preferred_name = f"{folder_name}.png"
        for png_file in png_files:
            if png_file.name == preferred_name:
                image_file = png_file
                break
        
        if not image_file:
            # 如果没有找到匹配的，选择第一个（按名称排序）
            image_file = sorted(png_files)[0]
        
        print(f"  上传图片: {image_file.name}")
        
        # 上传到Storage（使用文件夹名称作为路径）
        image_url = upload_image_to_storage(folder_name, image_file)
        
        if image_url:
            print(f"  上传成功: {image_url}")
            uploaded_count += 1
            
            # 更新数据库（使用转换后的卡片名称）
            if update_card_image_url(card_name_en, image_url):
                print(f"  数据库更新成功")
                updated_count += 1
            else:
                print(f"  数据库更新失败")
        else:
            skipped_count += 1
    
    print("\n" + "=" * 60)
    print("上传完成！")
    print("=" * 60)
    print(f"\n统计:")
    print(f"  成功上传: {uploaded_count} 张")
    print(f"  数据库更新: {updated_count} 条")
    print(f"  跳过: {skipped_count} 个")

if __name__ == "__main__":
    main()

