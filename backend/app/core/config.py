"""
Configuration management for Tarot Agent backend.
Handles environment variables and application settings.
"""

from typing import List, Annotated
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, BeforeValidator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env file
    )
    
    # Supabase Configuration
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_service_role_key: str = Field(..., env="SUPABASE_SERVICE_ROLE_KEY")
    # Anon key is optional - if not provided, service_role_key will be used for all operations
    supabase_anon_key: str = Field(default="", env="SUPABASE_ANON_KEY")
    # Publishable key (mainly for frontend, but can be stored here for reference)
    supabase_publishable_key: str = Field(default="", env="SUPABASE_PUBLISHABLE_KEY")
    
    # OpenAI/OpenRouter Configuration (for RAG and LLM)
    # If using OpenRouter, set USE_OPENROUTER=true and provide OPENROUTER_API_KEY
    # If using OpenAI directly, provide OPENAI_API_KEY
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openrouter_api_key: str = Field(default="", env="OPENROUTER_API_KEY")
    use_openrouter: bool = Field(default=False, env="USE_OPENROUTER")
    
    # Model Preset Configuration
    # Options: gpt4omini_fast (推荐), gpt5_4omini, deepseek_r1_v3, deepseek_fast, gemini_25pro_15
    model_preset: str = Field(default="gpt4omini_fast", env="MODEL_PRESET")
    
    # Model names - will be set dynamically based on use_openrouter
    # These are computed properties, not env variables
    @property
    def openai_embed_model(self) -> str:
        """Get embedding model name based on provider."""
        if self.use_openrouter:
            return "openai/text-embedding-3-small"
        return "text-embedding-3-small"
    
    @property
    def openai_chat_model(self) -> str:
        """Get chat model name based on provider."""
        if self.use_openrouter:
            return "openai/gpt-4o-mini"
        return "gpt-4o-mini"
    
    # Application Configuration - hardcoded defaults (no need to put in .env)
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins_str: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        env="CORS_ORIGINS",
        exclude=True  # Don't include in model output
    )
    
    def __init__(self, **kwargs):
        """Initialize settings with debug logging for CORS_ORIGINS"""
        super().__init__(**kwargs)
        # Debug: Log environment variable reading
        import os
        cors_env = os.getenv("CORS_ORIGINS")
        if cors_env:
            print(f"[DEBUG] CORS_ORIGINS from environment: {cors_env}")
        else:
            print(f"[DEBUG] CORS_ORIGINS not found in environment, using default")
        print(f"[DEBUG] Final cors_origins_str value: {self.cors_origins_str}")
    # Frontend URL for email verification links (used in auth routes)
    frontend_url: str = Field(
        default="http://localhost:3000",
        env="FRONTEND_URL",
        description="Frontend URL for email verification redirects. Should be set to production URL in production environment."
    )
    api_v1_prefix: str = "/api/v1"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS_ORIGINS from comma-separated string."""
        if hasattr(self, 'cors_origins_str'):
            return [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]
        return ["http://localhost:3000", "http://localhost:3001"]
    
    # RAG Configuration - hardcoded defaults (no need to put in .env)
    rag_chunk_size: int = 400
    rag_chunk_overlap: int = 60
    rag_top_k: int = 6
    rag_temperature: float = 0.1
    embedding_dimensions: int = 1536  # text-embedding-3-small dimensions


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings

