"""
Embedding service for generating text embeddings using OpenAI or OpenRouter.
"""

import logging
from typing import List
import openai
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI or OpenRouter."""
    
    def __init__(self):
        """Initialize OpenAI/OpenRouter client for embeddings."""
        # 判断使用 OpenRouter 还是 OpenAI
        if settings.use_openrouter and settings.openrouter_api_key:
            # 使用 OpenRouter
            api_key = settings.openrouter_api_key
            base_url = "https://openrouter.ai/api/v1"
            # OpenRouter 需要额外的 headers
            default_headers = {
                "HTTP-Referer": "https://github.com/yourusername/tarot_agent",  # 可选：你的应用 URL
                "X-Title": "Tarot Agent"  # 可选：应用名称
            }
            logger.info(f"Using OpenRouter for embeddings: {base_url}")
        else:
            # 使用 OpenAI
            api_key = settings.openai_api_key
            base_url = None  # OpenAI 默认 base_url
            default_headers = {}
            logger.info("Using OpenAI for embeddings")
        
        self.openai_client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers if default_headers else None
        )
        self.embed_model = settings.openai_embed_model
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (1536 dimensions for text-embedding-3-small)
        """
        try:
            response = self.openai_client.embeddings.create(
                model=self.embed_model,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            logger.info(f"Generated embeddings for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
    
    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a single query.
        
        Args:
            query: Query text to embed
            
        Returns:
            Embedding vector
        """
        embeddings = await self.embed_texts([query])
        return embeddings[0]


# Global service instance
embedding_service = EmbeddingService()

