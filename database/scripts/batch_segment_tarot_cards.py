#!/usr/bin/env python3
"""
批量处理塔罗卡牌图像分割

遍历 database/images/tarot_card 中的所有图片，使用阿里云图像分割API进行分割，
并将结果保存到 database/images/extract 文件夹，保持原有的目录结构。
"""
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple
from dotenv import load_dotenv

# 添加脚本目录到路径，以便导入 image_segmentation_simple
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

# 导入图像分割类
from image_segmentation_simple import AliyunImageSegmentation


def find_all_images(root_dir: Path) -> List[Path]:
    """查找所有PNG图片文件"""
    images = []
    for ext in ['*.png', '*.PNG', '*.jpg', '*.JPG', '*.jpeg', '*.JPEG']:
        images.extend(root_dir.rglob(ext))
    return sorted(images)


def get_output_path(input_path: Path, extract_root: Path, tarot_card_root: Path) -> Path:
    """根据输入路径生成输出路径，保持目录结构"""
    # 获取相对于 tarot_card_root 的相对路径
    relative_path = input_path.relative_to(tarot_card_root)
    # 在 extract_root 下创建相同的目录结构
    output_path = extract_root / relative_path
    # 确保输出文件是PNG格式
    return output_path.with_suffix('.png')


def process_images(
    tarot_card_dir: Path,
    extract_dir: Path,
    client: AliyunImageSegmentation,
    skip_existing: bool = True
) -> Tuple[int, int, List[str], int]:
    """
    批量处理图像分割
    
    Args:
        tarot_card_dir: 输入目录（tarot_card）
        extract_dir: 输出目录（extract）
        client: 图像分割客户端
        skip_existing: 是否跳过已存在的文件
    
    Returns:
        (成功数量, 失败数量, 错误列表)
    """
    # 查找所有图片
    print(f"🔍 正在扫描目录: {tarot_card_dir}")
    images = find_all_images(tarot_card_dir)
    total = len(images)
    
    if total == 0:
        print("❌ 未找到任何图片文件")
        return 0, 0, [], 0
    
    print(f"📊 找到 {total} 个图片文件\n")
    
    # 创建输出目录
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    fail_count = 0
    errors = []
    skipped_count = 0
    
    for idx, image_path in enumerate(images, 1):
        # 生成输出路径
        output_path = get_output_path(image_path, extract_dir, tarot_card_dir)
        
        # 检查是否已存在
        if skip_existing and output_path.exists():
            print(f"[{idx}/{total}] ⏭️  跳过（已存在）: {image_path.name}")
            print(f"      输出: {output_path.relative_to(extract_dir.parent)}")
            skipped_count += 1
            continue
        
        print(f"\n[{idx}/{total}] 📷 处理: {image_path.name}")
        print(f"      输入: {image_path.relative_to(tarot_card_dir.parent)}")
        print(f"      输出: {output_path.relative_to(extract_dir.parent)}")
        
        # 执行分割
        start_time = time.time()
        result = client.segment_hd_common_image(image_path)
        elapsed_time = time.time() - start_time
        
        if not result.get("success"):
            error_msg = result.get("error", "未知错误")
            print(f"      ❌ 分割失败: {error_msg}")
            fail_count += 1
            errors.append(f"{image_path.name}: {error_msg}")
            continue
        
        image_url = result.get("image_url")
        request_id = result.get("request_id")
        
        print(f"      ✅ 分割成功 (耗时: {elapsed_time:.2f}秒)")
        
        # 下载图像
        print(f"      ⬇️  下载中...")
        if client.download_segmented_image(image_url, output_path):
            file_size = output_path.stat().st_size / 1024
            print(f"      ✅ 已保存: {file_size:.2f} KB")
            success_count += 1
        else:
            print(f"      ❌ 下载失败")
            fail_count += 1
            errors.append(f"{image_path.name}: 下载失败")
        
        # 添加短暂延迟，避免API限流
        if idx < total:
            time.sleep(0.5)
    
    return success_count, fail_count, errors, skipped_count


def main():
    """主函数"""
    # 加载环境变量
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent.parent / "backend"
    env_file = backend_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
    # 设置路径
    project_root = script_dir.parent.parent
    tarot_card_dir = project_root / "database" / "images" / "tarot_card"
    extract_dir = project_root / "database" / "images" / "extract"
    
    # 检查输入目录
    if not tarot_card_dir.exists():
        print(f"❌ 输入目录不存在: {tarot_card_dir}")
        sys.exit(1)
    
    print("=" * 60)
    print("🎴 塔罗卡牌批量图像分割工具")
    print("=" * 60)
    print(f"📁 输入目录: {tarot_card_dir}")
    print(f"📁 输出目录: {extract_dir}\n")
    
    # 初始化客户端
    access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID", "").strip()
    access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "").strip()
    
    if not access_key_id or not access_key_secret:
        print("❌ 请配置 ALIYUN_ACCESS_KEY_ID 和 ALIYUN_ACCESS_KEY_SECRET 环境变量")
        print("   在 backend/.env 文件中配置，或设置环境变量")
        print("   获取方式: https://ram.console.aliyun.com/manage/ak")
        sys.exit(1)
    
    client = AliyunImageSegmentation(access_key_id, access_key_secret)
    print("✅ 阿里云客户端初始化成功\n")
    
    # 批量处理
    start_time = time.time()
    success_count, fail_count, errors, skipped_count = process_images(
        tarot_card_dir,
        extract_dir,
        client,
        skip_existing=True
    )
    total_time = time.time() - start_time
    
    # 输出统计信息
    print("\n" + "=" * 60)
    print("📊 处理完成统计")
    print("=" * 60)
    print(f"✅ 成功: {success_count}")
    print(f"⏭️  跳过: {skipped_count}")
    print(f"❌ 失败: {fail_count}")
    print(f"⏱️  总耗时: {total_time:.2f}秒")
    
    if errors:
        print(f"\n❌ 失败详情:")
        for error in errors:
            print(f"   - {error}")
    
    print("\n🎉 批量处理完成！")


if __name__ == "__main__":
    main()

