#!/usr/bin/env python3
"""
批量生成塔罗牌图片脚本
为 pkt_tarot_cards.json 中每张卡片的 description 生成图片
"""

import os
import sys
import json
import time
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


class AliyunText2Image:
    """阿里云通义万相文生图API客户端"""
    
    def __init__(self, api_key: Optional[str] = None, region: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            api_key: DashScope API Key
            region: 地域，beijing 或 singapore
        """
        self.api_key = (api_key or os.getenv("ALIYUN_DASHSCOPE_API_KEY", "")).strip()
        if not self.api_key:
            raise ValueError("需要设置 ALIYUN_DASHSCOPE_API_KEY 环境变量或传入 api_key 参数")
        
        # 如果没有指定 region，从环境变量读取，默认使用 singapore
        if region is None:
            region = os.getenv("ALIYUN_DASHSCOPE_REGION", "singapore")
        
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
        """创建文生图任务"""
        headers = {
            "X-DashScope-Async": "enable",
            "Authorization": f"Bearer {self.api_key.strip()}",
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
        
        if kwargs:
            payload["parameters"].update(kwargs)
        
        try:
            response = requests.post(
                self.create_task_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # 检查 401 错误，提供更详细的提示
            if response.status_code == 401:
                error_detail = response.json() if response.text else {}
                error_code = error_detail.get("code", "")
                error_msg = error_detail.get("message", "")
                
                print(f"❌ API Key 认证失败 (401)")
                print(f"   错误代码: {error_code}")
                print(f"   错误信息: {error_msg}")
                print(f"\n💡 请检查:")
                print(f"   1. API Key 是否正确（当前: {self.api_key[:10]}...{self.api_key[-4:]})")
                print(f"   2. Region 是否正确（当前: {self.region}）")
                print(f"      💡 提示: 如果当前 region 无效，请尝试另一个 region")
                print(f"      - 在 .env 中设置: ALIYUN_DASHSCOPE_REGION=beijing 或 singapore")
                print(f"   3. 是否已开通通义万相文生图服务")
                print(f"   4. API Key 是否有权限访问文生图服务")
                print(f"   5. 获取 API Key: https://help.aliyun.com/zh/model-studio/get-api-key")
                
                response.raise_for_status()
            
            response.raise_for_status()
            result = response.json()
            
            task_id = result.get("output", {}).get("task_id")
            if task_id:
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
        """查询任务状态"""
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
        """等待任务完成并返回结果"""
        start_time = time.time()
        
        while True:
            elapsed_time = time.time() - start_time
            if elapsed_time > max_wait_time:
                print(f"❌ 超时: 等待时间超过 {max_wait_time}秒")
                return {"error": "timeout"}
            
            result = self.query_task(task_id)
            task_status = result.get("output", {}).get("task_status")
            
            if task_status == "SUCCEEDED":
                return result
            elif task_status == "FAILED":
                print(f"❌ 任务失败")
                print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
            elif task_status in ["PENDING", "RUNNING"]:
                time.sleep(poll_interval)
            else:
                print(f"⚠️  未知状态: {task_status}")
                print(f"   响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result
    
    def download_image(self, image_url: str, save_path: Path) -> bool:
        """下载图片到本地"""
        try:
            response = requests.get(image_url, timeout=60, stream=True)
            response.raise_for_status()
            
            # 确保目录存在
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存图片
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            return False


class Dalle3ImageGenerator:
    """OpenAI DALL-E 3 图片生成客户端（支持 OpenAI 和 OpenRouter）"""
    
    def __init__(self, api_key: Optional[str] = None, use_openrouter: bool = False):
        """
        初始化客户端
        
        Args:
            api_key: OpenAI API Key 或 OpenRouter API Key
            use_openrouter: 是否使用 OpenRouter
        """
        if not openai:
            raise ValueError("需要安装 openai 库才能使用 DALL-E 3")
        
        if use_openrouter:
            self.api_key = (api_key or os.getenv("OPENROUTER_API_KEY", "")).strip()
            if not self.api_key:
                raise ValueError("使用 OpenRouter 需要设置 OPENROUTER_API_KEY 环境变量")
            base_url = "https://openrouter.ai/api/v1"
            default_headers = {
                "HTTP-Referer": "https://github.com/yourusername/tarot_agent",
                "X-Title": "Tarot Agent"
            }
            self.model = "openai/dall-e-3"  # OpenRouter 模型名称
        else:
            self.api_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
            if not self.api_key:
                raise ValueError("需要设置 OPENAI_API_KEY 环境变量或传入 api_key 参数")
            base_url = None  # OpenAI 默认 base_url
            default_headers = {}
            self.model = "dall-e-3"  # OpenAI 模型名称
        
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=base_url,
            default_headers=default_headers if default_headers else None
        )
    
    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1792",
        quality: str = "hd",
        style: str = "vivid"
    ) -> Dict[str, Any]:
        """
        生成图片
        
        Args:
            prompt: 文本提示词
            size: 图片尺寸，支持 "1024x1024", "1024x1792", "1792x1024"
            quality: 图片质量，"standard" 或 "hd"
            style: 风格，"vivid" 或 "natural"
        
        Returns:
            包含图片 URL 的响应字典
        """
        try:
            print(f"📤 使用 OpenRouter DALL-E 3 生成图片...")
            print(f"   Prompt 长度: {len(prompt)} 字符")
            print(f"   尺寸: {size}")
            print(f"   质量: {quality}")
            print(f"   风格: {style}")
            
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=1  # DALL-E 3 只支持生成 1 张图片
            )
            
            image_url = response.data[0].url
            revised_prompt = getattr(response.data[0], 'revised_prompt', None)
            
            print(f"✅ 图片生成成功")
            print(f"   图片 URL: {image_url[:80]}...")
            if revised_prompt:
                print(f"   DALL-E 3 优化后的 Prompt: {revised_prompt[:100]}...")
            
            return {
                "url": image_url,
                "revised_prompt": revised_prompt
            }
            
        except Exception as e:
            print(f"❌ 生成失败: {e}")
            raise
    
    def download_image(self, image_url: str, save_path: Path) -> bool:
        """下载图片到本地"""
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


def generate_all_card_images(
    start_index: int = 0,
    end_index: Optional[int] = None,
    test_mode: bool = False,
    use_dalle3: bool = False
):
    """
    为所有卡片生成图片
    
    Args:
        start_index: 开始索引（用于断点续传）
        end_index: 结束索引（None表示处理到最后）
        test_mode: 测试模式，只处理第一张卡片
        use_dalle3: 是否使用 OpenRouter DALL-E 3（否则使用阿里云）
    """
    print("\n" + "="*60)
    print("批量生成塔罗牌图片")
    print("="*60)
    
    # 选择使用的 API
    if use_dalle3:
        print("\n🎨 使用 OpenAI DALL-E 3 API")
        # 注意：OpenRouter 目前不支持 DALL-E 3 images API，需要使用 OpenAI API Key
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not openai_key:
            print("❌ 错误: 未设置 OPENAI_API_KEY 环境变量")
            print("   注意: OpenRouter 目前不支持 DALL-E 3 images API")
            print("   请直接在 backend/.env 文件中设置 OPENAI_API_KEY")
            print("   获取 API Key: https://platform.openai.com/api-keys")
            return
        
        print("   使用 OpenAI API Key")
        print(f"\n✅ API Key 已设置: {openai_key[:10]}...{openai_key[-4:]}")
        
        try:
            client = Dalle3ImageGenerator(api_key=openai_key, use_openrouter=False)
        except Exception as e:
            print(f"❌ 初始化 DALL-E 3 客户端失败: {e}")
            return
    else:
        print("\n🎨 使用阿里云通义万相文生图 API")
        # 检查阿里云 API Key
        api_key = os.getenv("ALIYUN_DASHSCOPE_API_KEY")
        if not api_key:
            print("❌ 错误: 未设置 ALIYUN_DASHSCOPE_API_KEY 环境变量")
            print("   请在 backend/.env 文件中设置 ALIYUN_DASHSCOPE_API_KEY")
            return
        
        print(f"\n✅ API Key 已设置: {api_key[:10]}...{api_key[-4:]}")
        
        # 获取地域配置
        region = os.getenv("ALIYUN_DASHSCOPE_REGION", "singapore")  # 默认使用 singapore
        print(f"✅ 地域: {region}")
        if not region:
            print("⚠️  警告: 未设置 ALIYUN_DASHSCOPE_REGION，默认使用 singapore")
            print("   如果 API key 无效，请尝试设置 ALIYUN_DASHSCOPE_REGION=beijing 或 singapore")
        
        try:
            client = AliyunText2Image(api_key=api_key, region=region)
        except Exception as e:
            print(f"❌ 初始化阿里云客户端失败: {e}")
            return
    
    # 读取JSON文件
    json_path = project_root / "database" / "data" / "pkt_tarot_cards.json"
    if not json_path.exists():
        print(f"❌ 文件不存在: {json_path}")
        return
    
    print(f"\n📖 读取卡片数据: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        cards = json.load(f)
    
    if not cards:
        print("❌ JSON文件为空")
        return
    
    total_cards = len(cards)
    print(f"✅ 共找到 {total_cards} 张卡片")
    
    # 确定处理范围
    if test_mode:
        cards_to_process = cards[:1]
        print(f"\n🧪 测试模式：只处理第一张卡片")
    else:
        if end_index is None:
            end_index = total_cards
        cards_to_process = cards[start_index:end_index]
        print(f"\n📋 处理范围: 第 {start_index + 1} 到 {end_index} 张卡片")
        print(f"   共 {len(cards_to_process)} 张卡片")
    
    # 准备保存目录
    output_dir = project_root / "database" / "images"
    output_dir.mkdir(exist_ok=True)
    print(f"\n📁 图片保存目录: {output_dir}")
    
    # 塔罗牌比例：2:3 (经典卡牌比例)
    if use_dalle3:
        # DALL-E 3 支持的尺寸：1024x1024, 1024x1792, 1792x1024
        # 使用 1024x1792 接近 2:3 比例
        tarot_size = "1024x1792"
    else:
        tarot_size = "768*1152"  # 2:3 比例
    
    # 统计信息
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    # 处理每张卡片
    for idx, card in enumerate(cards_to_process, start=start_index + 1):
        card_name_en = card.get("card_name_en", "Unknown")
        card_name_cn = card.get("card_name_cn", "未知")
        card_number = card.get("card_number", 0)
        description = card.get("description", "")
        
        print(f"\n{'='*60}")
        print(f"处理卡片 {idx}/{total_cards}: {card_name_en} ({card_name_cn})")
        print(f"{'='*60}")
        
        # 检查是否已有图片
        safe_name = card_name_en.replace(" ", "_").replace("'", "").replace("/", "_")
        filename = f"{safe_name}.png"
        save_path = output_dir / filename
        
        if save_path.exists():
            print(f"⏭️  图片已存在，跳过: {save_path.name}")
            skipped_count += 1
            continue
        
        if not description:
            print(f"⚠️  卡片没有描述信息，跳过")
            skipped_count += 1
            continue
        
        try:
            # 构建 prompt：添加风格描述（全英文）
            # 推荐使用的详细版 style_prompt
            style_prompt = "Tarot card illustration in a highly abstract, mystical, and fantastical 2D art style. Features stylized and symbolic figures, avoiding any realistic human features. The scene is imbued with a surreal, dreamlike quality and a magical, arcane atmosphere. The composition seamlessly fuses geometric patterns, esoteric symbols, and otherworldly elements, while maintaining a moderate complexity and a clear, balanced structure. Use minimal yet dramatic lighting to create an ethereal glow. The emphasis is on symbolic representation to evoke a sense of wonder, fantasy, and profound mystery."
            full_prompt = f"{description} {style_prompt}"
            
            if use_dalle3:
                # 使用 DALL-E 3 生成图片
                print(f"📤 使用 DALL-E 3 生成图片...")
                print(f"   Prompt 长度: {len(full_prompt)} 字符")
                
                result = client.generate_image(
                    prompt=full_prompt,
                    size=tarot_size,
                    quality="hd",  # 使用高质量
                    style="vivid"  # 使用生动风格
                )
                
                image_url = result.get("url", "")
                revised_prompt = result.get("revised_prompt")
                if revised_prompt:
                    print(f"   DALL-E 3 优化后的 Prompt: {revised_prompt[:100]}...")
                
                if image_url:
                    # 下载图片
                    print(f"📥 下载图片...")
                    if client.download_image(image_url, save_path):
                        file_size = save_path.stat().st_size
                        print(f"✅ 成功！图片已保存")
                        print(f"   文件: {save_path.name}")
                        print(f"   大小: {file_size / 1024:.2f} KB")
                        success_count += 1
                    else:
                        print(f"❌ 下载失败")
                        fail_count += 1
                else:
                    print(f"❌ 未找到图片URL")
                    fail_count += 1
            else:
                # 使用阿里云 API
                print(f"📤 创建生成任务...")
                print(f"   Prompt 长度: {len(full_prompt)} 字符")
                create_result = client.create_task(
                    prompt=full_prompt,
                    model="wan2.5-t2i-preview",
                    size=tarot_size,
                    n=1
                )
                
                task_id = create_result.get("output", {}).get("task_id")
                if not task_id:
                    print(f"❌ 无法获取 task_id")
                    fail_count += 1
                    continue
                
                # 等待结果
                print(f"⏳ 等待任务完成...")
                result = client.wait_for_result(task_id, max_wait_time=300, poll_interval=5)
                
                task_status = result.get("output", {}).get("task_status")
                
                if task_status == "SUCCEEDED":
                    results = result.get("output", {}).get("results", [])
                    if results:
                        img_result = results[0]
                        image_url = img_result.get('url', '')
                        
                        if image_url:
                            # 下载图片
                            print(f"📥 下载图片...")
                            if client.download_image(image_url, save_path):
                                file_size = save_path.stat().st_size
                                print(f"✅ 成功！图片已保存")
                                print(f"   文件: {save_path.name}")
                                print(f"   大小: {file_size / 1024:.2f} KB")
                                success_count += 1
                            else:
                                print(f"❌ 下载失败")
                                fail_count += 1
                        else:
                            print(f"❌ 未找到图片URL")
                            fail_count += 1
                    else:
                        print(f"❌ 任务完成但未返回结果")
                        fail_count += 1
                else:
                    print(f"❌ 任务失败，状态: {task_status}")
                    fail_count += 1
                
                # 显示使用情况（仅阿里云 API）
                usage = result.get("usage", {})
                if usage:
                    print(f"   使用情况: 生成图片数 {usage.get('image_count', 0)}")
            
            # 避免请求过快，添加延迟
            if idx < len(cards_to_process):
                print(f"⏸️  等待 2 秒后处理下一张...")
                time.sleep(2)
        
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            fail_count += 1
    
    # 显示最终统计
    print(f"\n{'='*60}")
    print("处理完成统计")
    print(f"{'='*60}")
    print(f"✅ 成功: {success_count} 张")
    print(f"❌ 失败: {fail_count} 张")
    print(f"⏭️  跳过: {skipped_count} 张")
    print(f"📁 图片保存目录: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="批量生成塔罗牌图片")
    parser.add_argument("--test", action="store_true", help="测试模式：只处理第一张卡片")
    parser.add_argument("--start", type=int, default=0, help="开始索引（用于断点续传）")
    parser.add_argument("--end", type=int, default=None, help="结束索引（默认处理到最后）")
    parser.add_argument("--dalle3", action="store_true", help="使用 OpenRouter DALL-E 3 API（否则使用阿里云）")
    
    args = parser.parse_args()
    
    generate_all_card_images(
        start_index=args.start,
        end_index=args.end,
        test_mode=args.test,
        use_dalle3=args.dalle3
    )

