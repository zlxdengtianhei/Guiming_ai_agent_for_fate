"""
Health check endpoints
"""

from fastapi import APIRouter
from app.core.database import get_supabase

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "tarot-agent-api"}


@router.get("/health/db")
async def database_health_check():
    """Check database connectivity."""
    try:
        supabase = get_supabase()
        # Try a simple query to check connectivity
        result = supabase.table("_prisma_migrations").select("id").limit(1).execute()
        return {
            "status": "healthy",
            "database": "connected",
            "supabase": "ok"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

