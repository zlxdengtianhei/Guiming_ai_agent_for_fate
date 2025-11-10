#!/usr/bin/env python3
"""
检查当前使用的模型配置
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.model_config import get_model_config

def main():
    print("=" * 60)
    print("当前模型配置检查")
    print("=" * 60)
    print()
    
    # 检查环境变量
    print("📋 环境变量配置:")
    print(f"  USE_OPENROUTER: {settings.use_openrouter}")
    print(f"  MODEL_PRESET (环境变量): {getattr(settings, 'model_preset', '未设置')}")
    print()
    
    # 获取模型配置
    model_config = get_model_config()
    
    print("🤖 当前使用的模型预设:")
    print(f"  {model_config.preset.value}")
    print()
    
    print("📊 各任务使用的模型:")
    print(f"  问题分析 (Question Analysis):")
    print(f"    → {model_config.question_analysis_model}")
    print()
    print(f"  意象生成 (Imagery Generation):")
    print(f"    → {model_config.imagery_generation_model}")
    print()
    print(f"  最终解读 (Final Interpretation):")
    print(f"    → {model_config.final_interpretation_model}")
    print()
    
    # 性能预估
    print("⏱️  预期性能:")
    preset = model_config.preset.value
    if preset == "gpt5_4omini":
        print("  ⚠️  当前使用 GPT-5，速度较慢 (~200秒)")
        print("  💡 建议切换到 gpt4omini_fast 可提速 7-9倍")
    elif preset == "gpt4omini_fast":
        print("  ✅ 快速模式 (~25-30秒)")
    elif preset == "deepseek_fast":
        print("  ✅ 快速模式 (~30-35秒)")
    elif preset == "deepseek_r1_v3":
        print("  ⚡ 平衡模式 (~60-90秒)")
    elif preset == "gemini_25pro_15":
        print("  ⚡ 平衡模式 (~40-60秒)")
    print()
    
    print("=" * 60)
    print("💡 如需切换模型，请运行:")
    print("   cd .. && ./switch_model_speed.sh")
    print("=" * 60)

if __name__ == "__main__":
    main()



