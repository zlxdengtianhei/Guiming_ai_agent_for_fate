#!/usr/bin/env python3
"""
快速切换到最快模型配置（全部使用 gpt-4o-mini）
"""

import os
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"

def main():
    print("=" * 60)
    print("切换到最快模型配置")
    print("=" * 60)
    print()
    
    # 读取现有 .env 文件
    env_content = ""
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 更新或添加 MODEL_PRESET
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith("MODEL_PRESET="):
                new_lines.append("MODEL_PRESET=gpt4omini_fast\n")
                updated = True
            else:
                new_lines.append(line)
        
        if not updated:
            new_lines.append("MODEL_PRESET=gpt4omini_fast\n")
        
        env_content = "".join(new_lines)
    else:
        env_content = "MODEL_PRESET=gpt4omini_fast\n"
    
    # 写入文件
    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("✅ 已更新配置为: gpt4omini_fast")
    print()
    print("📊 当前配置:")
    print("  问题分析: openai/gpt-4o-mini ⚡")
    print("  意象生成: openai/gpt-4o-mini ⚡")
    print("  最终解读: deepseek/deepseek-r1")
    print()
    print("⚠️  注意：最终解读仍使用 DeepSeek R1（推理能力强但较慢）")
    print()
    print("💡 如果想全部使用 gpt-4o-mini（最快），需要修改代码中的预设配置")
    print("   或者可以尝试 deepseek_fast 预设（全部使用 DeepSeek Chat，更快）")
    print()
    print("🔄 请重启后端服务以使配置生效：")
    print("   cd backend")
    print("   # 停止当前服务（Ctrl+C）")
    print("   source venv/bin/activate")
    print("   uvicorn main:app --reload --host 0.0.0.0 --port 8001")
    print()

if __name__ == "__main__":
    main()



