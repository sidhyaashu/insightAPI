"""
runtime/agents/__init__.py — InsightAPI Specialized Agent Roles.

Reference (AGENTS.md §15):
  - ExplorerAgent: Responsible for browser navigation, AXTree, DOM context, forms, clicks, SPA states.
  - NetworkAgent: Responsible for REST, GraphQL, WebSocket, headers, parameters, route normalization.
  - VerificationAgent: Skeptical, evidence-driven replay, auth requirement confirmation, schema validation.
"""
from app.runtime.agents.base import BaseAgent, AgentTask, AgentResult
from app.runtime.agents.recon import ReconAgent
from app.runtime.agents.explorer import ExplorerAgent
from app.runtime.agents.network import NetworkAgent
from app.runtime.agents.verifier import VerificationAgent

__all__ = [
    "BaseAgent",
    "AgentTask",
    "AgentResult",
    "ReconAgent",
    "ExplorerAgent",
    "NetworkAgent",
    "VerificationAgent",
]
