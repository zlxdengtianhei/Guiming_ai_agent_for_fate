#!/usr/bin/env python3
"""
阿里云通义万相文生图API测试脚本
在test目录下运行: python3 test_aliyun_text2image.py
"""

import os
import sys
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import requests
except ImportError:
    print("❌ 需要安装 requests 库")
    print("   运行: pip install requests")
    sys.exit(1)

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

# 加载环境变量
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️  警告: .env 文件不存在，使用环境变量")


class AliyunText2Image:
    """阿里云通义万相文生图API客户端"""
    
    def __init__(self, api_key: Optional[str] = None, region: str = "beijing"):
        """
        初始化客户端
        
        Args:
            api_key: DashScope API Key
            region: 地域，beijing 或 singapore
        """
        self.api_key = api_key or os.getenv("ALIYUN_DASHSCOPE_API_KEY")
        if not self.api_key:
            raise ValueError("需要设置 ALIYUN_DASHSCOPE_API_KEY 环境变量或传入 api_key 参数")
        
        self.region = region.lower()
        if self.region == "beijing":
            self.base_url = "https://dashscope.aliyuncs.com/api/v1"
        elif self.region == "singapore":
            self.base_url = "https://dashscope-intl.aliyuncs.com/api/v1"
        else:
            raise ValueError("region 必须是 'beijing' 或 'singapore'")
        
        self.create_task_url = f"{self.base_url}/services/aigc/text2image/image-synthesis"
        self.query_task_url = f"{self.base_url}/tasks"
    
    def create_task(
        self,
        prompt: str,
        model: str = "wan2.5-t2i-preview",
        size: str = "1024*1024",
        n: int = 1,
        negative_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建文生图任务
        
        Args:
            prompt: 文本提示词
            model: 模型名称，默认 wan2.5-t2i-preview
            size: 图像尺寸，格式如 "1024*1024"
            n: 生成图像数量，默认1
            negative_prompt: 反向提示词（可选）
            **kwargs: 其他参数
        
        Returns:
            包含 task_id 的响应字典
        """
        headers = {
            "X-DashScope-Async": "enable",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "input": {
                "prompt": prompt
            },
            "parameters": {
                "size": size,
                "n": n
            }
        }
        
        if negative_prompt:
            payload["input"]["negative_prompt"] = negative_prompt
        
        # 添加其他参数
        if kwargs:
            payload["parameters"].update(kwargs)
        
        print(f"📤 创建任务中...")
        print(f"   提示词: {prompt}")
        print(f"   模型: {model}")
        print(f"   尺寸: {size}")
        
        try:
            response = requests.post(
                self.create_task_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            task_id = result.get("output", {}).get("task_id")
            if task_id:
                print(f"✅ 任务创建成功")
                print(f"   Task ID: {task_id}")
                return result
            else:
                print(f"❌ 任务创建失败: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
                
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"   错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
                except:
                    print(f"   响应内容: {e.response.text}")
            raise
    
    def query_task(self, task_id: str) -> Dict[str, Any]:
        """
        查询任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态和结果
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.query_task_url}/{task_id}"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ 查询任务失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"   错误详情: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
                except:
                    print(f"   响应内容: {e.response.text}")
            raise
    
    def wait_for_result(
        self,
        task_id: str,
        max_wait_time: int = 300,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """
        等待任务完成并返回结果
        
        Args:
            task_id: 任务ID
            max_wait_time: 最大等待时间（秒），默认300秒（5分钟）
            poll_interval: 轮询间隔（秒），默认5秒
        
        Returns:
            任务结果
        """
        start_time = time.time()
        print(f"\n⏳ 等待任务完成...")
        print(f"   最大等待时间: {max_wait_time}秒")
        print(f"   轮询间隔: {poll_interval}秒")
        
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                print(f"❌ 超时: 等待时间超过 {max_wait_time}秒")
                return {"error": "timeout"}
            
            result = self.query_task(task_id)
            task_status = result.get("output", {}).get("task_status")
            
            if task_status == "SUCCEEDED":
                print(f"✅ 任务完成！耗时: {elapsed_time:.1f}秒")
                return result
            elif task_status == "FAILED":
                print(f"❌ 任务失败")
                print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            elif task_status in ["PENDING", "RUNNING"]:
                print(f"   状态: {task_status} (已等待 {elapsed_time:.1f}秒)")
                time.sleep(poll_interval)
            else:
                print(f"⚠️  未知状态: {task_status}")
                print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
    
    def download_image(self, image_url: str, save_path: Path) -> bool:
        """
        下载图片到本地
        
        Args:
            image_url: 图片URL
            save_path: 保存路径
        
        Returns:
            是否下载成功
        """
        try:
            print(f"\n📥 下载图片中...")
            print(f"   URL: {image_url[:80]}...")
            print(f"   保存路径: {save_path}")
            
            response = requests.get(image_url, timeout=60, stream=True)
            response.raise_for_status()
            
            # 确保目录存在
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存图片
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = save_path.stat().st_size
            print(f"✅ 图片下载成功")
            print(f"   文件大小: {file_size / 1024:.2f} KB")
            print(f"   保存位置: {save_path.absolute()}")
            return True
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            return False


def test_basic():
    """基础测试"""
    print("\n" + "="*60)
    print("阿里云通义万相文生图API测试")
    print("="*60)
    
    # 检查API Key
    api_key = os.getenv("ALIYUN_DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 错误: 未设置 ALIYUN_DASHSCOPE_API_KEY 环境变量")
        print("   请在 backend/.env 文件中设置 ALIYUN_DASHSCOPE_API_KEY")
        return
    
    print(f"\n✅ API Key 已设置: {api_key[:10]}...{api_key[-4:]}")
    
    # 获取地域配置
    region = os.getenv("ALIYUN_DASHSCOPE_REGION", "beijing")
    print(f"✅ 地域: {region}")
    
    try:
        # 初始化客户端
        client = AliyunText2Image(api_key=api_key, region=region)
        
        # 测试提示词
        test_prompt = "一间有着精致窗户的花店，漂亮的木质门，摆放着花朵"
        
        # 塔罗牌比例：2:3 (经典卡牌比例)
        # 可选尺寸：768*1152 (2:3), 800*1200 (2:3), 1024*1536 (2:3)
        # 注意：总像素需要在 [768*768, 1440*1440] 之间
        # 图片格式：API 输出为 PNG 格式，无法更改
        tarot_size = "768*1152"  # 2:3 比例，总像素 884736，在允许范围内
        
        # 创建任务
        create_result = client.create_task(
            prompt=test_prompt,
            model="wan2.5-t2i-preview",
            size=tarot_size,
            n=1
        )
        
        task_id = create_result.get("output", {}).get("task_id")
        if not task_id:
            print("❌ 无法获取 task_id")
            return
        
        # 等待结果
        result = client.wait_for_result(task_id, max_wait_time=300, poll_interval=5)
        
        # 显示结果
        print("\n" + "="*60)
        print("任务结果")
        print("="*60)
        
        task_status = result.get("output", {}).get("task_status")
        print(f"状态: {task_status}")
        
        if task_status == "SUCCEEDED":
            results = result.get("output", {}).get("results", [])
            if results:
                print(f"\n✅ 成功生成 {len(results)} 张图片")
                
                # 准备保存目录
                result_dir = Path(__file__).parent / "result"
                result_dir.mkdir(exist_ok=True)
                
                for i, img_result in enumerate(results, 1):
                    print(f"\n图片 {i}:")
                    print(f"  原始提示词: {img_result.get('orig_prompt', 'N/A')}")
                    print(f"  实际提示词: {img_result.get('actual_prompt', 'N/A')}")
                    image_url = img_result.get('url', '')
                    print(f"  图片URL: {image_url}")
                    
                    # 下载图片
                    if image_url:
                        # 生成文件名：使用时间戳和任务ID
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        filename = f"aliyun_text2image_{timestamp}_{i}.png"
                        save_path = result_dir / filename
                        
                        # 下载图片
                        client.download_image(image_url, save_path)
            
            # 显示使用情况
            usage = result.get("usage", {})
            if usage:
                print(f"\n使用情况:")
                print(f"  生成图片数: {usage.get('image_count', 0)}")
        else:
            print(f"\n❌ 任务未成功完成")
            print(f"完整响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_with_negative_prompt():
    """测试使用反向提示词"""
    print("\n" + "="*60)
    print("测试：使用反向提示词")
    print("="*60)
    
    api_key = os.getenv("ALIYUN_DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 错误: 未设置 ALIYUN_DASHSCOPE_API_KEY 环境变量")
        return
    
    region = os.getenv("ALIYUN_DASHSCOPE_REGION", "beijing")
    
    try:
        client = AliyunText2Image(api_key=api_key, region=region)
        
        prompt = "雪地，白色小教堂，极光，冬日场景，柔和的光线。"
        negative_prompt = "人物"
        
        # 塔罗牌比例：2:3
        tarot_size = "768*1152"
        
        create_result = client.create_task(
            prompt=prompt,
            negative_prompt=negative_prompt,
            model="wan2.2-t2i-flash",
            size=tarot_size,
            n=1
        )
        
        task_id = create_result.get("output", {}).get("task_id")
        if task_id:
            result = client.wait_for_result(task_id)
            task_status = result.get("output", {}).get("task_status")
            if task_status == "SUCCEEDED":
                print("✅ 反向提示词测试成功")
            else:
                print(f"⚠️  任务状态: {task_status}")
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    # 运行基础测试
    test_basic()
    
    # 可选：运行反向提示词测试
    # test_with_negative_prompt()
