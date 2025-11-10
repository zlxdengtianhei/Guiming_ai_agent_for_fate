"""
Chat service for generating answers using LLM (OpenAI or OpenRouter).
"""

import logging
from typing import List, Dict, Any
import openai
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChatService:
    """Service for generating answers using OpenAI or OpenRouter Chat API."""
    
    def __init__(self):
        """Initialize OpenAI/OpenRouter client for chat."""
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
            logger.info(f"Using OpenRouter for chat: {base_url}")
        else:
            # 使用 OpenAI
            api_key = settings.openai_api_key
            base_url = None  # OpenAI 默认 base_url
            default_headers = {}
            logger.info("Using OpenAI for chat")
        
        self.openai_client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url,
            default_headers=default_headers if default_headers else None
        )
        self.chat_model = settings.openai_chat_model
        self.temperature = settings.rag_temperature
    
    async def generate_answer(
        self, 
        query: str, 
        context_blocks: List[Dict[str, Any]]
    ) -> str:
        """
        Generate answer using LLM with retrieved context.
        
        Args:
            query: User's question
            context_blocks: List of context chunks with 'text' and 'source' keys
            
        Returns:
            Generated answer text
        """
        try:
            # Prepare context from retrieved chunks (optimized format)
            context_parts = []
            for i, block in enumerate(context_blocks, 1):
                text = block.get('text', '')
                # Truncate very long texts to save tokens
                if len(text) > 600:
                    text = text[:600] + "..."
                context_parts.append(f"[{i}] {text}")
            
            context_text = "\n".join(context_parts)
            
            # Optimized system prompt (shorter)
            system_prompt = """You are a Tarot expert. Answer questions using the provided context. Be concise and accurate."""
            
            # Optimized user message (shorter format)
            user_message = f"""Context:\n{context_text}\n\nQ: {query}\nA:"""
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature
            )
            
            answer = response.choices[0].message.content
            logger.info(f"Generated answer for query: {query[:50]}...")
            return answer
            
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise


# Global service instance
chat_service = ChatService()

