#!/usr/bin/env python3
"""
依次运行三种模型组合的测试
使用原始的test_complete_reading_with_logging.py脚本
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

# 确保使用OpenRouter
os.environ['USE_OPENROUTER'] = 'true'

# 三种模型预设
presets = [
    ("gpt5_4omini", "GPT-5 (意象+解读) + GPT-4o-mini (问题分析)"),
    ("deepseek_r1_v3", "DeepSeek R1 (意象+解读) + DeepSeek v3 (问题分析)"),
    ("gemini_25pro_15", "Gemini 2.5 Pro (意象+解读) + Gemini 1.5 (问题分析)")
]

test_script = project_root / "test" / "test_complete_reading_with_logging.py"

print("="*80)
print("依次运行三种模型组合的测试")
print("="*80)

for preset_value, preset_name in presets:
    print(f"\n{'='*80}")
    print(f"测试: {preset_name}")
    print(f"预设: {preset_value}")
    print("="*80)
    
    # 设置环境变量
    os.environ['MODEL_PRESET'] = preset_value
    
    # 运行测试脚本
    try:
        result = subprocess.run(
            [sys.executable, str(test_script)],
            env=os.environ.copy(),
            cwd=str(project_root),
            check=True,
            capture_output=False
        )
        print(f"\n✅ {preset_name} 测试完成")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {preset_name} 测试失败: {e}")
    
    # 等待一段时间避免API限流
    if preset_value != presets[-1][0]:  # 不是最后一个
        print("\n等待10秒以避免API限流...")
        import time
        time.sleep(10)

print("\n" + "="*80)
print("所有测试完成")
print("="*80)




