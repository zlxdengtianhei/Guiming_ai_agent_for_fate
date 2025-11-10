"""
测试不同模型的生成速度
"""

import asyncio
import time
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
import openai


async def test_model_speed(model_name: str, prompt: str, max_tokens: int = 500):
    """测试单个模型的生成速度"""
    
    print(f"\n{'='*80}")
    print(f"测试模型: {model_name}")
    print(f"{'='*80}")
    
    if settings.use_openrouter and settings.openrouter_api_key:
        api_key = settings.openrouter_api_key
        base_url = "https://openrouter.ai/api/v1"
        default_headers = {
            "HTTP-Referer": "https://github.com/yourusername/tarot_agent",
            "X-Title": "Tarot Agent"
        }
    else:
        api_key = settings.openai_api_key
        base_url = None
        default_headers = {}
    
    client = openai.OpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers=default_headers if default_headers else None
    )
    
    try:
        # 测试流式生成
        print(f"开始时间: {time.strftime('%H:%M:%S')}")
        start_time = time.time()
        
        stream = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=max_tokens,
            stream=True
        )
        
        first_token_time = None
        token_count = 0
        full_text = ""
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                if first_token_time is None:
                    first_token_time = time.time()
                    print(f"首个token延迟: {(first_token_time - start_time):.2f}秒")
                
                content = chunk.choices[0].delta.content
                full_text += content
                token_count += len(content.split())
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"结束时间: {time.strftime('%H:%M:%S')}")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"生成内容长度: {len(full_text)} 字符")
        print(f"大约 {token_count} tokens")
        print(f"速度: {len(full_text)/total_time:.1f} 字符/秒")
        print(f"\n生成内容（前200字符）:")
        print(full_text[:200])
        
        return {
            'model': model_name,
            'total_time': total_time,
            'first_token_time': first_token_time - start_time if first_token_time else None,
            'length': len(full_text),
            'speed': len(full_text)/total_time
        }
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return None


async def main():
    """测试多个模型"""
    
    # 准备一个中等长度的prompt（模拟真实场景）
    prompt = """You are an experienced Tarot reader. Based on the following cards, provide a brief interpretation (about 3-5 sentences):

1. The Fool (upright) - Past position
2. The Magician (upright) - Present position  
3. The High Priestess (reversed) - Future position

Question domain: career

Please provide an insightful and meaningful interpretation."""
    
    print("\n" + "="*80)
    print("模型速度对比测试")
    print("="*80)
    print(f"\nPrompt长度: {len(prompt)} 字符")
    print(f"请求生成: 约500 tokens")
    
    # 测试的模型列表
    models = [
        "openai/gpt-4o-mini",           # 快速且便宜
        "deepseek/deepseek-chat",       # DeepSeek最新版本
        "google/gemini-2.0-flash-exp",  # Google最快的模型
        # "openai/gpt-5",                # 慢但质量高（注释掉避免浪费时间）
    ]
    
    results = []
    
    for model in models:
        try:
            result = await test_model_speed(model, prompt, max_tokens=500)
            if result:
                results.append(result)
            await asyncio.sleep(2)  # 避免API限流
        except Exception as e:
            print(f"模型 {model} 测试失败: {e}")
    
    # 输出对比结果
    print("\n" + "="*80)
    print("速度对比总结")
    print("="*80)
    
    if results:
        # 按速度排序
        results.sort(key=lambda x: x['total_time'])
        
        print(f"\n{'模型':<35} {'总耗时':<12} {'首token':<10} {'速度':<15}")
        print("-" * 80)
        
        for r in results:
            model_name = r['model'].split('/')[-1][:30]
            total = f"{r['total_time']:.2f}秒"
            first = f"{r['first_token_time']:.2f}秒" if r['first_token_time'] else "N/A"
            speed = f"{r['speed']:.1f} 字符/秒"
            print(f"{model_name:<35} {total:<12} {first:<10} {speed:<15}")
        
        # 计算最快和最慢的差异
        if len(results) > 1:
            fastest = results[0]['total_time']
            slowest = results[-1]['total_time']
            speedup = slowest / fastest
            print(f"\n⚡ 最快的模型比最慢的快 {speedup:.1f}x")
            print(f"⚡ 如果156秒的任务用最快模型: ~{156/speedup:.1f}秒")


if __name__ == "__main__":
    asyncio.run(main())




