#!/usr/bin/env python3
"""提取日志文件中的所有LLM交互"""

import json
import sys
from pathlib import Path

def extract_llm_interactions(log_file):
    """从日志文件中提取所有LLM交互"""
    with open(log_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    interactions = []
    
    # 提取基本信息
    question = data.get('question', '')
    user_profile = data.get('user_profile', {})
    
    print("=" * 80)
    print("占卜问题:", question)
    print("用户信息:", json.dumps(user_profile, ensure_ascii=False, indent=2))
    print("=" * 80)
    print("\n")
    
    # 遍历所有步骤
    for step in data.get('steps', []):
        step_name = step.get('step_name', '')
        step_order = step.get('step_order', 0)
        prompt_content = step.get('prompt_content', '')
        prompt_type = step.get('prompt_type', '')
        model_used = step.get('model_used', '')
        temperature = step.get('temperature', '')
        
        # 获取LLM响应
        llm_response = None
        output_data = step.get('output_data', {})
        
        if 'llm_response' in output_data:
            llm_response = output_data['llm_response']
        elif 'analysis' in output_data and isinstance(output_data['analysis'], dict):
            if 'llm_response' in output_data['analysis']:
                llm_response = output_data['analysis']['llm_response']
            else:
                # 如果analysis本身就是响应，尝试序列化
                llm_response = json.dumps(output_data['analysis'], ensure_ascii=False, indent=2)
        
        if prompt_content or llm_response:
            interaction = {
                'step_name': step_name,
                'step_order': step_order,
                'prompt_type': prompt_type,
                'prompt_content': prompt_content,
                'llm_response': llm_response,
                'model_used': model_used,
                'temperature': temperature,
                'input_data': step.get('input_data', {}),
                'output_data': output_data
            }
            interactions.append(interaction)
    
    return interactions, data

def print_interactions(interactions):
    """打印所有交互"""
    for i, interaction in enumerate(interactions, 1):
        print("\n" + "=" * 80)
        print(f"交互 #{i}: {interaction['step_name']} (步骤 {interaction['step_order']})")
        print("=" * 80)
        print(f"模型: {interaction['model_used']}")
        print(f"温度: {interaction['temperature']}")
        print(f"Prompt类型: {interaction['prompt_type']}")
        print("\n--- PROMPT ---")
        print(interaction['prompt_content'])
        print("\n--- LLM RESPONSE ---")
        print(interaction['llm_response'])
        print("\n" + "-" * 80)

if __name__ == '__main__':
    # 默认使用result目录中的最新日志文件
    result_dir = Path(__file__).parent / "result"
    log_files = list(result_dir.glob("test_reading_log_*.json"))
    if log_files:
        log_file = max(log_files, key=lambda p: p.stat().st_mtime)
        print(f"使用最新的日志文件: {log_file}")
    else:
        print("❌ 未找到日志文件，请指定日志文件路径")
        sys.exit(1)
    
    interactions, full_data = extract_llm_interactions(str(log_file))
    print_interactions(interactions)
    
    # 保存到文件
    output_file = result_dir / 'llm_interactions_extracted.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'question': full_data.get('question', ''),
            'user_profile': full_data.get('user_profile', {}),
            'interactions': interactions
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n总共提取了 {len(interactions)} 个LLM交互")
    print(f"已保存到: {output_file}")

