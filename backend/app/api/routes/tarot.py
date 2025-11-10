"""
Tarot reading endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import asyncio
from app.core.database import get_supabase, get_supabase_service
from app.services.tarot.reading_service import reading_service
from app.models.schemas import UserProfileCreate
from app.api.routes.auth import get_current_user

router = APIRouter()


class TarotReadingRequest(BaseModel):
    """Request model for tarot reading."""
    question: str
    user_selected_spread: Optional[str] = None  # three_card, celtic_cross, auto
    use_rag_for_pattern: Optional[bool] = False  # 是否使用RAG进行牌型分析
    preferred_source: Optional[str] = 'pkt'  # pkt, 78degrees
    user_profile: Optional[Dict[str, Any]] = None  # 用户信息（可选）
    source_page: Optional[str] = None  # 占卜来源页面：home, manual-input, spread-selection


class TarotReadingResponse(BaseModel):
    """Response model for tarot reading."""
    reading_id: str
    question: str
    question_analysis: Dict[str, Any]
    spread_type: str
    significator: Optional[Dict[str, Any]] = None
    cards: List[Dict[str, Any]]
    pattern_analysis: Dict[str, Any]
    interpretation: Dict[str, Any]
    metadata: Dict[str, Any]


@router.post("/reading", response_model=TarotReadingResponse)
async def create_tarot_reading(
    request: TarotReadingRequest,
    authorization: Optional[str] = Header(None)
):
    """
    创建新的塔罗占卜
    
    - **question**: 要问塔罗牌的问题
    - **user_selected_spread**: 用户指定的占卜方式（可选，默认auto）
    - **use_rag_for_pattern**: 是否使用RAG进行牌型分析（默认False）
    - **preferred_source**: 偏好的数据源（pkt或78degrees，默认pkt）
    - **user_profile**: 用户信息（可选，包含age、gender、zodiac_sign等）
    
    如果提供了Authorization header，占卜结果将保存到用户账户中。
    """
    try:
        # 获取当前用户（如果已登录）
        user_id = None
        user_profile_obj = None
        
        if authorization:
            try:
                current_user = get_current_user(authorization)
                user_id = current_user["id"]
                
                # 如果提供了user_profile，使用提供的；否则尝试从数据库获取
                if request.user_profile:
                    user_profile_obj = UserProfileCreate(**request.user_profile)
                else:
                    # 尝试从数据库获取用户信息
                    supabase = get_supabase_service()
                    profile_result = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
                    if profile_result.data:
                        profile_data = profile_result.data[0]
                        user_profile_obj = UserProfileCreate(
                            age=profile_data.get('age'),
                            gender=profile_data.get('gender'),
                            zodiac_sign=profile_data.get('zodiac_sign'),
                            appearance_type=profile_data.get('appearance_type'),  # 保留字段，不再使用
                            personality_type=profile_data.get('personality_type'),
                            preferred_source=profile_data.get('preferred_source', 'pkt'),
                            preferred_spread=profile_data.get('preferred_spread'),
                            significator_priority=profile_data.get('significator_priority', 'question_first'),
                            interpretation_model=profile_data.get('interpretation_model')
                        )
            except HTTPException:
                # 如果认证失败，继续作为匿名用户
                pass
        
        # 如果请求中提供了user_profile，使用请求中的
        if request.user_profile and not user_profile_obj:
            user_profile_obj = UserProfileCreate(**request.user_profile)
        
        # 调用占卜服务
        result = await reading_service.create_reading(
            question=request.question,
            user_id=user_id,
            user_selected_spread=request.user_selected_spread,
            user_profile=user_profile_obj,
            use_rag_for_pattern=request.use_rag_for_pattern,
            preferred_source=request.preferred_source,
            source_page=request.source_page
        )
        
        return TarotReadingResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating reading: {str(e)}")


@router.get("/readings/{reading_id}")
async def get_tarot_reading(
    reading_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    获取特定占卜的详细信息
    
    如果提供了Authorization header，只能查看自己的占卜。
    如果没有提供，可以查看任何占卜（如果RLS允许）。
    """
    try:
        supabase = get_supabase_service()
        
        # 构建查询
        query = supabase.table("readings").select("*").eq("id", reading_id)
        
        # 如果用户已登录，只查询自己的占卜
        if authorization:
            try:
                current_user = get_current_user(authorization)
                query = query.eq("user_id", current_user["id"])
            except HTTPException:
                # 如果认证失败，继续查询（RLS会处理权限）
                pass
        
        result = query.execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Reading not found")
        
        reading = result.data[0]
        
        # 获取关联的牌
        cards_result = supabase.table("reading_cards").select("*").eq("reading_id", reading_id).order("position_order").execute()
        reading_cards = cards_result.data or []
        
        # 批量获取卡牌的image_url和其他信息
        if reading_cards:
            card_ids = [card['card_id'] for card in reading_cards]
            tarot_cards_result = supabase.table("tarot_cards").select("id, image_url, card_name_en, card_name_cn").in_("id", card_ids).execute()
            
            # 创建card_id到tarot_card的映射
            tarot_cards_map = {card['id']: card for card in (tarot_cards_result.data or [])}
            
            # 合并数据
            cards = []
            for reading_card in reading_cards:
                card_id = reading_card['card_id']
                tarot_card = tarot_cards_map.get(card_id, {})
                
                card_data = {
                    **reading_card,
                    'image_url': tarot_card.get('image_url'),
                    'card_name_en': tarot_card.get('card_name_en') or reading_card.get('card_name_en'),
                    'card_name_cn': tarot_card.get('card_name_cn') or reading_card.get('card_name_cn'),
                }
                cards.append(card_data)
            
            reading["cards"] = cards
        else:
            reading["cards"] = []
        
        return reading
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reading: {str(e)}")


