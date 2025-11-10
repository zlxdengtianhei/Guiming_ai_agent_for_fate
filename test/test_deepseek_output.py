"""
测试 DeepSeek R1 的实际输出格式
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
import openai


async def test_deepseek_r1_output():
    """测试 DeepSeek R1 的实际输出格式"""
    
    print("\n" + "="*80)
    print("测试 DeepSeek R1 实际输出格式")
    print("="*80)
    
    if settings.use_openrouter and settings.openrouter_api_key:
        api_key = settings.openrouter_api_key
        base_url = "https://openrouter.ai/api/v1"
        default_headers = {
            "HTTP-Referer": "https://github.com/yourusername/tarot_agent",
            "X-Title": "Tarot Agent"
        }
    else:
        print("❌ 需要配置 OpenRouter API")
        return
    
    client = openai.OpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers=default_headers if default_headers else None
    )
    
    prompt = "请简短回答：塔罗牌中愚者牌的含义是什么？（请用1-2句话回答）"
    
    print(f"\nPrompt: {prompt}")
    print("\n" + "-"*80)
    print("开始流式输出...")
    print("-"*80 + "\n")
    
    try:
        stream = client.chat.completions.create(
            model="deepseek/deepseek-r1",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            stream=True
        )
        
        full_text = ""
        chunk_count = 0
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_text += content
                chunk_count += 1
                
                # 显示前10个chunk的原始内容
                if chunk_count <= 10:
                    print(f"Chunk {chunk_count}: {repr(content)}")
        
        print("\n" + "-"*80)
        print("完整输出:")
        print("-"*80)
        print(full_text)
        print("\n" + "-"*80)
        print(f"总共 {chunk_count} 个chunks")
        print(f"总长度: {len(full_text)} 字符")
        
        # 检查是否包含特殊标签
        if '<think>' in full_text:
            print("\n✅ 发现 <think> 标签")
            think_start = full_text.find('<think>')
            think_end = full_text.find('</think>')
            if think_end > think_start:
                print(f"   - Thinking内容长度: {think_end - think_start} 字符")
                print(f"   - Thinking内容（前100字符）:")
                print(f"     {full_text[think_start:think_start+100]}...")
                print(f"   - 最终答案（前200字符）:")
                answer = full_text[think_end+8:]  # 跳过 </think>
                print(f"     {answer[:200]}")
        else:
            print("\n❌ 未发现 <think> 标签")
            print("   模型可能直接输出答案，或使用其他格式")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_deepseek_r1_output())




