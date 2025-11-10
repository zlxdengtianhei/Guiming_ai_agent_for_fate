#!/usr/bin/env python3
"""
上传塔罗牌和占卜方法数据到Supabase数据库
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# 添加backend目录到路径，以便导入配置
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# 加载环境变量 - 优先从backend目录的.env文件加载
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)
else:
    # 如果backend没有.env，尝试从项目根目录加载
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

# 数据文件路径 - 脚本在 database/scripts/ 目录下，所以需要向上两级到项目根目录
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"

def load_json_file(file_path: Path) -> List[Dict[Any, Any]]:
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def upload_tarot_cards(source: str, file_path: Path):
    """上传塔罗牌数据"""
    print(f"\n开始上传 {source} 塔罗牌数据...")
    cards = load_json_file(file_path)
    
    records = []
    for card in cards:
        record = {
            "source": source,
            "card_name_en": card.get("card_name_en", ""),
            "card_name_cn": card.get("card_name_cn"),
            "card_number": card.get("card_number"),
            "suit": card.get("suit", ""),
            "arcana": card.get("arcana", ""),
            "description": card.get("description"),
            "symbolic_meaning": card.get("symbolic_meaning"),
            "upright_meaning": card.get("upright_meaning"),
            "reversed_meaning": card.get("reversed_meaning"),
            "additional_meanings": card.get("additional_meanings"),
        }
        records.append(record)
    
    # 批量插入（Supabase支持批量插入）
    batch_size = 100
    total_inserted = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            result = supabase.table("tarot_cards").insert(batch).execute()
            total_inserted += len(batch)
            print(f"  已插入 {total_inserted}/{len(records)} 条记录")
        except Exception as e:
            print(f"  插入批次 {i//batch_size + 1} 时出错: {e}")
            # 尝试逐条插入
            for record in batch:
                try:
                    supabase.table("tarot_cards").insert(record).execute()
                    total_inserted += 1
                except Exception as err:
                    print(f"    跳过记录 {record.get('card_name_en')}: {err}")
    
    print(f"✓ 完成上传 {source} 塔罗牌数据: {total_inserted}/{len(records)} 条记录")

def upload_divination_methods(source: str, file_path: Path):
    """上传占卜方法数据"""
    print(f"\n开始上传 {source} 占卜方法数据...")
    methods = load_json_file(file_path)
    
    records = []
    for method in methods:
        metadata = method.get("metadata", {})
        record = {
            "source": source,
            "chunk_id": method.get("chunk_id", ""),
            "text": method.get("text", ""),
            "source_book": method.get("source"),
            "method_type": metadata.get("method_type"),
            "type": metadata.get("type"),
            "section": metadata.get("section"),
            "title": metadata.get("title"),
            "card_count": None if metadata.get("card_count") == "variable" or not isinstance(metadata.get("card_count"), int) else metadata.get("card_count"),
            "lines": metadata.get("lines"),
            "interpretation_type": metadata.get("interpretation_type"),
            "position": metadata.get("position"),
            "arcana_type": metadata.get("arcana_type"),
            "suit": metadata.get("suit"),
        }
        records.append(record)
    
    # 批量插入
    batch_size = 100
    total_inserted = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            result = supabase.table("divination_methods").insert(batch).execute()
            total_inserted += len(batch)
            print(f"  已插入 {total_inserted}/{len(records)} 条记录")
        except Exception as e:
            print(f"  插入批次 {i//batch_size + 1} 时出错: {e}")
            # 尝试逐条插入
            for record in batch:
                try:
                    supabase.table("divination_methods").insert(record).execute()
                    total_inserted += 1
                except Exception as err:
                    print(f"    跳过记录 {record.get('chunk_id')}: {err}")
    
    print(f"✓ 完成上传 {source} 占卜方法数据: {total_inserted}/{len(records)} 条记录")

def main():
    """主函数"""
    print("=" * 60)
    print("开始上传塔罗牌数据库")
    print("=" * 60)
    
    # 上传PKT数据
    pkt_cards_file = DATA_DIR / "pkt_tarot_cards.json"
    pkt_methods_file = DATA_DIR / "pkt_methods_and_interpretation.json"
    
    if pkt_cards_file.exists():
        upload_tarot_cards("pkt", pkt_cards_file)
    else:
        print(f"警告: 找不到文件 {pkt_cards_file}")
    
    if pkt_methods_file.exists():
        upload_divination_methods("pkt", pkt_methods_file)
    else:
        print(f"警告: 找不到文件 {pkt_methods_file}")
    
    # 上传78degrees数据
    degrees_cards_file = DATA_DIR / "78degrees_tarot_cards.json"
    degrees_methods_file = DATA_DIR / "78degrees_methods_and_interpretation.json"
    
    if degrees_cards_file.exists():
        upload_tarot_cards("78degrees", degrees_cards_file)
    else:
        print(f"警告: 找不到文件 {degrees_cards_file}")
    
    if degrees_methods_file.exists():
        upload_divination_methods("78degrees", degrees_methods_file)
    else:
        print(f"警告: 找不到文件 {degrees_methods_file}")
    
    print("\n" + "=" * 60)
    print("上传完成！")
    print("=" * 60)
    
    # 验证数据
    print("\n验证数据...")
    try:
        pkt_cards_count = supabase.table("tarot_cards").select("id", count="exact").eq("source", "pkt").execute()
        degrees_cards_count = supabase.table("tarot_cards").select("id", count="exact").eq("source", "78degrees").execute()
        pkt_methods_count = supabase.table("divination_methods").select("id", count="exact").eq("source", "pkt").execute()
        degrees_methods_count = supabase.table("divination_methods").select("id", count="exact").eq("source", "78degrees").execute()
        
        print(f"\n数据统计:")
        print(f"  PKT 塔罗牌: {pkt_cards_count.count} 条")
        print(f"  78degrees 塔罗牌: {degrees_cards_count.count} 条")
        print(f"  PKT 占卜方法: {pkt_methods_count.count} 条")
        print(f"  78degrees 占卜方法: {degrees_methods_count.count} 条")
    except Exception as e:
        print(f"验证数据时出错: {e}")

if __name__ == "__main__":
    main()

