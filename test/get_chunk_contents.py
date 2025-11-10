#!/usr/bin/env python3
"""
获取指定chunk_id的文档块内容
"""

import json
import re
from pathlib import Path

def find_chunk_in_json(json_file: str, chunk_id_base: str):
    """在JSON文件中查找chunk内容"""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for doc in data:
        if doc.get('chunk_id', '').startswith(chunk_id_base):
            return doc
    return None

def get_chunk_content(chunk_id: str):
    """获取chunk内容"""
    # 提取基础chunk_id（去掉#1后缀）
    base_id = chunk_id.split('#')[0]
    
    # 确定文件路径
    if base_id.startswith('pkt-section-'):
        json_file = 'rag/data/pkt_documents.json'
    elif base_id.startswith('78degrees-section-'):
        json_file = 'rag/data/78degrees_documents.json'
    else:
        return None
    
    json_path = Path(json_file)
    if not json_path.exists():
        return None
    
    # 查找chunk
    chunk = find_chunk_in_json(str(json_path), base_id)
    return chunk

def main():
    chunk_ids = [
        'pkt-section-0079#1',
        '78degrees-section-0262#1',
        '78degrees-section-0315#1'
    ]
    
    print("=" * 80)
    print("文档块内容查询")
    print("=" * 80)
    
    for chunk_id in chunk_ids:
        print(f"\n{'='*80}")
        print(f"Chunk ID: {chunk_id}")
        print(f"{'='*80}\n")
        
        chunk = get_chunk_content(chunk_id)
        
        if chunk:
            print(f"基础 Chunk ID: {chunk.get('chunk_id', 'N/A')}")
            print(f"来源: {chunk.get('source', 'N/A')}")
            print(f"元数据: {chunk.get('metadata', {})}")
            print(f"\n内容:")
            print("-" * 80)
            text = chunk.get('text', '')
            # 格式化输出，每行不超过80字符
            words = text.split()
            line = ""
            for word in words:
                if len(line) + len(word) + 1 > 80:
                    print(line)
                    line = word
                else:
                    line = line + " " + word if line else word
            if line:
                print(line)
        else:
            print(f"❌ 未找到chunk: {chunk_id}")
            print("注意: chunk_id中的#1后缀表示这是进一步分块的结果。")
            print("基础section内容可能包含多个子块。")
        
        print()

if __name__ == "__main__":
    main()




