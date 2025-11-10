"""
用户信息管理API端点
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from app.core.database import get_supabase_service
from app.models.schemas import UserProfileCreate, UserProfileUpdate, UserProfileResponse
from app.api.routes.auth import get_current_user

router = APIRouter()


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """
    获取用户个人信息
    
    需要Authorization header: "Bearer <token>"
    """
    try:
        supabase = get_supabase_service()
        
        # 查询用户信息
        result = supabase.table("user_profiles").select("*").eq("user_id", current_user["id"]).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        profile_data = result.data[0]
        return UserProfileResponse(**profile_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user profile: {str(e)}")


@router.post("/profile", response_model=UserProfileResponse)
async def create_user_profile(
    profile: UserProfileCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    创建用户个人信息
    
    需要Authorization header: "Bearer <token>"
    """
    try:
        supabase = get_supabase_service()
        
        # 检查是否已存在
        existing = supabase.table("user_profiles").select("*").eq("user_id", current_user["id"]).execute()
        
        if existing.data:
            raise HTTPException(status_code=400, detail="User profile already exists. Use PUT to update.")
        
        # 创建用户信息
        profile_data = profile.model_dump()
        profile_data["user_id"] = current_user["id"]
        
        # 将空字符串转换为 None，以符合数据库 CHECK 约束
        # 数据库 CHECK 约束只接受特定值或 NULL，不接受空字符串
        # 需要处理的字段：gender, personality_type, appearance_type, preferred_spread, zodiac_sign
        fields_to_convert = ["gender", "personality_type", "appearance_type", "preferred_spread", "zodiac_sign"]
        for field in fields_to_convert:
            if profile_data.get(field) == "":
                profile_data[field] = None
        
        result = supabase.table("user_profiles").insert(profile_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create user profile")
        
        return UserProfileResponse(**result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user profile: {str(e)}")


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile: UserProfileUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    更新用户个人信息
    
    需要Authorization header: "Bearer <token>"
    """
    try:
        supabase = get_supabase_service()
        
        # 更新用户信息（只更新提供的字段）
        profile_data = profile.model_dump(exclude_unset=True)
        
        # 将空字符串转换为 None，以符合数据库 CHECK 约束
        # 数据库 CHECK 约束只接受特定值或 NULL，不接受空字符串
        fields_to_convert = ["gender", "personality_type", "appearance_type", "preferred_spread", "zodiac_sign"]
        for field in fields_to_convert:
            if field in profile_data and profile_data[field] == "":
                profile_data[field] = None
        
        result = supabase.table("user_profiles").update(profile_data).eq("user_id", current_user["id"]).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return UserProfileResponse(**result.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating user profile: {str(e)}")



