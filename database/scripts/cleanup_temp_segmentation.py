#!/usr/bin/env python3
"""
清理Supabase Storage中的临时图像分割文件

使用方法:
    python3 database/scripts/cleanup_temp_segmentation.py [--dry-run]
"""
import os
import sys
from pathlib import Path
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

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="清理Supabase Storage中的临时图像分割文件")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅显示要删除的文件，不实际删除"
    )
    args = parser.parse_args()
    
    try:
        from supabase import create_client, Client
        
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        
        if not supabase_url or not supabase_key:
            print("❌ 未配置SUPABASE_URL和SUPABASE_SERVICE_ROLE_KEY环境变量")
            return
        
        supabase: Client = create_client(supabase_url, supabase_key)
        bucket_name = "tarot-cards"
        
        # 列出temp目录下的所有文件
        print(f"📁 检查 Supabase Storage bucket: {bucket_name}")
        print(f"📂 路径: temp/")
        print()
        
        try:
            files = supabase.storage.from_(bucket_name).list("temp")
            
            # 过滤出临时分割文件
            temp_files = [f for f in files if f.get("name", "").startswith("temp_segmentation_")]
            
            if not temp_files:
                print("✅ 没有找到临时分割文件")
                return
            
            print(f"📄 找到 {len(temp_files)} 个临时分割文件:")
            total_size = 0
            for f in temp_files:
                name = f.get("name", "unknown")
                size = f.get("metadata", {}).get("size", 0)
                total_size += size
                print(f"  - {name} ({size / 1024:.2f} KB)")
            
            print(f"\n📊 总大小: {total_size / 1024:.2f} KB ({total_size / 1024 / 1024:.2f} MB)")
            
            if args.dry_run:
                print("\n🔍 这是预览模式（--dry-run），不会实际删除文件")
                print("   要实际删除，请运行: python3 database/scripts/cleanup_temp_segmentation.py")
            else:
                print(f"\n🗑️  开始删除 {len(temp_files)} 个文件...")
                deleted_count = 0
                failed_count = 0
                
                for f in temp_files:
                    file_path = f"temp/{f.get('name')}"
                    try:
                        supabase.storage.from_(bucket_name).remove([file_path])
                        deleted_count += 1
                        print(f"  ✅ 已删除: {f.get('name')}")
                    except Exception as e:
                        failed_count += 1
                        print(f"  ❌ 删除失败 {f.get('name')}: {e}")
                
                print(f"\n✅ 完成！成功删除 {deleted_count} 个文件")
                if failed_count > 0:
                    print(f"⚠️  失败 {failed_count} 个文件")
        
        except Exception as e:
            print(f"❌ 列出文件失败: {e}")
    
    except ImportError:
        print("❌ 需要安装supabase库: pip install supabase")
    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    main()




