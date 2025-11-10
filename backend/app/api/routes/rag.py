"""
RAG API endpoints for Tarot Agent.
Provides endpoints for querying RAG system and managing documents.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.services.rag import rag_service

router = APIRouter()


class QueryRequest(BaseModel):
    """Request model for RAG query."""
    query: str
    top_k: Optional[int] = None


class QueryResponse(BaseModel):
    """Response model for RAG query."""
    text: str
    citations: List[Dict[str, Any]]
    debug: Dict[str, Any]


class SeedRequest(BaseModel):
    """Request model for seeding documents."""
    documents: List[Dict[str, str]]


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Query the RAG system with a question.
    
    - **query**: The question to ask
    - **top_k**: Number of chunks to retrieve (optional)
    """
    try:
        result = await rag_service.answer_query(
            query=request.query,
            top_k=request.top_k
        )
        return QueryResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.post("/seed")
async def seed_documents(request: SeedRequest):
    """
    Seed the RAG database with documents.
    
    - **documents**: List of documents with 'text', 'source', 'chunk_id', and optional 'metadata'
    """
    try:
        count = await rag_service.seed_documents(request.documents)
        return {
            "message": f"Successfully processed {count} chunks",
            "chunks_inserted": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error seeding documents: {str(e)}")


@router.get("/stats")
async def get_rag_stats():
    """Get RAG database statistics."""
    try:
        stats = await rag_service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

