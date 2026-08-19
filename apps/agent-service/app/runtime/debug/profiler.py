"""
runtime/debug/profiler.py — Performance Profiling & Resource Diagnostics.

Measures and aggregates execution latencies across Planning, Browser, Network,
Model, Persistence, and Artifact generation phases with percentiles (Debug Prompt §35, §36).
"""
from __future__ import annotations

import statistics
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PhaseLatencyStats(BaseModel):
    """Latency distribution statistics for a specific runtime phase."""
    count: int = 0
    total_ms: int = 0
    min_ms: int = 0
    p50_ms: int = 0
    p95_ms: int = 0
    max_ms: int = 0


class InvestigationProfile(BaseModel):
    """Aggregated performance and resource profile for an investigation."""
    session_id: str
    total_duration_ms: int = 0
    phases: Dict[str, PhaseLatencyStats] = Field(default_factory=dict)
    resource_counters: Dict[str, int] = Field(default_factory=dict)


class Profiler:
    """
    Tracks and aggregates phase latencies and resource counters for an investigation session.
    """

    def __init__(self) -> None:
        self._latencies: Dict[str, Dict[str, List[int]]] = {}  # session_id -> phase -> [latencies_ms]
        self._resources: Dict[str, Dict[str, int]] = {}        # session_id -> resource -> count
        self._start_times: Dict[str, float] = {}              # session_id -> start_perf_counter

    def start_session(self, session_id: str) -> None:
        """Mark investigation start time."""
        self._start_times[session_id] = time.perf_counter()
        self._latencies[session_id] = {
            "planning": [],
            "browser": [],
            "network": [],
            "model": [],
            "persistence": [],
            "artifact": [],
        }
        self._resources[session_id] = {
            "browser_actions": 0,
            "network_requests": 0,
            "model_calls": 0,
            "graph_mutations": 0,
            "db_persists": 0,
        }

    def record_phase(self, session_id: str, phase: str, duration_ms: int) -> None:
        """Record elapsed duration for a phase."""
        if session_id not in self._latencies:
            self.start_session(session_id)
        self._latencies[session_id].setdefault(phase, []).append(max(0, duration_ms))

    def increment_resource(self, session_id: str, resource_name: str, count: int = 1) -> None:
        """Increment a tracked resource counter."""
        if session_id not in self._resources:
            self.start_session(session_id)
        self._resources[session_id][resource_name] = self._resources[session_id].get(resource_name, 0) + count

    def get_profile(self, session_id: str) -> InvestigationProfile:
        """Calculate and return percentile-aggregated profile."""
        start_time = self._start_times.get(session_id, time.perf_counter())
        total_duration_ms = int((time.perf_counter() - start_time) * 1000)

        phase_stats: Dict[str, PhaseLatencyStats] = {}
        session_latencies = self._latencies.get(session_id, {})

        for phase, latencies in session_latencies.items():
            if not latencies:
                phase_stats[phase] = PhaseLatencyStats()
                continue
            sorted_lat = sorted(latencies)
            n = len(sorted_lat)
            p50_idx = int(0.50 * (n - 1))
            p95_idx = int(0.95 * (n - 1))

            phase_stats[phase] = PhaseLatencyStats(
                count=n,
                total_ms=sum(sorted_lat),
                min_ms=sorted_lat[0],
                p50_ms=sorted_lat[p50_idx],
                p95_ms=sorted_lat[p95_idx],
                max_ms=sorted_lat[-1],
            )

        return InvestigationProfile(
            session_id=session_id,
            total_duration_ms=total_duration_ms,
            phases=phase_stats,
            resource_counters=dict(self._resources.get(session_id, {})),
        )

    def clear(self, session_id: Optional[str] = None) -> None:
        """Clear profiler data."""
        if session_id:
            self._latencies.pop(session_id, None)
            self._resources.pop(session_id, None)
            self._start_times.pop(session_id, None)
        else:
            self._latencies.clear()
            self._resources.clear()
            self._start_times.clear()


# Global profiler singleton
profiler = Profiler()
