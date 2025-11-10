#!/usr/bin/env python3
"""
阿里云视觉智能开放平台 - 图像分割抠图工具（简化版）

使用方法:
    python3 database/scripts/image_segmentation_simple.py \
        --image /path/to/image.png \
        --output /path/to/output.png \
        --type hd_common  # 可选: common, hd_common, body

注意：
    需要配置 ALIYUN_ACCESS_KEY_ID 和 ALIYUN_ACCESS_KEY_SECRET
    获取方式: https://ram.console.aliyun.com/manage/ak
"""
import os
import sys
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any
import argparse

try:
    from alibabacloud_imageseg20191230.client import Client as imageseg20191230Client
    from alibabacloud_tea_openapi import models as open_api_models
    from alibabacloud_imageseg20191230 import models as imageseg_20191230_models
    from alibabacloud_tea_util import models as util_models
    import requests
    from dotenv import load_dotenv
except ImportError as e:
    print("❌ 需要安装依赖库")
    print("   运行: pip install alibabacloud-imageseg20191230 alibabacloud-tea-openapi alibabacloud-tea-util requests python-dotenv")
    print(f"   错误: {e}")
    sys.exit(1)

# 加载环境变量
backend_dir = Path(__file__).parent.parent.parent / "backend"
env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(env_file)


class AliyunImageSegmentation:
    """阿里云图像分割客户端"""
    
    def __init__(self, access_key_id: str, access_key_secret: str, region: str = "cn-shanghai"):
        """
        初始化客户端
        
        Args:
            access_key_id: 阿里云AccessKey ID
            access_key_secret: 阿里云AccessKey Secret
            region: 区域（固定为cn-shanghai）
        """
        config = open_api_models.Config(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            region_id=region,
            type='access_key'
        )
        # 视觉智能开放平台分割抠图API仅支持cn-shanghai区域
        config.endpoint = 'imageseg.cn-shanghai.aliyuncs.com'
        self.client = imageseg20191230Client(config)
    
    def wait_for_async_result(
        self,
        job_id: str,
        max_wait_time: int = 60,
        poll_interval: int = 2
    ) -> Dict[str, Any]:
        """等待异步任务完成并获取结果"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                request = imageseg_20191230_models.GetAsyncJobResultRequest(job_id=job_id)
                runtime = util_models.RuntimeOptions()
                runtime.read_timeout = 10000
                runtime.connect_timeout = 5000
                
                response = self.client.get_async_job_result_with_options(request, runtime)
                
                if not response or not response.body or not response.body.data:
                    time.sleep(poll_interval)
                    continue
                
                status = response.body.data.status
                
                if status == "PROCESS_SUCCESS":
                    result_str = response.body.data.result
                    if result_str:
                        result_data = json.loads(result_str)
                        image_url = (
                            result_data.get('ImageURL') or 
                            result_data.get('ImageUrl') or 
                            result_data.get('imageURL') or 
                            result_data.get('imageUrl') or
                            result_data.get('image_url')
                        )
                        if image_url:
                            return {
                                "success": True,
                                "image_url": image_url,
                                "request_id": job_id
                            }
                    return {
                        "success": False,
                        "error": f"任务成功但未找到图像URL。结果: {result_str}"
                    }
                elif status == "PROCESS_FAILED":
                    error_code = response.body.data.error_code
                    error_message = response.body.data.error_message
                    return {
                        "success": False,
                        "error": f"任务失败: {error_code} - {error_message}"
                    }
                elif status in ["PROCESSING", "QUEUEING"]:
                    elapsed = time.time() - start_time
                    print(f"   ⏳ 任务处理中... (已等待 {elapsed:.1f}秒)")
                    time.sleep(poll_interval)
                    continue
                else:
                    return {
                        "success": False,
                        "error": f"未知任务状态: {status}"
                    }
                    
            except Exception as e:
                print(f"   ⚠️  查询任务状态时出错: {e}")
                time.sleep(poll_interval)
                continue
        
        return {
            "success": False,
            "error": f"任务超时（超过 {max_wait_time} 秒）"
        }
    
    def segment_hd_common_image(self, image_path: Path) -> Dict[str, Any]:
        """通用高清分割 - 输出PNG格式透明图"""
        # 检查文件大小（API限制40MB）
        file_size = image_path.stat().st_size
        if file_size > 40 * 1024 * 1024:
            return {
                "success": False,
                "error": f"图像文件过大 ({file_size / 1024 / 1024:.2f}MB)，请压缩到40MB以下"
            }
        
        try:
            with open(image_path, 'rb') as f:
                request = imageseg_20191230_models.SegmentHDCommonImageAdvanceRequest(
                    image_url_object=f
                )
                runtime = util_models.RuntimeOptions()
                runtime.read_timeout = 60000
                runtime.connect_timeout = 10000
                
                response = self.client.segment_hdcommon_image_advance(request, runtime)
                
                if not response or not response.body:
                    return {"success": False, "error": "API返回空响应"}
                
                request_id = response.body.request_id if hasattr(response.body, 'request_id') else None
                
                if not hasattr(response.body, 'data') or response.body.data is None:
                    if request_id:
                        print(f"   ℹ️  检测到异步调用，任务ID: {request_id}")
                        print(f"   🔄 开始查询任务结果...")
                        return self.wait_for_async_result(request_id)
                    else:
                        return {"success": False, "error": "API返回数据为空"}
                
                image_url = response.body.data.image_url if hasattr(response.body.data, 'image_url') else None
                if not image_url:
                    return {"success": False, "error": "响应中未找到image_url"}
                
                return {
                    "success": True,
                    "image_url": image_url,
                    "request_id": request_id
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def download_segmented_image(self, image_url: str, output_path: Path) -> bool:
        """下载分割后的图像"""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return True
        except Exception as e:
            print(f"   ❌ 下载失败: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(description="阿里云图像分割抠图工具")
    parser.add_argument("--image", required=True, help="输入图像路径")
    parser.add_argument("--output", help="输出图像路径（默认：原图同目录，文件名加_segmented后缀）")
    parser.add_argument("--type", default="hd_common", choices=["hd_common"], help="分割类型（目前只支持hd_common）")
    
    args = parser.parse_args()
    
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"❌ 图像文件不存在: {image_path}")
        sys.exit(1)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = image_path.parent / f"{image_path.stem}_segmented.png"
    
    print(f"📷 输入图像: {image_path}")
    print(f"💾 输出路径: {output_path}")
    print(f"🔧 分割类型: {args.type}\n")
    
    # 初始化客户端
    access_key_id = os.getenv("ALIYUN_ACCESS_KEY_ID", "").strip()
    access_key_secret = os.getenv("ALIYUN_ACCESS_KEY_SECRET", "").strip()
    
    if not access_key_id or not access_key_secret:
        print("❌ 请配置 ALIYUN_ACCESS_KEY_ID 和 ALIYUN_ACCESS_KEY_SECRET 环境变量")
        print("   获取方式: https://ram.console.aliyun.com/manage/ak")
        sys.exit(1)
    
    client = AliyunImageSegmentation(access_key_id, access_key_secret)
    print("✅ 阿里云客户端初始化成功\n")
    
    # 执行分割
    start_time = time.time()
    result = client.segment_hd_common_image(image_path)
    elapsed_time = time.time() - start_time
    
    if not result.get("success"):
        print(f"❌ 分割失败: {result.get('error')}")
        sys.exit(1)
    
    image_url = result.get("image_url")
    request_id = result.get("request_id")
    
    print(f"✅ 分割成功 (耗时: {elapsed_time:.2f}秒)")
    print(f"   Request ID: {request_id}")
    print(f"   结果图像 URL: {image_url}\n")
    
    # 下载图像
    print(f"⬇️  下载分割后的图像...")
    if client.download_segmented_image(image_url, output_path):
        file_size = output_path.stat().st_size / 1024
        print(f"✅ 图像已保存: {output_path}")
        print(f"   文件大小: {file_size:.2f} KB")
    else:
        print(f"❌ 下载失败")
        sys.exit(1)
    
    print(f"\n🎉 完成！")


if __name__ == "__main__":
    main()




