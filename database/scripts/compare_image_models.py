#!/usr/bin/env python3
"""
图像生成模型对比脚本
使用相同的 prompt 测试不同的图像生成模型，并保存结果到对比文件夹
"""

import os
import sys
import json
import time
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    import requests
except ImportError:
    print("❌ 需要安装 requests 库")
    print("   运行: pip install requests")
    sys.exit(1)

try:
    import openai
except ImportError:
    print("⚠️  警告: 未安装 openai 库，无法使用 DALL-E 3")
    print("   如需使用 DALL-E 3，请运行: pip install openai")

# 添加backend目录到路径
project_root = Path(__file__).parent.parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

# 加载环境变量
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️  警告: .env 文件不存在，使用环境变量")


def get_openai_org_id() -> Optional[str]:
    """从环境变量或 .env 文件读取 OpenAI Organization ID"""
    org_id = os.getenv("OPENAI_ORG_ID", "").strip()
    
    if not org_id and env_path.exists():
        import re
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
        match = re.search(r'^OPENAI_ORG_ID=(.+)$', content, re.MULTILINE)
        if match:
            org_id = match.group(1).strip().strip('"').strip("'")
    
    return org_id if org_id else None


class ImageGenerator:
    """图像生成器基类"""
    
    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成图片，返回包含图片数据的字典"""
        raise NotImplementedError
    
    def download_image(self, image_data: Any, save_path: Path) -> bool:
        """保存图片到本地"""
        raise NotImplementedError


class AliyunGenerator(ImageGenerator):
    """阿里云通义万相文生图"""
    
    def __init__(self, model: str = "wan2.5-t2i-preview"):
        """
        初始化阿里云生成器
        
        Args:
            model: 模型名称，可选值：
                - wan2.5-t2i-preview: 通义万相 2.5 预览版（默认）
                - wan2.1-t2i-turbo: 通义万相 2.1 极速版
                - wan2.1-t2i-plus: 通义万相 2.1 专业版
        """
        api_key = os.getenv("ALIYUN_DASHSCOPE_API_KEY", "").strip()
        if not api_key:
            raise ValueError("需要设置 ALIYUN_DASHSCOPE_API_KEY")
        
        region = os.getenv("ALIYUN_DASHSCOPE_REGION", "singapore")
        if region == "beijing":
            self.base_url = "https://dashscope.aliyuncs.com/api/v1"
        else:
            self.base_url = "https://dashscope-intl.aliyuncs.com/api/v1"
        
        self.api_key = api_key
        self.model = model
        self.create_task_url = f"{self.base_url}/services/aigc/text2image/image-synthesis"
        self.query_task_url = f"{self.base_url}/tasks"
    
    def create_task(self, prompt: str, size: str = "768*1152") -> str:
        """创建任务并返回 task_id"""
        headers = {
            "X-DashScope-Async": "enable",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": {"prompt": prompt},
            "parameters": {"size": size, "n": 1}
        }
        
        response = requests.post(self.create_task_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result.get("output", {}).get("task_id")
    
    def wait_for_result(self, task_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """等待任务完成"""
        start_time = time.time()
        while True:
            if time.time() - start_time > max_wait_time:
                return {"error": "timeout"}
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            response = requests.get(f"{self.query_task_url}/{task_id}", headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            task_status = result.get("output", {}).get("task_status")
            if task_status == "SUCCEEDED":
                return result
            elif task_status == "FAILED":
                return {"error": "failed", "result": result}
            
            time.sleep(5)
    
    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成图片"""
        size = kwargs.get("size", "768*1152")
        task_id = self.create_task(prompt, size)
        result = self.wait_for_result(task_id)
        
        if "error" in result:
            raise Exception(f"任务失败: {result.get('error')}")
        
        results = result.get("output", {}).get("results", [])
        if not results:
            raise Exception("未返回结果")
        
        image_url = results[0].get("url", "")
        if not image_url:
            raise Exception("未找到图片URL")
        
        return {"url": image_url, "type": "url"}
    
    def download_image(self, image_data: Any, save_path: Path) -> bool:
        """下载图片"""
        image_url = image_data.get("url")
        if not image_url:
            return False
        
        response = requests.get(image_url, timeout=60, stream=True)
        response.raise_for_status()
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True


