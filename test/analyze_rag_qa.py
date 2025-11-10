#!/usr/bin/env python3
"""
分析RAG查询日志，提取问题和答案，翻译为中文，并识别重复答案
"""

import json
from collections import defaultdict
from typing import Dict, List, Tuple

def translate_query_type(query_type: str) -> str:
    """翻译查询类型"""
    translations = {
        "method_steps": "方法步骤",
        "position_interpretation": "位置解读",
        "psychological_background": "心理背景",
        "traditional_method": "传统方法",
        "number_patterns": "数字模式",
        "suit_distribution": "花色分布",
        "card_relationships": "牌面关系",
        "basic_meaning": "基本含义",
        "visual_description": "视觉描述",
        "upright_meaning": "正位含义",
        "reversed_meaning": "逆位含义",
        "position_meaning": "位置含义",
        "psychological_meaning": "心理含义",
        "suit_element_meaning": "花色元素含义"
    }
    return translations.get(query_type, query_type)

def translate_query(query_text: str) -> str:
    """翻译查询文本"""
    # 这里使用简单的关键词替换，实际应该使用翻译API
    translations = {
        "three_card spread": "三张牌阵",
        "tarot": "塔罗",
        "divination": "占卜",
        "method": "方法",
        "how to use": "如何使用",
        "steps": "步骤",
        "card positions": "牌的位置",
        "meaning": "含义",
        "interpretation": "解读",
        "psychological approach": "心理方法",
        "traditional": "传统",
        "ancient celtic": "古代凯尔特",
        "number patterns": "数字模式",
        "same numbers": "相同数字",
        "sequences": "序列",
        "suit distribution": "花色分布",
        "element balance": "元素平衡",
        "relationships": "关系",
        "sequence meaning": "序列含义",
        "past": "过去",
        "present": "现在",
        "future": "未来",
        "description": "描述",
        "image": "图像",
        "visual appearance": "视觉外观",
        "upright": "正位",
        "reversed": "逆位",
        "water element": "水元素",
        "emotion": "情感",
        "air element": "风元素",
        "thought": "思想",
        "earth element": "土元素",
        "material": "物质"
    }
    
    result = query_text
    for eng, chn in translations.items():
        result = result.replace(eng, chn)
    
    # 手动翻译一些常见模式
    if "Four of Cups" in result:
        result = result.replace("Four of Cups", "圣杯四")
    if "Five of Swords" in result:
        result = result.replace("Five of Swords", "宝剑五")
    if "King of Pentacles" in result:
        result = result.replace("King of Pentacles", "星币国王")
    
    return result

def translate_answer(answer_text: str) -> str:
    """翻译答案文本"""
    # 这里只是简单的占位，实际应该使用翻译API
    # 由于答案较长，我们保留英文原文，但添加中文说明
    return answer_text  # 实际应用中应该使用翻译服务

def analyze_duplicates(data: dict) -> Dict[str, List[Tuple[int, str, str]]]:
    """
    分析重复答案
    返回: {chunk_id: [(query_index, query_text, answer_preview), ...]}
    """
    duplicates = defaultdict(list)
    
    # 从duplicate_analysis中提取信息
    if "duplicate_analysis" in data and "duplicates" in data["duplicate_analysis"]:
        for chunk_id, query_list in data["duplicate_analysis"]["duplicates"].items():
            for query_info in query_list:
                query_idx = query_info["query_index"]
                query_text = query_info["query"]
                
                # 从query_result_mapping中找到对应的答案
                answer_preview = ""
                for qm in data["query_result_mapping"]:
                    if qm["query_index"] == query_idx + 1:  # query_index从1开始
                        answer_preview = qm.get("result_text_preview", "")
                        break
                
                duplicates[chunk_id].append((query_idx + 1, query_text, answer_preview))
    
    return duplicates

def main():
    # 读取JSON文件
    with open("test/result/rag_analysis_test_reading_log_20251106_230806.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 提取所有问题和答案
    qa_pairs = []
    for query in data["query_result_mapping"]:
        query_idx = query["query_index"]
        query_type = translate_query_type(query["query_type"])
        card_name = query.get("card_name") or "N/A"
        query_text_en = query["query_text"]
        query_text_cn = translate_query(query_text_en)
        answer_preview = query.get("result_text_preview", "")
        
        qa_pairs.append({
            "index": query_idx,
            "type": query_type,
            "card": card_name,
            "query_en": query_text_en,
            "query_cn": query_text_cn,
            "answer": answer_preview,
            "top_chunks": query.get("top_doc_ids", [])
        })
    
    # 分析重复答案
    duplicates = analyze_duplicates(data)
    
    # 生成报告
    output = []
    output.append("=" * 80)
    output.append("RAG查询问题与答案分析报告")
    output.append("=" * 80)
    output.append(f"\n原始问题: {data['question']}")
    output.append(f"总查询数: {data['summary']['total_queries']}")
    output.append("\n" + "=" * 80)
    output.append("所有问题与答案（按查询顺序）")
    output.append("=" * 80)
    
    for qa in qa_pairs:
        output.append(f"\n【查询 #{qa['index']}】")
        output.append(f"类型: {qa['type']}")
        output.append(f"牌名: {qa['card']}")
        output.append(f"问题（英文）: {qa['query_en']}")
        output.append(f"问题（中文）: {qa['query_cn']}")
        output.append(f"答案预览: {qa['answer'][:200]}..." if len(qa['answer']) > 200 else f"答案预览: {qa['answer']}")
        output.append(f"使用的文档块: {', '.join(qa['top_chunks'][:3])}")
        output.append("-" * 80)
    
    # 重复答案分析
    output.append("\n" + "=" * 80)
    output.append("重复答案分析")
    output.append("=" * 80)
    
    if duplicates:
        for chunk_id, query_list in duplicates.items():
            if len(query_list) > 1:  # 只显示真正重复的
                output.append(f"\n【重复的文档块: {chunk_id}】")
                output.append(f"被 {len(query_list)} 个不同查询使用:")
                
                # 获取第一个查询的完整答案作为示例
                first_query_idx = query_list[0][0]
                example_answer = ""
                for qa in qa_pairs:
                    if qa['index'] == first_query_idx:
                        example_answer = qa['answer']
                        break
                
                for query_idx, query_text, answer_preview in query_list:
                    query_cn = translate_query(query_text)
                    output.append(f"\n  查询 #{query_idx}: {query_cn}")
                    output.append(f"  原始问题: {query_text}")
                
                output.append(f"\n  重复的答案内容（示例）:")
                output.append(f"  {example_answer[:300]}..." if len(example_answer) > 300 else f"  {example_answer}")
                output.append("-" * 80)
    else:
        output.append("\n未发现重复答案")
    
    # 统计信息
    output.append("\n" + "=" * 80)
    output.append("统计摘要")
    output.append("=" * 80)
    
    duplicate_chunks = sum(1 for chunk_id, query_list in duplicates.items() if len(query_list) > 1)
    output.append(f"重复使用的文档块数量: {duplicate_chunks}")
    output.append(f"总唯一文档块数: {data['summary']['total_unique_chunks']}")
    output.append(f"重复文档块总数: {data['summary']['duplicate_chunks_count']}")
    
    # 写入文件
    report = "\n".join(output)
    print(report)
    
    with open("test/result/rag_qa_analysis_report_zh.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n报告已保存到: test/result/rag_qa_analysis_report_zh.md")

if __name__ == "__main__":
    main()




