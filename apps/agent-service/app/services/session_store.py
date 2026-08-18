"""
Local JSON Session Store for CLI and Python SDK execution.

Persists crawl session results to ~/.insightapi/sessions/<session_id>.json
so CLI commands (`insightapi list-endpoints`, `insightapi export`) can read
and export real crawl data without requiring PostgreSQL or Redis.
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

MAX_LOCAL_SESSIONS: int = 50


def get_sessions_dir() -> Path:
    """Return Path to local session storage directory (~/.insightapi/sessions)."""
    base_dir = Path.home() / ".insightapi" / "sessions"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def save_session(
    session_id: str,
    target_url: str,
    captured_endpoints: List[Dict[str, Any]],
    explored_count: int = 1,
    elapsed_time_seconds: float = 0.0,
    status: str = "completed",
    error_message: Optional[str] = None,
) -> str:
    """
    Persist a crawl session to ~/.insightapi/sessions/<session_id>.json.

    Caps total stored sessions at MAX_LOCAL_SESSIONS (prunes oldest by created_at).
    """
    sessions_dir = get_sessions_dir()

    data = {
        "session_id": session_id,
        "target_url": target_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "explored_count": explored_count,
        "elapsed_time_seconds": elapsed_time_seconds,
        "error_message": error_message,
        "captured_endpoints": captured_endpoints,
    }

    file_path = sessions_dir / f"{session_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    _prune_old_sessions(sessions_dir)
    return session_id


def get_session(session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve a saved crawl session dict.

    - If `session_id` is provided, looks for exact match or prefix match in ~/.insightapi/sessions/.
    - If `session_id` is None, returns the most recently created session (`latest`).
    """
    sessions_dir = get_sessions_dir()
    files = list(sessions_dir.glob("*.json"))
    if not files:
        return None

    if not session_id or session_id.lower() == "latest":
        def _get_created_at(p: Path) -> str:
            data = _load_file(p)
            return (data.get("created_at") if data else "") or str(p.stat().st_mtime)
        latest_file = max(files, key=_get_created_at)
        return _load_file(latest_file)

    # 1. Exact match
    exact_file = sessions_dir / f"{session_id}.json"
    if exact_file.exists():
        return _load_file(exact_file)

    # 2. Prefix match
    matches = [f for f in files if f.stem.startswith(session_id)]
    if matches:
        # Pick most recent match if multiple
        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return _load_file(matches[0])

    return None


def list_sessions() -> List[Dict[str, Any]]:
    """
    List all stored sessions sorted by created_at descending.

    Returns a list of summary dicts (without full payload noise).
    """
    sessions_dir = get_sessions_dir()
    files = list(sessions_dir.glob("*.json"))
    sessions: List[Dict[str, Any]] = []

    for f in files:
        session_data = _load_file(f)
        if session_data:
            captured = session_data.get("captured_endpoints", [])
            rest_count = sum(1 for ep in captured if not ep.get("graphql_operation_name") and ep.get("method") != "WS")
            graphql_count = sum(1 for ep in captured if ep.get("graphql_operation_name"))

            sessions.append({
                "session_id": session_data.get("session_id", f.stem),
                "target_url": session_data.get("target_url", "N/A"),
                "created_at": session_data.get("created_at", ""),
                "status": session_data.get("status", "unknown"),
                "explored_count": session_data.get("explored_count", 1),
                "elapsed_time_seconds": session_data.get("elapsed_time_seconds", 0.0),
                "endpoint_count": len(captured),
                "rest_count": rest_count,
                "graphql_count": graphql_count,
            })

    sessions.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return sessions


def _load_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _prune_old_sessions(sessions_dir: Path) -> None:
    files = list(sessions_dir.glob("*.json"))
    if len(files) <= MAX_LOCAL_SESSIONS:
        return

    # Sort oldest first
    files.sort(key=lambda p: p.stat().st_mtime)
    num_to_delete = len(files) - MAX_LOCAL_SESSIONS
    for f in files[:num_to_delete]:
        try:
            f.unlink()
        except OSError:
            pass