class Dalle3Generator(ImageGenerator):
    """OpenAI DALL-E 3"""
    
    def __init__(self):
        if not openai:
            raise ValueError("需要安装 openai 库")
        
        # 尝试从环境变量读取 OPENAI_API_KEY
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        
        # 如果环境变量中没有，尝试直接从 .env 文件读取
        if not api_key:
            import re
            env_file = backend_dir / ".env"
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                match = re.search(r'^OPENAI_API_KEY=(.+)$', content, re.MULTILINE)
                if match:
                    api_key = match.group(1).strip().strip('"').strip("'")
        
        if not api_key:
            raise ValueError("需要设置 OPENAI_API_KEY")
        
        # 读取 organization ID
        org_id = get_openai_org_id()
        client_kwargs = {"api_key": api_key}
        if org_id:
            client_kwargs["organization"] = org_id
        
        self.client = openai.OpenAI(**client_kwargs)
        self.model = "dall-e-3"
    
    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成图片"""
        size = kwargs.get("size", "1024x1792")
        quality = kwargs.get("quality", "hd")
        style = kwargs.get("style", "vivid")
        n = kwargs.get("n", 1)
        
        # DALL-E 3 只支持 n=1，强制设置为 1
        if n > 1:
            print(f"   ⚠️  注意：DALL-E 3 只支持生成 1 张图片，将忽略 n={n} 参数")
            n = 1
        
        # DALL-E 3 API 调用（只生成 1 张）
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,
            quality=quality,
            style=style,
            n=1  # DALL-E 3 只支持 n=1
        )
        
        image_url = response.data[0].url
        revised_prompt = getattr(response.data[0], 'revised_prompt', None)
        
        return {
            "url": image_url,
            "revised_prompt": revised_prompt,
            "type": "url"
        }
    
    def download_image(self, image_data: Any, save_path: Path) -> bool:
        """下载图片（支持单张或多张）"""
        # 处理多张图片的情况
        if image_data.get("type") == "url_multiple":
            image_urls = image_data.get("url_list", [])
            if not image_urls:
                return False
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            base_name = save_path.stem
            extension = save_path.suffix
            parent_dir = save_path.parent
            
            for idx, image_url in enumerate(image_urls):
                response = requests.get(image_url, timeout=60, stream=True)
                response.raise_for_status()
                
                if len(image_urls) > 1:
                    # 多张图片：添加序号
                    multi_path = parent_dir / f"{base_name}_{idx+1}{extension}"
                else:
                    multi_path = save_path
                
                with open(multi_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            return True
        
        # 处理单张图片的情况
        image_url = image_data.get("url")
        if not image_url:
            return False
        
        response = requests.get(image_url, timeout=60, stream=True)
        response.raise_for_status()
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True


class GPT5ImageGenerator(ImageGenerator):
    """OpenAI GPT-5 Image 系列（使用 Responses API）"""
    
    def __init__(self, model: str = "gpt-5"):
        """
        初始化 GPT-5 Image 生成器
        
        Args:
            model: 模型名称，可选值：
                - "gpt-5" - GPT-5 Image（标准版）
                - "gpt-5-mini" - GPT-5 Image Mini（Mini 版）
        """
        if not openai:
            raise ValueError("需要安装 openai 库")
        
        # 尝试从环境变量读取 OPENAI_API_KEY
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        
        # 如果环境变量中没有，尝试直接从 .env 文件读取
        if not api_key:
            import re
            env_file = backend_dir / ".env"
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                match = re.search(r'^OPENAI_API_KEY=(.+)$', content, re.MULTILINE)
                if match:
                    api_key = match.group(1).strip().strip('"').strip("'")
        
        if not api_key:
            raise ValueError(
                "需要设置 OPENAI_API_KEY\n"
                "请在 backend/.env 文件中添加：OPENAI_API_KEY=your_key_here\n"
                "或者设置为系统环境变量：export OPENAI_API_KEY=your_key_here"
            )
        
        # 读取 organization ID
        org_id = get_openai_org_id()
        client_kwargs = {"api_key": api_key}
        if org_id:
            client_kwargs["organization"] = org_id
        
        self.client = openai.OpenAI(**client_kwargs)
        self.model = model
    
    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成图片（使用 Responses API）
        
        Args:
            prompt: 文本提示词
            **kwargs: 额外参数
                - size: 图片尺寸，支持 "1024x1024", "1024x1536", "1536x1024"（默认: "1024x1536"）
                - quality: 图片质量，"low", "medium", "high"（默认: "high"）
                - n: 生成图片数量（默认: 1）
                注意：GPT-5 Image 系列使用 Responses API，一次请求只能生成一张图片
                如需生成多张，需要多次调用或使用 batch API
        """
        size = kwargs.get("size", "1024x1536")  # 默认使用竖屏 2:3 比例
        quality = kwargs.get("quality", "high")
        n = kwargs.get("n", 1)
        
        if n > 1:
            print(f"   ⚠️  注意：GPT-5 Image 系列一次请求只能生成 1 张图片")
            print(f"   如需生成 {n} 张，需要调用 {n} 次 API 或使用 batch API")
        
        print(f"   使用 OpenAI Responses API 生成图片")
        print(f"   模型: {self.model}")
        print(f"   尺寸: {size} ({'2:3 竖屏' if size == '1024x1536' else '3:2 横屏' if size == '1536x1024' else '1:1 正方形'})")
        print(f"   质量: {quality}")
        
        # 使用 Responses API
        # 注意：GPT-5 Image 系列一次请求只能生成 1 张图片
        # 如果需要多张，需要多次调用
        images_base64 = []
        for i in range(n):
            if n > 1:
                print(f"   生成第 {i+1}/{n} 张图片...")
            
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
                tools=[{
                    "type": "image_generation",
                    "size": size,
                    "quality": quality
                }]
            )
            
            # 从响应中提取图片数据
            image_data = [
                output.result
                for output in response.output
                if output.type == "image_generation_call"
            ]
            
            if not image_data:
                raise Exception(f"第 {i+1} 张图片生成失败：未找到生成的图片数据")
            
            images_base64.append(image_data[0])
        
        # 如果只生成一张，返回单张格式；否则返回多张格式
        if n == 1:
            return {
                "b64_json": images_base64[0],
                "type": "base64"
            }
        else:
            return {
                "b64_json_list": images_base64,
                "type": "base64_multiple",
                "count": len(images_base64)
            }
    
    def download_image(self, image_data: Any, save_path: Path) -> bool:
        """保存 base64 图片（支持单张或多张）"""
        # 处理多张图片的情况
        if image_data.get("type") == "base64_multiple":
            images_base64 = image_data.get("b64_json_list", [])
            if not images_base64:
                return False
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            # 保存多张图片，文件名添加序号
            base_name = save_path.stem
            extension = save_path.suffix
            parent_dir = save_path.parent
            
            for idx, image_base64 in enumerate(images_base64):
                image_bytes = base64.b64decode(image_base64)
                if len(images_base64) > 1:
                    # 多张图片：添加序号
                    multi_path = parent_dir / f"{base_name}_{idx+1}{extension}"
                else:
                    multi_path = save_path
                with open(multi_path, 'wb') as f:
                    f.write(image_bytes)
            return True
        
        # 处理单张图片的情况
        image_base64 = image_data.get("b64_json")
        if not image_base64:
            return False
        
        image_bytes = base64.b64decode(image_base64)
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        return True


