"""
api/v1/endpoints/debug.py — Developer Inspection & Real-time Debug API Routes.

Exposes developer endpoints to inspect investigation lifecycles, timeline traces,
sanitized network events, errors, graph state, and AI diagnostic reports
(Debug Prompt §30, §34).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.runtime.debug.recorder import recorder
from app.runtime.debug.exporter import DebugExporter
from app.runtime.debug.profiler import profiler
from app.runtime.persistence import AgentStateStore
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/internal/debug/investigations", tags=["internal-debug"])
state_store = AgentStateStore()


class MissingEndpointAnalysisRequest(BaseModel):
    target_endpoint: str


@router.get("/{session_id}", response_model=Dict[str, Any])
async def get_investigation_debug_session(session_id: str):
    """Retrieve top-level debug session metadata, status, and profile."""
    session = recorder.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Debug session '{session_id}' not found.",
        )
    profile = profiler.get_profile(session_id)
    return {
        "session": session.model_dump(),
        "profile": profile.model_dump(),
    }


@router.get("/{session_id}/timeline", response_model=List[str])
async def get_investigation_timeline(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Retrieve the human-readable chronological timeline."""
    timeline = recorder.get_timeline(session_id)
    return timeline[:limit]


@router.get("/{session_id}/actions", response_model=List[Dict[str, Any]])
async def get_investigation_actions(
    session_id: str,
    action_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
):
    """Retrieve all autonomous action traces for a session."""
    actions = recorder.get_actions(session_id)
    if action_type:
        actions = [a for a in actions if a.get("action_type") == action_type]
    return actions[:limit]


@router.get("/{session_id}/network", response_model=List[Dict[str, Any]])
async def get_investigation_network_traces(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Retrieve sanitized network request/response traces."""
    network = recorder.get_network(session_id)
    return network[:limit]


@router.get("/{session_id}/errors", response_model=List[Dict[str, Any]])
async def get_investigation_errors(session_id: str):
    """Retrieve all error traces and exceptions logged during an investigation."""
    return recorder.get_errors(session_id)


@router.get("/{session_id}/hypotheses", response_model=List[Dict[str, Any]])
async def get_investigation_hypotheses(session_id: str):
    """Retrieve all endpoint hypotheses, experiment designs, and evaluations."""
    return recorder.get_hypotheses(session_id)


@router.get("/{session_id}/graph", response_model=Dict[str, Any])
async def get_investigation_world_model(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the serialized ApplicationGraph world model."""
    world_model = await state_store.load_world_model(session_id, db=db)
    if not world_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ApplicationGraph for session '{session_id}' not found.",
        )
    return world_model.to_dict()


@router.get("/{session_id}/bundle", response_model=Dict[str, Any])
async def get_investigation_debug_bundle(session_id: str):
    """Export the complete debug bundle for an investigation session."""
    return DebugExporter.export_session_bundle(session_id)


@router.post("/{session_id}/analyze-missing", response_model=Dict[str, Any])
async def analyze_missing_endpoint(
    session_id: str,
    req: MissingEndpointAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """Walk backward through the execution chain to diagnose why an expected endpoint was missed."""
    world_model = await state_store.load_world_model(session_id, db=db)
    return DebugExporter.analyze_missing(
        target_endpoint=req.target_endpoint,
        session_id=session_id,
        graph=world_model,
    )
