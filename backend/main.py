"""
Tarot Agent - FastAPI Backend
Main application entry point
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.api.routes import tarot, health, rag, auth, user
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Tarot Agent API",
    description="塔罗占卜AI助手后端API",
    version="1.0.0",
)

# Log CORS configuration on startup
logger.info("=" * 50)
logger.info("CORS Configuration:")
logger.info(f"  CORS_ORIGINS env var: {settings.cors_origins_str}")
logger.info(f"  Parsed CORS origins: {settings.cors_origins}")
logger.info(f"  Frontend URL: {settings.frontend_url}")
logger.info("=" * 50)

# Configure CORS
# Allow specific origins from settings and all Vercel preview deployments
# DEBUG: Log CORS origins being used
logger.info(f"Setting up CORS with origins: {settings.cors_origins}")
logger.info(f"Vercel regex pattern: https://.*\\.vercel\\.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DEBUG: Add middleware to log CORS headers in responses
class CORSDebugMiddleware(BaseHTTPMiddleware):
    """Debug middleware to log CORS-related headers"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin")
        if origin:
            logger.info(f"CORS Debug - Origin: {origin}, Method: {request.method}, Path: {request.url.path}")
            logger.info(f"CORS Debug - Response status: {response.status_code}")
            # Log CORS headers in response
            cors_headers = {
                "access-control-allow-origin": response.headers.get("access-control-allow-origin"),
                "access-control-allow-methods": response.headers.get("access-control-allow-methods"),
                "access-control-allow-headers": response.headers.get("access-control-allow-headers"),
                "access-control-allow-credentials": response.headers.get("access-control-allow-credentials"),
            }
            logger.info(f"CORS Debug - Response headers: {cors_headers}")
        return response

app.add_middleware(CORSDebugMiddleware)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(tarot.router, prefix="/api/tarot", tags=["tarot"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Tarot Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