class GPTImageGenerator(ImageGenerator):
    """OpenAI GPT-Image-1 系列（直接使用 OpenAI API）"""
    
    def __init__(self, model: str = "gpt-image-1"):
        """
        初始化 GPT-Image 生成器
        
        Args:
            model: 模型名称，可选值：
                - "gpt-image-1" - GPT-Image-1（标准版）
                - "gpt-image-1-mini" - GPT-Image-1 Mini（Mini 版）
        """
        if not openai:
            raise ValueError("需要安装 openai 库")
        
        # 尝试从环境变量读取 OPENAI_API_KEY
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        
        # 如果环境变量中没有，尝试直接从 .env 文件读取
        if not api_key:
            import re
            env_file = backend_dir / ".env"
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                match = re.search(r'^OPENAI_API_KEY=(.+)$', content, re.MULTILINE)
                if match:
                    api_key = match.group(1).strip().strip('"').strip("'")
        
        if not api_key:
            raise ValueError(
                "需要设置 OPENAI_API_KEY\n"
                "请在 backend/.env 文件中添加：OPENAI_API_KEY=your_key_here\n"
                "或者设置为系统环境变量：export OPENAI_API_KEY=your_key_here"
            )
        
        # 读取 organization ID
        org_id = get_openai_org_id()
        client_kwargs = {"api_key": api_key}
        if org_id:
            client_kwargs["organization"] = org_id
        
        self.client = openai.OpenAI(**client_kwargs)
        self.model = model
    
    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成图片
        
        Args:
            prompt: 文本提示词
            **kwargs: 额外参数
                - size: 图片尺寸，支持 "1024x1024", "1024x1536", "1536x1024"（默认: "1024x1536"）
                  注意：1024x1536 是 2:3 竖屏，1536x1024 是 3:2 横屏
                - quality: 图片质量，"low", "medium", "high"（默认: "high"）
                - n: 生成图片数量，1-10（默认: 1）
        """
        # 根据模型设置默认质量
        if "mini" in self.model.lower():
            default_quality = "medium"  # GPT-Image-1-Mini 默认质量是 medium
        else:
            default_quality = "high"  # GPT-Image-1 默认质量是 high
        
        size = kwargs.get("size", "1024x1536")  # 默认使用竖屏 2:3 比例 (1024×1536)
        quality = kwargs.get("quality", default_quality)
        n = kwargs.get("n", 1)
        
        print(f"   使用 OpenAI API 生成图片")
        print(f"   模型: {self.model}")
        print(f"   尺寸: {size} ({'2:3 竖屏' if size == '1024x1536' else '3:2 横屏' if size == '1536x1024' else '1:1 正方形'})")
        print(f"   质量: {quality}")
        
        response = self.client.images.generate(
            model=self.model,
            prompt=prompt,
            size=size,
            quality=quality,
            n=n
        )
        
        # GPT-Image-1 返回 base64 编码的图片
        # 如果 n > 1，返回多张图片
        if n > 1:
            images_base64 = [item.b64_json for item in response.data]
            return {
                "b64_json_list": images_base64,
                "type": "base64_multiple",
                "count": len(images_base64)
            }
        else:
            image_base64 = response.data[0].b64_json
            return {
                "b64_json": image_base64,
                "type": "base64"
            }
    
    def download_image(self, image_data: Any, save_path: Path) -> bool:
        """保存 base64 图片（支持单张或多张）"""
        # 处理多张图片的情况
        if image_data.get("type") == "base64_multiple":
            images_base64 = image_data.get("b64_json_list", [])
            if not images_base64:
                return False
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            # 保存多张图片，文件名添加序号
            base_name = save_path.stem
            extension = save_path.suffix
            parent_dir = save_path.parent
            
            for idx, image_base64 in enumerate(images_base64):
                image_bytes = base64.b64decode(image_base64)
                if len(images_base64) > 1:
                    # 多张图片：添加序号
                    multi_path = parent_dir / f"{base_name}_{idx+1}{extension}"
                else:
                    multi_path = save_path
                with open(multi_path, 'wb') as f:
                    f.write(image_bytes)
            return True
        
        # 处理单张图片的情况
        image_base64 = image_data.get("b64_json")
        if not image_base64:
            return False
        
        image_bytes = base64.b64decode(image_base64)
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'wb') as f:
            f.write(image_bytes)
        return True


class OpenRouterImageGenerator(ImageGenerator):
    """OpenRouter 图像生成模型（使用 chat/completions API）"""
    
    def __init__(self, model_id: str):
        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise ValueError("需要设置 OPENROUTER_API_KEY")
        
        if not openai:
            raise ValueError("需要安装 openai 库")
        
        self.model_id = model_id
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/yourusername/tarot_agent",
                "X-Title": "Tarot Agent"
            }
        )
    
    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成图片
        
        Args:
            prompt: 文本提示词
            **kwargs: 额外参数
                - aspect_ratio: 图片比例，例如 "3:2", "16:9", "1:1", "2:3" 等
                  支持的 Gemini 模型比例：
                  - 1:1 (1024×1024, 默认)
                  - 2:3 (832×1248，或 GPT-5 Image Mini 的 1024×1536)
                  - 3:2 (1248×832)
                  - 3:4 (864×1184)
                  - 4:3 (1184×864)
                  - 4:5 (896×1152)
                  - 5:4 (1152×896)
                  - 9:16 (768×1344)
                  - 16:9 (1344×768)
                  - 21:9 (1536×672)
        """
        try:
            aspect_ratio = kwargs.get("aspect_ratio")
            
            # 检测是否是 GPT-5 Image 系列模型
            is_gpt5_image = "gpt-5-image" in self.model_id.lower()
            
            # 对于 GPT-5 Image 系列，如果没有指定 aspect_ratio，默认使用 2:3（竖屏 1024×1536）
            if is_gpt5_image and not aspect_ratio:
                aspect_ratio = "2:3"
                print(f"   检测到 GPT-5 Image 模型，自动使用竖屏比例 2:3 (1024×1536)")
            
            # 对于 GPT-5 Image 系列，在 prompt 中添加尺寸要求
            # 注意：OpenRouter 的 GPT-5 Image 系列可能不支持通过 image_config 设置尺寸
            # 因此需要在 prompt 中非常明确地指定尺寸要求
            final_prompt = prompt
            if is_gpt5_image and aspect_ratio == "2:3":
                # 在 prompt 开头和末尾都添加明确的尺寸要求
                # 使用多种表达方式确保模型理解
                size_note_start = "CRITICAL: You MUST generate this image with EXACT dimensions: width 1024 pixels, height 1536 pixels (portrait orientation, 2:3 aspect ratio). "
                size_note_end = " REMINDER: The final image MUST be exactly 1024 pixels wide and 1536 pixels tall (portrait, 2:3 ratio). Do NOT generate a square image."
                if not prompt.startswith(size_note_start):
                    final_prompt = size_note_start + prompt + size_note_end
                    print(f"   已在 prompt 中添加尺寸要求: 1024×1536 (portrait)")
                elif not prompt.endswith(size_note_end):
                    final_prompt = prompt + size_note_end
                    print(f"   已在 prompt 末尾添加尺寸要求: 1024×1536 (portrait)")
            
            # 对于 GPT-5 Image 系列，尝试使用工具调用的方式
            # 根据调试信息，GPT-5 Image 使用 tool_calls 来生成图片
            use_tool_calls = is_gpt5_image
            
            # 如果指定了 aspect_ratio 或者是 GPT-5 Image 模型，直接使用 requests 发送请求
            # （因为 OpenAI SDK 可能不支持 image_config，且 GPT-5 Image 需要特殊参数）
            if aspect_ratio or is_gpt5_image:
                import requests
                api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/yourusername/tarot_agent",
                    "X-Title": "Tarot Agent"
                }
                
                payload = {
                    "model": self.model_id,
                    "messages": [
                        {"role": "user", "content": final_prompt}
                    ],
                    "modalities": ["image", "text"]
                }
                
                # 根据模型类型设置不同的参数
                if is_gpt5_image:
                    # GPT-5 Image 系列：根据 OpenRouter 文档，应该使用 image_config.aspect_ratio
                    # 参考：https://openrouter.ai/docs/features/multimodal/image-generation
                    # 注意：GPT-5 Image 可能不支持直接设置 size，需要通过 aspect_ratio
                    if aspect_ratio == "2:3":
                        # 使用 aspect_ratio 参数（OpenRouter 推荐方式）
                        payload["image_config"] = {
                            "aspect_ratio": "2:3"
                        }
                        # 同时尝试在 prompt 中明确指定（已在上面添加）
                    elif aspect_ratio == "3:2":
                        payload["image_config"] = {
                            "aspect_ratio": "3:2"
                        }
                    else:
                        # 其他比例，使用 aspect_ratio
                        payload["image_config"] = {
                            "aspect_ratio": aspect_ratio
                        }
                else:
                    # 其他模型（如 Gemini）：使用 aspect_ratio
                    payload["image_config"] = {
                        "aspect_ratio": aspect_ratio
                    }
                
                response_obj = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=120
                )
                response_obj.raise_for_status()
                response_dict = response_obj.json()
                
                # 调试：打印请求和响应结构（仅在前几次调用时，用于调试）
                # 对于 GPT-5 Image (非 Mini)，打印完整响应以便调试
                if is_gpt5_image and "mini" not in self.model_id.lower():
                    debug_key = f'_debug_printed_{self.model_id}'
                    if not hasattr(self, debug_key):
                        print(f"   [调试] GPT-5 Image 响应结构: {json.dumps(response_dict, indent=2, ensure_ascii=False)[:1000]}...")
                        setattr(self, debug_key, True)
                
                # 将响应转换为类似 OpenAI SDK 的格式
                class MockMessage:
                    def __init__(self, content, images, tool_calls=None):
                        self.content = content
                        self.images = images
                        self.tool_calls = tool_calls
                
                class MockChoice:
                    def __init__(self, message):
                        self.message = message
                
                class MockResponse:
                    def __init__(self, choices):
                        self.choices = choices
                
                choices_data = response_dict.get("choices", [])
                if not choices_data:
                    raise Exception("响应中未找到 choices")
                
                message_data = choices_data[0].get("message", {})
                images_data = message_data.get("images", [])
                tool_calls_data = message_data.get("tool_calls", [])
                
                # 创建模拟的响应对象
                mock_message = MockMessage(
                    content=message_data.get("content", ""),
                    images=images_data,
                    tool_calls=tool_calls_data
                )
                mock_choice = MockChoice(mock_message)
                response = MockResponse([mock_choice])
            else:
                # 没有指定 aspect_ratio，使用 OpenAI SDK
                request_params = {
                    "model": self.model_id,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "modalities": ["image", "text"]
                }
                response = self.client.chat.completions.create(**request_params)
            
            message = response.choices[0].message
            
            # 检查响应格式
            image_data_url = None
            
            # 处理使用 requests 时的响应（images 是字典列表）
            if hasattr(message, 'images') and message.images:
                image_obj = message.images[0]
                if isinstance(image_obj, dict):
                    image_data_url = image_obj.get('image_url', {}).get('url', '')
                elif hasattr(image_obj, 'image_url'):
                    if isinstance(image_obj.image_url, dict):
                        image_data_url = image_obj.image_url.get('url', '')
                    else:
                        image_data_url = image_obj.image_url.url
                else:
                    raise Exception(f"未知的图片格式: {type(image_obj)}")
            
            # 处理 OpenAI SDK 的响应格式
            elif hasattr(message, 'content') and isinstance(message.content, list):
                for item in message.content:
                    if hasattr(item, 'type') and item.type == 'image_url':
                        if hasattr(item, 'image_url'):
                            if isinstance(item.image_url, dict):
                                image_data_url = item.image_url.get('url', '')
                            else:
                                image_data_url = item.image_url.url
                        break
                if not image_data_url:
                    raise Exception("未找到图片数据")
            
            # 尝试从原始响应中提取
            if not image_data_url:
                response_dict = response_dict if 'response_dict' in locals() else (response.model_dump() if hasattr(response, 'model_dump') else {})
                choices = response_dict.get('choices', [])
                if choices:
                    message_dict = choices[0].get('message', {})
                    images = message_dict.get('images', [])
                    if images:
                        image_data_url = images[0].get('image_url', {}).get('url', '')
                    else:
                        raise Exception("响应中未找到图片数据")
                else:
                    raise Exception("响应格式异常")
            
            if not image_data_url:
                raise Exception("图片 URL 为空")
            
            return {
                "data_url": image_data_url,
                "type": "base64"
            }
        except Exception as e:
            raise Exception(f"OpenRouter 生成失败: {e}")
    
    def download_image(self, image_data: Any, save_path: Path) -> bool:
        """保存 base64 图片"""
        data_url = image_data.get("data_url")
        if not data_url:
            return False
        
        # 解析 data URL: data:image/png;base64,...
        if data_url.startswith("data:image"):
            header, encoded = data_url.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'wb') as f:
                f.write(image_bytes)
            return True
        return False


