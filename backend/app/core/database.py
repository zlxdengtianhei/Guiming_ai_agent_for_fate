"""
Supabase database connection and client setup.
"""

from supabase import create_client, Client
from app.core.config import settings


class SupabaseClient:
    """Supabase client singleton."""
    
    _client: Client | None = None
    _service_client: Client | None = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get Supabase client with anon key (for user operations)."""
        if cls._client is None:
            # Use anon key if provided, otherwise fallback to service_role_key
            key = settings.supabase_anon_key if settings.supabase_anon_key else settings.supabase_service_role_key
            cls._client = create_client(
                settings.supabase_url,
                key
            )
        return cls._client
    
    @classmethod
    def get_service_client(cls) -> Client:
        """Get Supabase client with service role key (bypasses RLS)."""
        if cls._service_client is None:
            cls._service_client = create_client(
                settings.supabase_url,
                settings.supabase_service_role_key
            )
        return cls._service_client


# Convenience functions
def get_supabase() -> Client:
    """Get Supabase client for user operations."""
    return SupabaseClient.get_client()


def get_supabase_service() -> Client:
    """Get Supabase client with service role (bypasses RLS)."""
    return SupabaseClient.get_service_client()

