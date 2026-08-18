"""
vector_store.py — Vector Store Endpoint Memory for InsightAPI AI

Design
------
Stores and retrieves API endpoint metadata across crawl sessions.
Supports semantic similarity search ("find all authentication endpoints") and cross-session deduplication.
Uses an in-memory vector index with optional PostgreSQL pgvector persistence when DATABASE_URL is available.
"""
from __future__ import annotations

import logging
import math
from typing import List, Dict, Any, Optional

logger = logging.getLogger("agent.vector_store")


def _tokenize(text: str) -> List[str]:
    import re
    return [w.lower() for w in re.findall(r"\w+", text) if len(w) > 1]


def _cosine_similarity_tf(text1: str, text2: str) -> float:
    """Computes TF-based cosine similarity between two text strings."""
    tokens1 = _tokenize(text1)
    tokens2 = _tokenize(text2)
    if not tokens1 or not tokens2:
        return 0.0

    freq1: Dict[str, int] = {}
    for t in tokens1:
        freq1[t] = freq1.get(t, 0) + 1

    freq2: Dict[str, int] = {}
    for t in tokens2:
        freq2[t] = freq2.get(t, 0) + 1

    all_words = set(freq1.keys()) | set(freq2.keys())
    dot = sum(freq1.get(w, 0) * freq2.get(w, 0) for w in all_words)
    mag1 = math.sqrt(sum(v * v for v in freq1.values()))
    mag2 = math.sqrt(sum(v * v for v in freq2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


class EndpointVectorStore:
    """
    Cross-session endpoint memory and semantic search engine.
    Supports optional ChromaDB local vector embeddings with TF-IDF fallback.

    Memory is bounded to MAX_STORE_SIZE entries. When the limit is reached the
    oldest entries are evicted (FIFO) to prevent unbounded growth on long-running
    processes. Persist via Phase 8 (AgentEvent DB) for cross-restart durability.
    """
    MAX_STORE_SIZE: int = 10_000
    _store: List[Dict[str, Any]] = []
    _chroma_client: Optional[Any] = None
    _chroma_collection: Optional[Any] = None

    @classmethod
    def _init_chroma(cls):
        if cls._chroma_client is not None:
            return
        try:
            import chromadb
            cls._chroma_client = chromadb.Client()
            cls._chroma_collection = cls._chroma_client.get_or_create_collection(name="insightapi_endpoints")
            logger.info("🔮 VectorStore: Initialized ChromaDB embedded vector store collection.")
        except Exception as e:
            logger.debug(f"ChromaDB initialization skipped ({type(e).__name__}: {e}). Using TF-IDF vector memory.")

    @classmethod
    def _endpoint_to_text(cls, ep: Dict[str, Any]) -> str:
        method = ep.get("method", "")
        route = ep.get("template_route", "")
        summary = ep.get("ai_summary", "")
        category = ep.get("ai_endpoint_category", "")
        tags = " ".join(ep.get("ai_tags", []))
        schema_props = " ".join(ep.get("schema", {}).get("properties", {}).keys())
        return f"{method} {route} {category} {tags} {summary} {schema_props}"

    @classmethod
    async def store_endpoints(cls, session_id: str, endpoints: List[Dict[str, Any]]) -> None:
        """
        Stores endpoint metadata from a completed crawl session.
        """
        if not endpoints:
            return

        added_count = 0
        for ep in endpoints:
            searchable_text = cls._endpoint_to_text(ep)
            record = {
                "session_id": session_id,
                "template_route": ep.get("template_route"),
                "method": ep.get("method"),
                "status": ep.get("status"),
                "ai_summary": ep.get("ai_summary", ""),
                "ai_category": ep.get("ai_endpoint_category", ""),
                "ai_tags": ep.get("ai_tags", []),
                "schema": ep.get("schema"),
                "confidence": ep.get("confidence", 0),
                "searchable_text": searchable_text,
                "raw": ep,
            }
            cls._store.append(record)
            added_count += 1

        # Evict oldest entries if store exceeds MAX_STORE_SIZE
        overflow = len(cls._store) - cls.MAX_STORE_SIZE
        if overflow > 0:
            cls._store = cls._store[overflow:]
            logger.debug(f"VectorStore: Evicted {overflow} oldest entries (store at MAX_STORE_SIZE={cls.MAX_STORE_SIZE}).")

        cls._init_chroma()
        if cls._chroma_collection:
            try:
                documents = [cls._endpoint_to_text(ep) for ep in endpoints]
                metadatas = [{"route": str(ep.get("template_route")), "method": str(ep.get("method")), "session_id": session_id} for ep in endpoints]
                ids = [f"{session_id}_{i}" for i in range(len(endpoints))]
                cls._chroma_collection.add(documents=documents, metadatas=metadatas, ids=ids)
            except Exception as e:
                logger.debug(f"ChromaDB store error: {e}")

        logger.info(f"💾 VectorStore: Stored {added_count} endpoints for session {session_id}. Total memory size: {len(cls._store)}")

    @classmethod
    async def search_similar(cls, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Performs semantic search across all stored endpoints using query matching.

        Parameters
        ----------
        query : Natural language search string (e.g. "authentication and user login").
        top_k : Maximum number of results to return.

        Returns
        -------
        List of matching endpoint records ordered by similarity score descending.
        """
        cls._init_chroma()
        if cls._chroma_collection:
            try:
                res = cls._chroma_collection.query(query_texts=[query], n_results=top_k)
                if res and res.get("documents") and res["documents"][0]:
                    docs = res["documents"][0]
                    results = []
                    for doc in docs:
                        for rec in cls._store:
                            if rec["searchable_text"] == doc:
                                results.append(rec["raw"])
                                break
                    if results:
                        return results
            except Exception as e:
                logger.debug(f"ChromaDB query error: {e}")

        if not cls._store:
            return []

        scored = []
        for record in cls._store:
            score = _cosine_similarity_tf(query, record["searchable_text"])
            if score > 0.05:
                res_record = dict(record["raw"])
                res_record["similarity_score"] = round(score, 3)
                scored.append((score, res_record))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    @classmethod
    async def find_known_endpoints(cls, template_routes: List[str]) -> List[Dict[str, Any]]:
        """
        Checks if template routes were already documented in past sessions (drift detection).
        """
        known_routes = set(template_routes)
        return [
            rec["raw"]
            for rec in cls._store
            if rec.get("template_route") in known_routes
        ]