def get_available_openrouter_models() -> List[Dict[str, str]]:
    """获取 OpenRouter 可用的图像生成模型"""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return []
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=30)
        if response.status_code != 200:
            return []
        
        models = response.json().get("data", [])
        image_models = []
        
        for model in models:
            arch = model.get("architecture", {})
            output_modalities = arch.get("output_modalities", [])
            if "image" in output_modalities:
                image_models.append({
                    "id": model.get("id"),
                    "name": model.get("name", model.get("id")),
                    "description": model.get("description", "")[:100]
                })
        
        return image_models
    except Exception as e:
        print(f"⚠️  获取 OpenRouter 模型列表失败: {e}")
        return []


def compare_models(
    prompt: str,
    models_to_test: List[str],
    output_dir: Path,
    aspect_ratio: Optional[str] = None,
    n: int = 1
):
    """
    对比不同模型的图像生成效果
    
    Args:
        prompt: 测试用的 prompt
        models_to_test: 要测试的模型列表，格式: ["aliyun", "dalle3", "openrouter:model_id"]
        output_dir: 输出目录
        aspect_ratio: 图片比例（仅对支持的 OpenRouter 模型有效），例如 "3:2", "16:9" 等
    """
    print("\n" + "="*60)
    print("图像生成模型对比测试")
    print("="*60)
    print(f"\n测试 Prompt:")
    print(f"{prompt[:200]}...")
    print(f"\nPrompt 长度: {len(prompt)} 字符")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存 prompt 到文件
    prompt_file = output_dir / "test_prompt.txt"
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    print(f"\n📁 Prompt 已保存到: {prompt_file}")
    
    results = []
    
    for model_spec in models_to_test:
        print(f"\n{'='*60}")
        print(f"测试模型: {model_spec}")
        print(f"{'='*60}")
        
        try:
            # 初始化生成器
            if model_spec == "aliyun":
                generator = AliyunGenerator()
                model_name = "Aliyun_Wan2.5"
            elif model_spec.startswith("aliyun:"):
                # 支持指定阿里云模型，例如: aliyun:wan2.1-t2i-plus
                model_id = model_spec.split(":", 1)[1]
                generator = AliyunGenerator(model=model_id)
                model_name = f"Aliyun_{model_id.replace('-', '_').replace('.', '_')}"
            elif model_spec == "dalle3":
                generator = Dalle3Generator()
                model_name = "DALL-E_3"
            elif model_spec == "gpt-image-1" or model_spec == "gpt-image-1-mini":
                # 直接使用 OpenAI API 的 GPT-Image-1 系列
                generator = GPTImageGenerator(model=model_spec)
                model_name = model_spec.replace("-", "_")
            elif model_spec == "gpt-5-image" or model_spec == "gpt-5-image-mini":
                # GPT-5 Image 系列使用 OpenAI Responses API
                # 映射：gpt-5-image -> gpt-5, gpt-5-image-mini -> gpt-5-mini
                openai_model = "gpt-5" if model_spec == "gpt-5-image" else "gpt-5-mini"
                generator = GPT5ImageGenerator(model=openai_model)
                model_name = model_spec.replace("-", "_")
            elif model_spec.startswith("openrouter:"):
                model_id = model_spec.split(":", 1)[1]
                # 如果是 GPT-5 Image 系列，使用 OpenAI API 而不是 OpenRouter
                if model_id in ["openai/gpt-5-image", "openai/gpt-5-image-mini"]:
                    # 提取模型名称并映射到 OpenAI API 模型名
                    if "mini" in model_id:
                        openai_model = "gpt-5-mini"
                    else:
                        openai_model = "gpt-5"
                    generator = GPT5ImageGenerator(model=openai_model)
                    model_name = model_id.replace("/", "_").replace(":", "_").replace("openai_", "")
                else:
                    # 其他 OpenRouter 模型（如 Gemini）继续使用 OpenRouter
                    generator = OpenRouterImageGenerator(model_id)
                    model_name = model_id.replace("/", "_").replace(":", "_")
            else:
                print(f"❌ 未知的模型: {model_spec}")
                continue
            
            # 生成图片
            print(f"📤 生成图片中...")
            if model_spec in ["gpt-image-1", "gpt-image-1-mini"]:
                print(f"   使用 OpenAI Images API，默认尺寸: 1024×1536 (2:3 portrait)")
            elif model_spec in ["gpt-5-image", "gpt-5-image-mini"] or \
                 (model_spec.startswith("openrouter:") and "openai/gpt-5-image" in model_spec):
                print(f"   使用 OpenAI Responses API，默认尺寸: 1024×1536 (2:3 portrait)")
            elif aspect_ratio and model_spec.startswith("openrouter:"):
                print(f"   使用图片比例: {aspect_ratio}")
            start_time = time.time()
            if aspect_ratio and model_spec.startswith("openrouter:") and "openai/gpt-5-image" not in model_spec:
                # OpenRouter 模型（非 GPT-5 Image），使用 aspect_ratio
                image_data = generator.generate_image(prompt, aspect_ratio=aspect_ratio, n=n)
            elif model_spec in ["gpt-image-1", "gpt-image-1-mini"]:
                # GPT-Image-1 系列默认使用 1024x1536 (2:3 竖屏)
                if aspect_ratio == "2:3" or aspect_ratio is None:
                    size = "1024x1536"  # 2:3 竖屏
                elif aspect_ratio == "3:2":
                    size = "1536x1024"  # 3:2 横屏（注意：这是横屏，不是竖屏）
                else:
                    size = "1024x1536"  # 默认竖屏
                image_data = generator.generate_image(prompt, size=size, n=n)
            elif model_spec in ["gpt-5-image", "gpt-5-image-mini"] or \
                 (model_spec.startswith("openrouter:") and "openai/gpt-5-image" in model_spec):
                # GPT-5 Image 系列使用 Responses API，默认使用 1024x1536 (2:3 竖屏)
                if aspect_ratio == "2:3" or aspect_ratio is None:
                    size = "1024x1536"  # 2:3 竖屏
                elif aspect_ratio == "3:2":
                    size = "1536x1024"  # 3:2 横屏（注意：这是横屏，不是竖屏）
                else:
                    size = "1024x1536"  # 默认竖屏
                image_data = generator.generate_image(prompt, size=size, n=n)
            elif model_spec == "dalle3":
                # DALL-E 3 只支持 n=1，如果 n > 1 会多次调用 API
                image_data = generator.generate_image(prompt, n=n)
            else:
                image_data = generator.generate_image(prompt, n=n)
            elapsed_time = time.time() - start_time
            
            # 保存图片
            safe_model_name = model_name.replace(" ", "_").replace("/", "_")
            save_path = output_dir / f"{safe_model_name}.png"
            
            print(f"💾 保存图片到: {save_path.name}")
            success = generator.download_image(image_data, save_path)
            
            if success:
                # 检查是否生成了多张图片
                if image_data.get("type") in ["base64_multiple", "url_multiple"]:
                    count = image_data.get("count", 1)
                    print(f"✅ 成功生成 {count} 张图片！")
                    print(f"   耗时: {elapsed_time:.1f} 秒")
                    # 计算所有图片的总大小
                    total_size = 0
                    base_name = save_path.stem
                    extension = save_path.suffix
                    file_paths = []
                    for i in range(count):
                        if count > 1:
                            multi_path = save_path.parent / f"{base_name}_{i+1}{extension}"
                        else:
                            multi_path = save_path
                        if multi_path.exists():
                            total_size += multi_path.stat().st_size
                            file_paths.append(str(multi_path))
                    print(f"   总文件大小: {total_size / 1024:.2f} KB")
                    
                    results.append({
                        "model": model_spec,
                        "model_name": model_name,
                        "success": True,
                        "time": elapsed_time,
                        "file_size": total_size,
                        "file_path": str(save_path),
                        "image_count": count,
                        "file_paths": file_paths
                    })
                else:
                    file_size = save_path.stat().st_size
                    print(f"✅ 成功！")
                    print(f"   耗时: {elapsed_time:.1f} 秒")
                    print(f"   文件大小: {file_size / 1024:.2f} KB")
                    
                    results.append({
                        "model": model_spec,
                        "model_name": model_name,
                        "success": True,
                        "time": elapsed_time,
                        "file_size": file_size,
                        "file_path": str(save_path)
                    })
            else:
                print(f"❌ 保存失败")
                results.append({
                    "model": model_spec,
                    "model_name": model_name,
                    "success": False,
                    "error": "保存失败"
                })
            
            # 避免请求过快
            time.sleep(2)
        
        except Exception as e:
            print(f"❌ 失败: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "model": model_spec,
                "model_name": model_spec,
                "success": False,
                "error": str(e)
            })
    
    # 保存对比结果
    results_file = output_dir / "comparison_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "prompt": prompt,
            "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print("对比测试完成")
    print(f"{'='*60}")
    print(f"\n📊 测试结果:")
    success_count = sum(1 for r in results if r.get("success"))
    print(f"   成功: {success_count}/{len(results)}")
    print(f"   失败: {len(results) - success_count}/{len(results)}")
    print(f"\n📁 结果保存在: {output_dir}")
    print(f"   - 图片文件: {output_dir}/*.png")
    print(f"   - 对比结果: {results_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="图像生成模型对比测试")
    parser.add_argument("--prompt", type=str, help="测试用的 prompt（如果不提供，将使用默认的塔罗牌描述）")
    parser.add_argument("--models", type=str, nargs="+", 
                       help="要测试的模型列表，例如: aliyun dalle3 gpt-image-1-mini gpt-image-1 openrouter:google/gemini-2.5-flash-image-preview")
    parser.add_argument("--list-openrouter", action="store_true", help="列出 OpenRouter 可用的图像生成模型")
    parser.add_argument("--output", type=str, default=None, help="输出目录（默认: database/images/comparison_YYYYMMDD_HHMMSS）")
    parser.add_argument("--aspect-ratio", type=str, default=None,
                       help="图片比例，例如: 2:3 (竖屏), 3:2 (横屏), 16:9, 1:1 等。对于 GPT-Image-1 系列，支持 2:3 (1024x1536) 和 3:2 (1536x1024)")
    parser.add_argument("--n", type=int, default=1,
                       help="每个模型生成的图片数量（默认: 1，最大: 10）")
    
    args = parser.parse_args()
    
    # 列出 OpenRouter 模型
    if args.list_openrouter:
        print("\n查询 OpenRouter 可用的图像生成模型...")
        models = get_available_openrouter_models()
        if models:
            print(f"\n找到 {len(models)} 个支持图像生成的模型:\n")
            for i, model in enumerate(models, 1):
                print(f"{i}. {model['id']}")
                print(f"   名称: {model['name']}")
                print(f"   描述: {model['description']}")
                print()
        else:
            print("未找到可用的图像生成模型，请检查 OPENROUTER_API_KEY 是否正确设置")
        sys.exit(0)
    
    # 准备 prompt
    if args.prompt:
        test_prompt = args.prompt
    else:
        # 使用第一张塔罗牌的描述 + 风格描述
        json_path = project_root / "database" / "data" / "pkt_tarot_cards.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                cards = json.load(f)
            description = cards[0].get("description", "")
            # 推荐使用的详细版 style_prompt
            style_prompt = "Tarot card illustration in a highly abstract, mystical, and fantastical 2D art style. Features stylized and symbolic figures, avoiding any realistic human features. The scene is imbued with a surreal, dreamlike quality and a magical, arcane atmosphere. The composition seamlessly fuses geometric patterns, esoteric symbols, and otherworldly elements, while maintaining a moderate complexity and a clear, balanced structure. Use minimal yet dramatic lighting to create an ethereal glow. The emphasis is on symbolic representation to evoke a sense of wonder, fantasy, and profound mystery."
            test_prompt = f"{description} {style_prompt}"
        else:
            test_prompt = "A mysterious, abstract, dark 2D artwork with fantastical elements, featuring abstract symbolic human forms, occult atmosphere, and mystical symbols"
    
    # 准备要测试的模型
    if args.models:
        models_to_test = args.models
    else:
        # 默认测试列表：包含所有可用的模型
        models_to_test = []
        
        # 添加阿里云模型
        if os.getenv("ALIYUN_DASHSCOPE_API_KEY"):
            # 默认使用 wan2.5-t2i-preview
            models_to_test.append("aliyun")
            # 可选：添加其他阿里云模型进行对比
            # models_to_test.append("aliyun:wan2.1-t2i-turbo")
            # models_to_test.append("aliyun:wan2.1-t2i-plus")
        
        # 添加 DALL-E 3
        if os.getenv("OPENAI_API_KEY"):
            models_to_test.append("dalle3")
            # 添加 GPT-Image-1 系列（直接使用 OpenAI API）
            models_to_test.append("gpt-image-1-mini")
            models_to_test.append("gpt-image-1")
        
        # 添加所有可用的 OpenRouter 文生图模型
        if os.getenv("OPENROUTER_API_KEY"):
            openrouter_models = get_available_openrouter_models()
            if openrouter_models:
                print(f"\n找到 {len(openrouter_models)} 个 OpenRouter 文生图模型，将全部加入对比测试")
                for model in openrouter_models:
                    models_to_test.append(f"openrouter:{model['id']}")
            else:
                print("\n⚠️  未找到 OpenRouter 文生图模型，请检查 API Key 是否正确")
        
        if not models_to_test:
            print("\n❌ 错误: 未找到任何可用的模型")
            print("   请至少设置以下环境变量之一:")
            print("   - ALIYUN_DASHSCOPE_API_KEY (阿里云)")
            print("   - OPENAI_API_KEY (DALL-E 3)")
            print("   - OPENROUTER_API_KEY (OpenRouter)")
            sys.exit(1)
    
    # 准备输出目录
    if args.output:
        output_dir = Path(args.output)
    else:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = project_root / "database" / "images" / f"comparison_{timestamp}"
    
    # 运行对比测试
    n = max(1, min(args.n, 10))  # 限制在 1-10 之间
    if args.n != n:
        print(f"⚠️  警告: n 参数已调整为 {n}（必须在 1-10 之间）")
    compare_models(test_prompt, models_to_test, output_dir, aspect_ratio=args.aspect_ratio, n=n)

