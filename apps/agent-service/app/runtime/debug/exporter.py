"""
runtime/debug/exporter.py — Debug Session Archive Exporter.

Utilities to package debug sessions into structured archive dictionaries
or JSON bundles for developer inspection and offline analysis.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.runtime.debug.models import DebugSession
from app.runtime.debug.recorder import recorder
from app.runtime.debug.profiler import profiler
from app.runtime.debug.diagnostics import MissingEndpointAnalyzer
from app.runtime.world_model import ApplicationGraph


class DebugExporter:
    """
    Exports full debug bundles for an investigation session.
    """

    @staticmethod
    def export_session_bundle(session_id: str) -> Dict[str, Any]:
        """Compile all in-memory and persisted traces into a single inspectable bundle."""
        session = recorder.get_session(session_id)
        profile = profiler.get_profile(session_id)

        return {
            "session_id": session_id,
            "session": session.model_dump() if session else None,
            "timeline": recorder.get_timeline(session_id),
            "actions": recorder.get_actions(session_id),
            "network": recorder.get_network(session_id),
            "errors": recorder.get_errors(session_id),
            "hypotheses": recorder.get_hypotheses(session_id),
            "profile": profile.model_dump(),
        }

    @staticmethod
    def analyze_missing(target_endpoint: str, session_id: str, graph: Optional[ApplicationGraph] = None) -> Dict[str, Any]:
        """Run missing endpoint diagnosis on a session."""
        effective_graph = graph or ApplicationGraph(session_id=session_id)
        actions = recorder.get_actions(session_id)
        network = recorder.get_network(session_id)
        diag = MissingEndpointAnalyzer.analyze(
            target_endpoint=target_endpoint,
            session_id=session_id,
            graph=effective_graph,
            actions=actions,
            network_traces=network,
        )
        return diag.model_dump()