@router.get("/readings")
async def list_tarot_readings(
    limit: int = 10,
    offset: int = 0,
    authorization: Optional[str] = Header(None)
):
    """
    列出占卜记录
    
    如果提供了Authorization header，只返回当前用户的占卜。
    如果没有提供，返回所有占卜（如果RLS允许）。
    """
    try:
        supabase = get_supabase_service()
        
        # 构建查询
        query = supabase.table("readings").select("*").order("created_at", desc=True).limit(limit).offset(offset)
        
        # 如果用户已登录，只查询自己的占卜
        if authorization:
            try:
                current_user = get_current_user(authorization)
                query = query.eq("user_id", current_user["id"])
            except HTTPException:
                # 如果认证失败，继续查询（RLS会处理权限）
                pass
        
        result = query.execute()
        
        return {
            "readings": result.data or [],
            "count": len(result.data) if result.data else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching readings: {str(e)}")


@router.post("/reading/stream")
async def create_tarot_reading_stream(
    request: TarotReadingRequest,
    authorization: Optional[str] = Header(None)
):
    """
    创建新的塔罗占卜（流式输出最终解读）
    
    这个端点会执行完整的占卜流程，但最终解读部分会以流式方式返回。
    使用 Server-Sent Events (SSE) 格式返回数据。
    
    - **question**: 要问塔罗牌的问题
    - **user_selected_spread**: 用户指定的占卜方式（可选，默认auto）
    - **use_rag_for_pattern**: 是否使用RAG进行牌型分析（默认False）
    - **preferred_source**: 偏好的数据源（pkt或78degrees，默认pkt）
    - **user_profile**: 用户信息（可选，包含age、gender、zodiac_sign等）
    
    响应格式（SSE）：
    - `event: progress` - 进度更新（JSON）
    - `event: interpretation` - 解读文本块（JSON，包含text字段）
    - `event: complete` - 完成信号（JSON）
    - `event: error` - 错误信号（JSON）
    """
    async def generate_stream():
        try:
            # 获取当前用户（如果已登录）
            user_id = None
            user_profile_obj = None
            
            if authorization:
                try:
                    current_user = get_current_user(authorization)
                    user_id = current_user["id"]
                    
                    # 如果提供了user_profile，使用提供的；否则尝试从数据库获取
                    if request.user_profile:
                        user_profile_obj = UserProfileCreate(**request.user_profile)
                    else:
                        # 尝试从数据库获取用户信息
                        supabase = get_supabase_service()
                        profile_result = supabase.table("user_profiles").select("*").eq("user_id", user_id).execute()
                        if profile_result.data:
                            profile_data = profile_result.data[0]
                            user_profile_obj = UserProfileCreate(
                                age=profile_data.get('age'),
                                gender=profile_data.get('gender'),
                                zodiac_sign=profile_data.get('zodiac_sign'),
                                appearance_type=profile_data.get('appearance_type'),
                                personality_type=profile_data.get('personality_type'),
                                preferred_source=profile_data.get('preferred_source', 'pkt'),
                                preferred_spread=profile_data.get('preferred_spread'),
                                significator_priority=profile_data.get('significator_priority', 'question_first'),
                                interpretation_model=profile_data.get('interpretation_model')
                            )
                except HTTPException:
                    # 如果认证失败，继续作为匿名用户
                    pass
            
            # 如果请求中提供了user_profile，使用请求中的
            if request.user_profile and not user_profile_obj:
                user_profile_obj = UserProfileCreate(**request.user_profile)
            
            # 调用流式占卜服务
            async for update in reading_service.create_reading_stream(
                question=request.question,
                user_id=user_id,
                user_selected_spread=request.user_selected_spread,
                user_profile=user_profile_obj,
                use_rag_for_pattern=request.use_rag_for_pattern,
                preferred_source=request.preferred_source,
                source_page=request.source_page
            ):
                if update['type'] == 'progress':
                    # 将step包含在data中
                    progress_data = update['data'].copy()
                    progress_data['step'] = update.get('step', 'unknown')
                    yield f"event: progress\ndata: {json.dumps(progress_data, ensure_ascii=False)}\n\n"
                elif update['type'] == 'imagery_chunk':
                    # ⭐ 意象描述流式块
                    yield f"event: imagery_chunk\ndata: {json.dumps({'text': update['text']}, ensure_ascii=False)}\n\n"
                elif update['type'] == 'interpretation':
                    yield f"event: interpretation\ndata: {json.dumps({'text': update['text']}, ensure_ascii=False)}\n\n"
                elif update['type'] == 'complete':
                    yield f"event: complete\ndata: {json.dumps(update['data'], ensure_ascii=False)}\n\n"
                elif update['type'] == 'error':
                    yield f"event: error\ndata: {json.dumps({'error': update['error'], 'reading_id': update.get('reading_id')}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            # 发送错误信号
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用nginx缓冲
        }
    )
