#!/usr/bin/env python3
"""
简单测试脚本：检查意象描述流式输出
"""
import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.services.tarot.reading_service import ReadingService
from backend.app.core.config import settings

async def test_imagery_stream():
    """测试意象描述流式输出"""
    print("=" * 80)
    print("测试意象描述流式输出")
    print("=" * 80)
    
    from backend.app.core.database import get_supabase_service
    supabase = get_supabase_service()
    service = ReadingService(supabase=supabase)
    
    print("\n开始创建占卜（流式输出）...")
    print("问题: 我的工作会有什么变化？")
    print()
    
    imagery_chunks_received = False
    imagery_generated_received = False
    interpretation_chunks = 0
    
    async for update in service.create_reading_stream(
        question="我的工作会有什么变化？",
        user_id=None,
        user_selected_spread='three_card',
        preferred_source='pkt'
    ):
        update_type = update.get('type')
        
        if update_type == 'progress':
            step = update.get('step', 'unknown')
            message = update.get('data', {}).get('message', '')
            print(f"📊 [{step}] {message}")
            
            if step == 'imagery_generated':
                imagery_generated_received = True
                print("✅ 收到 imagery_generated 事件")
        
        elif update_type == 'imagery_chunk':
            if not imagery_chunks_received:
                print("\n🖼️ 开始接收意象描述流式输出:")
                imagery_chunks_received = True
            print(update.get('text', ''), end='', flush=True)
        
        elif update_type == 'interpretation':
            interpretation_chunks += 1
            if interpretation_chunks == 1:
                print("\n\n📝 开始接收最终解读流式输出:")
            print(update.get('text', ''), end='', flush=True)
        
        elif update_type == 'complete':
            print("\n\n✅ 占卜完成")
            break
        
        elif update_type == 'error':
            print(f"\n❌ 错误: {update.get('error')}")
            break
    
    print("\n")
    print("=" * 80)
    print("测试结果:")
    print(f"  意象描述chunk数: {'✅ 收到' if imagery_chunks_received else '❌ 未收到'}")
    print(f"  imagery_generated事件: {'✅ 收到' if imagery_generated_received else '❌ 未收到'}")
    print(f"  解读chunk数: {interpretation_chunks}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_imagery_stream())

