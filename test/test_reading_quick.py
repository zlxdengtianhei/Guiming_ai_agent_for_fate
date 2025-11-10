"""
快速测试占卜流程并记录时间
"""

import asyncio
import sys
import time
from pathlib import Path

# 添加backend目录到路径
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(backend_dir))

from app.services.tarot.reading_service import ReadingService
from app.models.schemas import UserProfileCreate


async def test_reading_quick():
    """快速测试占卜流程"""
    print("\n" + "="*80)
    print("快速测试：占卜流程时间分析")
    print("="*80)
    
    # 创建服务实例
    service = ReadingService()
    
    # 创建测试用户信息
    user_profile = UserProfileCreate(
        age=28,
        gender="female",
        zodiac_sign="Leo",
        appearance_type="wands",
        personality_type="wands",
        preferred_source="pkt"
    )
    
    question = "我最近的感情运势如何？"
    
    print(f"\n问题: {question}")
    print(f"开始时间: {time.strftime('%H:%M:%S')}")
    
    # 记录开始时间
    start_time = time.time()
    
    try:
        # 调用占卜服务
        result = await service.create_reading(
            question=question,
            user_id=None,
            user_selected_spread=None,
            user_profile=user_profile,
            preferred_source="pkt"
        )
        
        # 计算总时间
        total_time = time.time() - start_time
        
        print(f"\n✅ 占卜完成!")
        print(f"总耗时: {total_time:.2f}秒 ({total_time*1000:.0f}ms)")
        print(f"占卜ID: {result.get('reading_id')}")
        print(f"牌阵类型: {result.get('spread_type')}")
        print(f"选中的牌数: {len(result.get('cards', []))}")
        
        return result
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    asyncio.run(test_reading_quick())




