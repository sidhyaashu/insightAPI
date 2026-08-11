"""
search.py — Semantic Endpoint Search REST API for InsightAPI AI

Endpoint
--------
POST /api/v1/search
Search discovered endpoints across sessions using natural-language queries.
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.vector_store import EndpointVectorStore

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query (e.g. 'find all payment and billing endpoints')")
    top_k: Optional[int] = Field(default=5, description="Maximum number of matching endpoints to return (default: 5)")


class SearchResponse(BaseModel):
    query: str
    result_count: int
    endpoints: List[Dict[str, Any]]


@router.post("", response_model=SearchResponse)
async def search_endpoints(request: SearchRequest):
    """
    Search across stored API endpoints from all crawl sessions using semantic query matching.
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query string must not be empty.")

    k = max(1, min(request.top_k or 5, 50))
    matches = await EndpointVectorStore.search_similar(request.query.strip(), top_k=k)

    return SearchResponse(
        query=request.query,
        result_count=len(matches),
        endpoints=matches,
    )
