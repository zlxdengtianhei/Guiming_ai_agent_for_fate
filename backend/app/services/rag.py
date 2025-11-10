"""
Main RAG service orchestrating the complete RAG pipeline.
"""

import logging
import time
import hashlib
from typing import List, Dict, Any, Optional
from app.services.rag_database import rag_db
from app.services.embedding import embedding_service
from app.services.chunker import chunker
from app.services.chat import chat_service
from app.core.config import settings

logger = logging.getLogger(__name__)

# Simple in-memory cache for embeddings (consider using Redis for production)
_embedding_cache: Dict[str, List[float]] = {}  # type: ignore


class RAGService:
    """Main RAG service orchestrating the complete pipeline."""
    
    async def seed_documents(self, documents: List[Dict[str, str]]) -> int:
        """
        Process and store documents in the vector database.
        
        Args:
            documents: List of documents with 'text', 'source', 'chunk_id', and optional 'metadata'
            
        Returns:
            Number of chunks stored
        """
        try:
            logger.info(f"Processing {len(documents)} documents for RAG")
            
            # Step 1: Chunk documents
            chunks = chunker.chunk_documents(documents)
            
            if not chunks:
                logger.warning("No chunks generated from documents")
                return 0
            
            # Step 2: Generate embeddings for all chunks
            texts = [chunk['text'] for chunk in chunks]
            embeddings = await embedding_service.embed_texts(texts)
            
            # Step 3: Add embeddings to chunks
            for i, chunk in enumerate(chunks):
                chunk['embedding'] = embeddings[i]
            
            # Step 4: Store in database
            inserted_count = await rag_db.upsert_chunks(chunks)
            
            logger.info(f"Successfully seeded {inserted_count} chunks into RAG database")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Failed to seed documents: {e}")
            raise
    
    async def answer_query(
        self, 
        query: str, 
        top_k: int = None,
        balance_sources: bool = True,
        min_similarity: float = 0.3
    ) -> Dict[str, Any]:
        """
        Process a query through the complete RAG pipeline.
        
        Args:
            query: User's question
            top_k: Number of chunks to retrieve (default from settings)
            balance_sources: If True, ensure results from multiple sources (default: True)
            min_similarity: Minimum similarity threshold (0.0 to 1.0, default: 0.3)
            
        Returns:
            Dictionary with answer, citations, and debug info
        """
        start_time = time.time()
        top_k = top_k or settings.rag_top_k
        
        try:
            # Step 1: Generate query embedding (with caching)
            query_embedding = await self._get_cached_embedding(query)
            
            # Step 2: Vector similarity search (with source balancing)
            if balance_sources:
                search_results = await self._balanced_vector_search(
                    query_embedding,
                    top_k=top_k,
                    min_similarity=min_similarity
                )
            else:
                search_results = await rag_db.vector_search(
                    query_embedding, 
                    top_k=top_k,
                    min_similarity=min_similarity
                )
            
            if not search_results:
                return {
                    'text': "I don't have enough information to answer your question. Could you please rephrase or provide more context?",
                    'citations': [],
                    'debug': {
                        'top_doc_ids': [],
                        'latency_ms': int((time.time() - start_time) * 1000)
                    }
                }
            
            # Step 3: Prepare context
            context_blocks = [
                {
                    'chunk_id': result.get('chunk_id', ''),
                    'text': result.get('text', ''),
                    'source': result.get('source', ''),
                    'similarity': result.get('similarity', 0.0),
                    'metadata': result.get('metadata', {})
                }
                for result in search_results
            ]
            
            # Step 4: Generate answer
            answer_text = await chat_service.generate_answer(query, context_blocks)
            
            # Step 5: Extract citations
            citations = [
                {
                    'source': block['source'],
                    'chunk_id': block['chunk_id'],
                    'similarity': block['similarity']
                }
                for block in context_blocks
            ]
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            result = {
                'text': answer_text,
                'citations': citations,
                'debug': {
                    'top_doc_ids': [block['chunk_id'] for block in context_blocks],
                    'latency_ms': elapsed_ms,
                    'num_results': len(context_blocks)
                }
            }
            
            logger.info(f"Query processed in {elapsed_ms}ms with {len(citations)} citations")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            raise
    
    async def _get_cached_embedding(self, query: str) -> List[float]:
        """
        Get embedding for query with caching.
        
        Args:
            query: Query text
            
        Returns:
            Embedding vector
        """
        # Create cache key from query hash
        cache_key = hashlib.md5(query.encode()).hexdigest()
        
        # Check cache
        if cache_key in _embedding_cache:
            logger.debug(f"Using cached embedding for query")
            return _embedding_cache[cache_key]
        
        # Generate new embedding
        embedding = await embedding_service.embed_query(query)
        
        # Cache it (limit cache size to prevent memory issues)
        if len(_embedding_cache) < 1000:  # Max 1000 cached embeddings
            _embedding_cache[cache_key] = embedding
        
        return embedding
    
    async def _balanced_vector_search(
        self,
        query_embedding: List[float],
        top_k: int = 6,
        min_similarity: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Perform balanced vector search ensuring results from multiple sources.
        
        This ensures that when there are multiple data sources, we get
        results from each source rather than only from the most similar one.
        Also includes deduplication to avoid returning duplicate chunks.
        
        Args:
            query_embedding: Query vector embedding
            top_k: Total number of results to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of matching chunks with similarity scores (deduplicated)
        """
        # Get more results to allow for balancing and deduplication
        search_k = min(top_k * 3, 20)  # Get more candidates
        
        # Search all sources
        all_results = await rag_db.vector_search(
            query_embedding,
            top_k=search_k,
            min_similarity=min_similarity
        )
        
        if not all_results:
            return []
        
        # Deduplicate by chunk_id first (keep highest similarity)
        seen_chunk_ids: Dict[str, Dict[str, Any]] = {}
        for result in all_results:
            chunk_id = result.get('chunk_id', '')
            if chunk_id:
                # Keep the result with highest similarity if duplicate
                if chunk_id not in seen_chunk_ids:
                    seen_chunk_ids[chunk_id] = result
                else:
                    current_sim = seen_chunk_ids[chunk_id].get('similarity', 0)
                    new_sim = result.get('similarity', 0)
                    if new_sim > current_sim:
                        seen_chunk_ids[chunk_id] = result
        
        # Convert back to list and sort by similarity
        deduplicated_results = list(seen_chunk_ids.values())
        deduplicated_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        # Group results by source
        results_by_source: Dict[str, List[Dict[str, Any]]] = {}
        for result in deduplicated_results:
            source = result.get('source', 'unknown')
            if source not in results_by_source:
                results_by_source[source] = []
            results_by_source[source].append(result)
        
        # If only one source, return top_k results (already deduplicated)
        if len(results_by_source) <= 1:
            return deduplicated_results[:top_k]
        
        # Balance results from multiple sources
        balanced_results = []
        sources = list(results_by_source.keys())
        
        # Calculate how many results per source
        per_source = max(1, top_k // len(sources))
        
        # Take top results from each source
        for source in sources:
            source_results = results_by_source[source][:per_source]
            balanced_results.extend(source_results)
        
        # If we need more results, fill from the remaining best results
        if len(balanced_results) < top_k:
            remaining_slots = top_k - len(balanced_results)
            # Get remaining results excluding already selected ones
            balanced_chunk_ids = {r.get('chunk_id') for r in balanced_results}
            for result in deduplicated_results:
                if result.get('chunk_id') not in balanced_chunk_ids:
                    balanced_results.append(result)
                    remaining_slots -= 1
                    if remaining_slots <= 0:
                        break
        
        # Sort by similarity (descending) and return top_k
        balanced_results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        logger.info(
            f"Balanced search: {len(balanced_results)} results from {len(sources)} sources "
            f"({', '.join(sources)}), deduplicated from {len(all_results)} candidates"
        )
        
        return balanced_results[:top_k]
    
    async def search_only(
        self,
        query: str,
        top_k: int = None,
        balance_sources: bool = True,
        min_similarity: float = 0.3
    ) -> Dict[str, Any]:
        """
        Search for relevant chunks only, without LLM processing.
        
        This method performs vector search and returns raw chunks without
        generating an answer using LLM. Useful when you want to collect
        all chunks and process them together later.
        
        Args:
            query: User's question
            top_k: Number of chunks to retrieve (default from settings)
            balance_sources: If True, ensure results from multiple sources (default: True)
            min_similarity: Minimum similarity threshold (0.0 to 1.0, default: 0.3)
            
        Returns:
            Dictionary with chunks (raw text), citations, and debug info
        """
        start_time = time.time()
        top_k = top_k or settings.rag_top_k
        
        try:
            # Step 1: Generate query embedding (with caching)
            query_embedding = await self._get_cached_embedding(query)
            
            # Step 2: Vector similarity search (with source balancing)
            if balance_sources:
                search_results = await self._balanced_vector_search(
                    query_embedding,
                    top_k=top_k,
                    min_similarity=min_similarity
                )
            else:
                search_results = await rag_db.vector_search(
                    query_embedding,
                    top_k=top_k,
                    min_similarity=min_similarity
                )
            
            if not search_results:
                return {
                    'chunks': [],
                    'citations': [],
                    'debug': {
                        'top_doc_ids': [],
                        'latency_ms': int((time.time() - start_time) * 1000)
                    }
                }
            
            # Step 3: Prepare chunks (raw text, no LLM processing)
            chunks = [
                {
                    'chunk_id': result.get('chunk_id', ''),
                    'text': result.get('text', ''),
                    'source': result.get('source', ''),
                    'similarity': result.get('similarity', 0.0),
                    'metadata': result.get('metadata', {})
                }
                for result in search_results
            ]
            
            # Step 4: Extract citations
            citations = [
                {
                    'source': chunk['source'],
                    'chunk_id': chunk['chunk_id'],
                    'similarity': chunk['similarity']
                }
                for chunk in chunks
            ]
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            result = {
                'chunks': chunks,
                'citations': citations,
                'debug': {
                    'top_doc_ids': [chunk['chunk_id'] for chunk in chunks],
                    'latency_ms': elapsed_ms,
                    'num_results': len(chunks)
                }
            }
            
            logger.info(f"Search completed in {elapsed_ms}ms with {len(chunks)} chunks (no LLM processing)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            raise
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get RAG database statistics."""
        return await rag_db.get_stats()
    
    def clear_embedding_cache(self):
        """Clear the embedding cache."""
        global _embedding_cache
        _embedding_cache.clear()
        logger.info("Embedding cache cleared")


# Global service instance
rag_service = RAGService()

