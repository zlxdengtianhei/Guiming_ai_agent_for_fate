"""
RAG database operations for Tarot Agent.
Handles vector storage and similarity search using Supabase with pgvector.
"""

import logging
from typing import Dict, List, Any, Optional
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)


class RAGDatabase:
    """RAG database operations manager using Supabase."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self._client: Optional[Client] = None
        self._service_client: Optional[Client] = None
    
    def get_client(self, admin: bool = True) -> Client:
        """
        Get Supabase client instance.
        
        Args:
            admin: If True, returns client with service role key (bypasses RLS).
                   If False, returns client with anon key.
        """
        if admin:
            if self._service_client is None:
                self._service_client = create_client(
                    settings.supabase_url,
                    settings.supabase_service_role_key
                )
            return self._service_client
        else:
            if self._client is None:
                # Use anon key if provided, otherwise fallback to service_role_key
                key = settings.supabase_anon_key if settings.supabase_anon_key else settings.supabase_service_role_key
                self._client = create_client(
                    settings.supabase_url,
                    key
                )
            return self._client
    
    async def upsert_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """
        Upsert document chunks into the database.
        
        Args:
            chunks: List of chunk dictionaries with keys: chunk_id, source, text, embedding, metadata
            
        Returns:
            Number of chunks inserted/updated
        """
        if not chunks:
            return 0
        
        try:
            client = self.get_client(admin=True)
            
            # Prepare data for Supabase
            chunk_data = []
            for chunk in chunks:
                chunk_data.append({
                    'chunk_id': chunk['chunk_id'],
                    'source': chunk['source'],
                    'text': chunk['text'],
                    'embedding': chunk['embedding'],
                    'metadata': chunk.get('metadata', {})
                })
            
            # Use upsert with on_conflict parameter
            result = client.table('rag_chunks').upsert(
                chunk_data,
                on_conflict='chunk_id'
            ).execute()
            
            inserted_count = len(result.data) if result.data else 0
            logger.info(f"Upserted {inserted_count} chunks to database")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Failed to upsert chunks: {e}")
            raise
    
    async def vector_search(
        self, 
        query_embedding: List[float], 
        top_k: int = 6,
        min_similarity: float = 0.0,
        filter_source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.
        
        Args:
            query_embedding: Query vector embedding (1536 dimensions)
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            filter_source: Optional source filter
            
        Returns:
            List of matching chunks with similarity scores
        """
        try:
            client = self.get_client(admin=True)
            
            # Use RPC call for vector similarity search
            result = client.rpc('match_chunks', {
                'query_embedding': query_embedding,
                'match_count': top_k,
                'min_similarity': min_similarity,
                'filter_source': filter_source
            }).execute()
            
            if result.data:
                logger.info(f"Vector search returned {len(result.data)} results")
                return result.data
            else:
                logger.warning("No results from vector search")
                return []
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            client = self.get_client(admin=True)
            result = client.rpc('get_chunk_stats').execute()
            
            if result.data:
                return result.data[0]
            return {}
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check database connection health."""
        try:
            client = self.get_client(admin=True)
            result = client.table('rag_chunks').select('id').limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global database instance
rag_db = RAGDatabase()

