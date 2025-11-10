"""
用户认证API端点
支持邮箱登录、密码登录、注册、登出等功能
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Request
from pydantic import BaseModel, EmailStr
from typing import Optional
import httpx
from urllib.parse import urlparse
from app.core.database import get_supabase, get_supabase_service
from app.core.config import settings
from supabase import Client

router = APIRouter()


def get_frontend_url(request: Request) -> str:
    """
    从请求头中动态获取前端URL
    优先级：配置中的FRONTEND_URL（如果设置了且不是localhost）> Origin头 > Referer头 > 默认值
    
    注意：在生产环境中，应该设置 FRONTEND_URL 环境变量，确保即使请求头缺失，
    也能使用正确的部署URL而不是 localhost。
    """
    # 优先使用配置中的FRONTEND_URL（如果设置了且不是localhost）
    # 这样可以确保生产环境始终使用正确的URL，不受请求头影响
    if settings.frontend_url and settings.frontend_url != "http://localhost:3000":
        return settings.frontend_url
    
    # 其次从Origin头获取（最可靠，来自实际请求）
    origin = request.headers.get("origin")
    if origin:
        # 提取协议和主机（包含端口）
        parsed = urlparse(origin)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    
    # 再次从Referer头获取
    referer = request.headers.get("referer")
    if referer:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    
    # 最后回退到默认值（仅用于开发环境）
    return settings.frontend_url


class SignUpRequest(BaseModel):
    """注册请求模型"""
    email: EmailStr
    password: str


class SignInRequest(BaseModel):
    """登录请求模型"""
    email: EmailStr
    password: str


class SignInResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    refresh_token: str
    user_id: str
    email: str


class SignUpResponse(BaseModel):
    """注册响应模型"""
    id: str
    email: str
    created_at: str
    requires_email_confirmation: bool  # 是否需要邮箱确认


class UserResponse(BaseModel):
    """用户信息响应模型"""
    id: str
    email: str
    created_at: str


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    从请求头中获取当前用户信息
    
    Args:
        authorization: Authorization header (格式: "Bearer <token>")
    
    Returns:
        用户信息字典
    
    Raises:
        HTTPException: 如果token无效或缺失
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        # 提取token
        token = authorization.replace("Bearer ", "").strip()
        
        # 使用Supabase验证token
        # 注意：Supabase Python客户端需要完整的session（access_token和refresh_token）
        # 但我们可以使用service role key来验证token
        from app.core.config import settings
        from supabase import create_client
        
        # 使用service role key创建客户端来验证token（绕过RLS）
        supabase = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        
        # 尝试使用token获取用户信息
        # 注意：Supabase Python SDK的get_user方法需要完整的session对象
        # 我们可以直接调用Supabase REST API来验证token
        import httpx
        
        # 调用Supabase Auth API验证token
        response = httpx.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": settings.supabase_anon_key or settings.supabase_service_role_key
            },
            timeout=5.0
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_data = response.json()
        
        return {
            "id": user_data["id"],
            "email": user_data.get("email", ""),
            "created_at": user_data.get("created_at", "")
        }
    except HTTPException:
        raise
    except httpx.HTTPError:
        raise HTTPException(status_code=401, detail="Failed to verify token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


@router.post("/signup", response_model=SignUpResponse)
async def signup(request: SignUpRequest, http_request: Request):
    """
    用户注册
    
    - **email**: 用户邮箱
    - **password**: 用户密码（至少6个字符）
    
    返回：
    - 如果启用了邮箱确认，requires_email_confirmation 为 True，用户需要检查邮箱并点击确认链接
    - 如果禁用了邮箱确认，requires_email_confirmation 为 False，用户可以直接登录
    """
    try:
        supabase = get_supabase()
        
        # 注册用户
        # 如果 Supabase 启用了邮箱确认，注册后不会立即返回 session
        # 需要用户点击邮箱中的确认链接后才能登录
        # 设置重定向 URL 到前端的回调页面（从请求头动态获取）
        frontend_url = get_frontend_url(http_request)
        email_redirect_to = f"{frontend_url}/auth/callback"
        
        # 记录调试信息
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Signup - Frontend URL: {frontend_url}, Email redirect to: {email_redirect_to}")
        logger.info(f"Signup - FRONTEND_URL env var: {settings.frontend_url}")
        
        response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "email_redirect_to": email_redirect_to
            }
        })
        
        if not response.user:
            raise HTTPException(status_code=400, detail="Failed to create user")
        
        # 检查是否有 session（如果邮箱确认被禁用，会有 session）
        # 如果启用了邮箱确认，session 可能为 None
        requires_email_confirmation = response.session is None
        
        # 处理 created_at：如果是 datetime 对象，转换为 ISO 格式字符串
        created_at = response.user.created_at
        if hasattr(created_at, 'isoformat'):
            created_at = created_at.isoformat()
        elif created_at is None:
            from datetime import datetime
            created_at = datetime.utcnow().isoformat()
        else:
            created_at = str(created_at)
        
        return SignUpResponse(
            id=response.user.id,
            email=response.user.email or request.email,
            created_at=created_at,
            requires_email_confirmation=requires_email_confirmation
        )
    except Exception as e:
        error_msg = str(e)
        # 记录详细错误日志
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Signup error: {error_msg}", exc_info=True)
        
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Email already registered")
        elif "password" in error_msg.lower() and ("weak" in error_msg.lower() or "short" in error_msg.lower()):
            raise HTTPException(status_code=400, detail="Password is too weak. Please use at least 6 characters.")
        elif "email" in error_msg.lower() and "invalid" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Invalid email address")
        raise HTTPException(status_code=500, detail=f"Error signing up: {error_msg}")


@router.post("/signin", response_model=SignInResponse)
async def signin(request: SignInRequest):
    """
    用户登录
    
    - **email**: 用户邮箱
    - **password**: 用户密码
    """
    try:
        supabase = get_supabase()
        
        # 登录
        response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not response.user or not response.session:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        return SignInResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user_id=response.user.id,
            email=response.user.email or request.email
        )
    except Exception as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() or "password" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Invalid email or password")
        raise HTTPException(status_code=500, detail=f"Error signing in: {error_msg}")


@router.post("/signout")
async def signout(authorization: Optional[str] = Header(None)):
    """
    用户登出
    
    需要Authorization header: "Bearer <token>"
    
    注意：由于前端已经在 finally 块中清除了所有 token，即使后端失败，
    用户也已经登出。这里主要验证 token 并返回成功。
    """
    try:
        if not authorization:
            # 如果没有 token，直接返回成功（前端已经清除了 token）
            return {"message": "Successfully signed out"}
        
        token = authorization.replace("Bearer ", "").strip()
        
        # 尝试验证 token 是否有效（可选）
        # 如果 token 无效，也返回成功，因为前端已经清除了 token
        try:
            # 使用 Supabase REST API 验证 token
            response = httpx.get(
                f"{settings.supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": settings.supabase_anon_key or settings.supabase_service_role_key
                },
                timeout=5.0
            )
            
            # 如果 token 有效，可以尝试撤销 refresh token（需要 refresh_token，但我们没有）
            # 由于前端已经清除了所有 token，这里直接返回成功即可
            if response.status_code == 200:
                # Token 有效，用户已登录，返回成功
                return {"message": "Successfully signed out"}
            else:
                # Token 无效或已过期，也返回成功（前端已经清除了 token）
                return {"message": "Successfully signed out"}
        except Exception:
            # 验证失败，也返回成功（前端已经清除了 token）
            return {"message": "Successfully signed out"}
            
    except Exception as e:
        # 即使发生错误，也返回成功，因为前端已经在 finally 块中清除了 token
        # 记录错误日志用于调试
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Signout error (ignored): {str(e)}")
        return {"message": "Successfully signed out"}


@router.post("/resend-confirmation")
async def resend_confirmation(request: SignUpRequest, http_request: Request):
    """
    重新发送邮箱确认邮件
    
    - **email**: 用户邮箱
    - **password**: 用户密码（用于验证，但 Supabase resend API 不需要密码）
    
    注意：Supabase 可能有频率限制，短时间内不能重复发送确认邮件
    """
    try:
        supabase = get_supabase()
        
        # 检查用户是否存在且未确认
        # 使用 service role key 来查询用户状态
        supabase_service = get_supabase_service()
        
        # 尝试通过邮箱查找用户（需要调用 Supabase Admin API）
        # 注意：resend API 不需要密码，只需要邮箱
        import logging
        logger = logging.getLogger(__name__)
        
        # 设置重定向 URL（从请求头动态获取）
        frontend_url = get_frontend_url(http_request)
        email_redirect_to = f"{frontend_url}/auth/callback"
        
        # 重新发送确认邮件
        # Supabase resend API 只需要邮箱和类型
        try:
            response = supabase.auth.resend({
                "type": "signup",
                "email": request.email,
                "options": {
                    "email_redirect_to": email_redirect_to
                }
            })
            
            logger.info(f"Resend confirmation email response: {response}")
            
            return {
                "message": "Confirmation email sent successfully",
                "email": request.email
            }
        except Exception as resend_error:
            error_msg = str(resend_error)
            logger.error(f"Resend error: {error_msg}")
            
            # 检查常见错误
            if "rate limit" in error_msg.lower() or "too many" in error_msg.lower():
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests. Please wait a few minutes before requesting another confirmation email."
                )
            elif "already confirmed" in error_msg.lower() or "confirmed" in error_msg.lower():
                raise HTTPException(
                    status_code=400,
                    detail="This email is already confirmed. You can log in directly."
                )
            elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                raise HTTPException(
                    status_code=404,
                    detail="No account found with this email address. Please sign up first."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error resending confirmation email: {error_msg}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error in resend_confirmation: {error_msg}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error resending confirmation email: {error_msg}")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str


@router.post("/refresh", response_model=SignInResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    刷新访问令牌
    
    - **refresh_token**: 刷新令牌
    
    如果refresh_token有效且未过期（30天内使用过），返回新的access_token和refresh_token
    """
    try:
        import httpx
        from app.core.config import settings
        
        # 直接调用Supabase Auth API刷新token
        # 使用REST API而不是SDK，避免session管理问题
        response = httpx.post(
            f"{settings.supabase_url}/auth/v1/token?grant_type=refresh_token",
            headers={
                "Content-Type": "application/json",
                "apikey": settings.supabase_anon_key or settings.supabase_service_role_key
            },
            json={"refresh_token": request.refresh_token},
            timeout=10.0
        )
        
        if response.status_code != 200:
            error_data = response.text
            if "expired" in error_data.lower() or "invalid" in error_data.lower():
                raise HTTPException(status_code=401, detail="Refresh token expired or invalid. Please login again.")
            raise HTTPException(status_code=401, detail=f"Failed to refresh token: {error_data}")
        
        token_data = response.json()
        
        # 获取用户信息
        access_token = token_data.get("access_token")
        refresh_token_new = token_data.get("refresh_token")
        
        if not access_token or not refresh_token_new:
            raise HTTPException(status_code=500, detail="Invalid token response from Supabase")
        
        # 使用新的access_token获取用户信息
        user_response = httpx.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "apikey": settings.supabase_anon_key or settings.supabase_service_role_key
            },
            timeout=5.0
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to get user info after refresh")
        
        user_data = user_response.json()
        
        return SignInResponse(
            access_token=access_token,
            refresh_token=refresh_token_new,
            user_id=user_data["id"],
            email=user_data.get("email", "")
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error refreshing token: {error_msg}", exc_info=True)
        if "expired" in error_msg.lower() or "invalid" in error_msg.lower():
            raise HTTPException(status_code=401, detail="Refresh token expired or invalid. Please login again.")
        raise HTTPException(status_code=500, detail=f"Error refreshing token: {error_msg}")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    获取当前用户信息
    
    需要Authorization header: "Bearer <token>"
    """
    # 处理 created_at：确保是字符串格式
    created_at = current_user.get("created_at", "")
    if hasattr(created_at, 'isoformat'):
        created_at = created_at.isoformat()
    elif created_at is None:
        from datetime import datetime
        created_at = datetime.utcnow().isoformat()
    else:
        created_at = str(created_at)
    
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        created_at=created_at
    )

