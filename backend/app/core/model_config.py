"""
模型配置管理 - 支持多种模型组合
"""

from typing import Literal, Dict, Optional
from enum import Enum
from app.core.config import settings


class ModelPreset(str, Enum):
    """模型预设组合"""
    GPT5_4OMINI = "gpt5_4omini"  # GPT-5 (意象+解读) + GPT-4o-mini (问题分析)
    GPT4OMINI_FAST = "gpt4omini_fast"  # ⚡ 全部使用 GPT-4o-mini（快速模式）
    DEEPSEEK_R1_V3 = "deepseek_r1_v3"  # DeepSeek R1 (意象+解读) + DeepSeek v3 (问题分析)
    DEEPSEEK_FAST = "deepseek_fast"  # ⚡ 全部使用 DeepSeek Chat（快速模式）
    GEMINI_25PRO_15 = "gemini_25pro_15"  # Gemini 2.5 Pro (意象+解读) + Gemini 1.5 (问题分析)


class ModelConfig:
    """模型配置类 - 管理不同任务的模型选择"""
    
    # 模型预设配置
    PRESETS: Dict[ModelPreset, Dict[str, str]] = {
        ModelPreset.GPT5_4OMINI: {
            "question_analysis": "openai/gpt-4o-mini",  # 问题分析
            "imagery_generation": "openai/gpt-5",  # 意象生成
            "final_interpretation": "openai/gpt-5",  # 最终解读
        },
        ModelPreset.GPT4OMINI_FAST: {
            "question_analysis": "openai/gpt-4o-mini",  # 问题分析
            "imagery_generation": "openai/gpt-4o-mini",  # ⚡ 意象生成（快速）
            "final_interpretation": "openai/gpt-4o-mini",  # ⚡ 最终解读（快速 - 全部使用 gpt-4o-mini）
        },
        ModelPreset.DEEPSEEK_R1_V3: {
            "question_analysis": "deepseek/deepseek-chat-v3",  # 问题分析
            "imagery_generation": "deepseek/deepseek-r1",  # 意象生成
            "final_interpretation": "deepseek/deepseek-r1",  # 最终解读
        },
        ModelPreset.DEEPSEEK_FAST: {
            "question_analysis": "deepseek/deepseek-chat",  # 问题分析
            "imagery_generation": "deepseek/deepseek-chat",  # ⚡ 意象生成（快速）
            "final_interpretation": "deepseek/deepseek-chat",  # ⚡ 最终解读（快速）
        },
        ModelPreset.GEMINI_25PRO_15: {
            "question_analysis": "google/gemini-2.5-flash",  # 问题分析 (快速响应，结构化输出)
            "imagery_generation": "google/gemini-2.5-pro",  # 意象生成 (高创造性)
            "final_interpretation": "google/gemini-2.5-pro",  # 最终解读 (深度推理)
        }
    }
    
    def __init__(self, preset: Optional[ModelPreset] = None):
        """
        初始化模型配置
        
        Args:
            preset: 模型预设，如果为None则从环境变量读取
        """
        if preset is None:
            # 从环境变量读取预设（如果存在）
            preset_str = getattr(settings, 'model_preset', 'gpt4omini_fast')
            try:
                preset = ModelPreset(preset_str.lower())
            except ValueError:
                # 如果环境变量值无效，使用默认值：gpt4omini_fast（快速模式 + DeepSeek R1 解读）
                preset = ModelPreset.GPT4OMINI_FAST
        
        self.preset = preset
        self.models = self.PRESETS[preset].copy()
    
    def get_model(self, task: str) -> str:
        """
        获取指定任务的模型名称
        
        Args:
            task: 任务类型 ('question_analysis', 'imagery_generation', 'final_interpretation')
            
        Returns:
            模型名称（如果使用OpenRouter，返回完整路径；否则返回模型名）
        """
        model_name = self.models.get(task)
        if not model_name:
            raise ValueError(f"Unknown task: {task}")
        
        # 如果使用OpenRouter，返回完整路径；否则返回模型名（去掉provider前缀）
        if settings.use_openrouter:
            return model_name
        else:
            # 去掉provider前缀（如 "openai/gpt-4o-mini" -> "gpt-4o-mini"）
            if '/' in model_name:
                return model_name.split('/', 1)[1]
            return model_name
    
    @property
    def question_analysis_model(self) -> str:
        """获取问题分析模型"""
        return self.get_model("question_analysis")
    
    @property
    def imagery_generation_model(self) -> str:
        """获取意象生成模型"""
        return self.get_model("imagery_generation")
    
    @property
    def final_interpretation_model(self) -> str:
        """获取最终解读模型"""
        return self.get_model("final_interpretation")
    
    def __repr__(self) -> str:
        return f"ModelConfig(preset={self.preset.value}, models={self.models})"


# 全局模型配置实例
_model_config: Optional[ModelConfig] = None


def get_model_config() -> ModelConfig:
    """获取全局模型配置实例"""
    global _model_config
    if _model_config is None:
        _model_config = ModelConfig()
    return _model_config


def set_model_config(preset: ModelPreset) -> None:
    """设置全局模型配置（用于测试）"""
    global _model_config
    _model_config = ModelConfig(preset)


def reset_model_config() -> None:
    """重置全局模型配置（用于测试）"""
    global _model_config
    _model_config = None

