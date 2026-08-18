# InsightAPI V3 — Master Runtime Wiring Audit

**Date**: 2026-08-19  
**Status**: Comprehensive Wiring & Execution Audit  
**Author**: Principal Engineer & Agent Runtime Architect

---

## 1. End-to-End Execution Path Matrix

| Path | Entrypoint | Runtime Layer | Supervisor Loop | Specialized Agents | Browser Actuator | Observations Pipeline | Application World Model | Durable Persistence | Artifact Generation | UI Rendering / Client | Wiring Status |
|---|---|---|---|---|---|---|---|---|---|---|:---:|
| **A. WebSocket Chat** | `GET /ws/chat/{session_id}` in `app/routers/chat.py` | `chat_service.py:stream_agentic_chat` → `InvestigationRuntime` | `Supervisor.run()` (Delegated) | `ExplorerAgent`, `NetworkAgent`, `VerificationAgent` | `PlaywrightBrowserAdapter` | Normalized `Observation` stream | `ApplicationGraph` updated per observation | `AgentStateStore` via `CrawlSession` DB | `ArtifactGenerator` via `get_artifacts()` | `apps/client/src/components/chat/` (`tool_start`, `tool_result`, `token`) | **CONNECTED** |
| **B. HTTP API** | `POST /api/v1/crawls` & `GET /api/v1/crawls/{id}` | `InvestigationRuntime.start_investigation()` | `Supervisor.run()` | `ExplorerAgent`, `NetworkAgent`, `VerificationAgent` | `PlaywrightBrowserAdapter` | `Observation` models recorded | `ApplicationGraph` | `CrawlRepository` / `CrawlSession` | `ArtifactGenerator` | JSON API response | **CONNECTED** |
| **C. CLI Tool** | `python -m app.cli investigate <url>` in `app/cli.py` | `InvestigationRuntime.stream_investigation()` | `Supervisor.run()` | `ExplorerAgent`, `NetworkAgent`, `VerificationAgent` | `PlaywrightBrowserAdapter` | Emitted observations | `ApplicationGraph` | `AgentStateStore` file/DB output | Written to `--output-dir` (OpenAPI, Postman, Pytest, Report) | Terminal stdout stream | **CONNECTED** |
| **D. Report Retrieval** | `GET /api/v1/reports/{session_id}` in `reports.py` | `InvestigationRuntime.get_artifacts()` | N/A (Read) | N/A | N/A | Reads stored observations | Loaded from DB `world_model` | `CrawlSession.llm_metrics_json` | `ArtifactGenerator.generate_discovery_report()` | Frontend dashboard report view | **CONNECTED** |
| **E. Artifact Export** | `GET /api/v1/reports/{session_id}/export` | `InvestigationRuntime.get_artifacts()` | N/A (Read) | N/A | N/A | Verified schema representations | Loaded from `ApplicationGraph` | `CrawlSession` in PostgreSQL | OpenAPI 3.1, Postman v2.1.0, Pytest suites, Markdown | Direct file download response | **CONNECTED** |
| **F. Authenticated Investigation** | `auth_vault.py:resolve_auth_headers` injected into `InvestigationRequest` | `InvestigationRuntime.stream_investigation()` | `Supervisor.execute_action()` with `state.auth_context` | `VerificationAgent.verify_endpoint()` & `ExplorerAgent` | Playwright context headers/cookies | Authenticated vs unauthenticated comparisons | `ApplicationGraph` auth annotations | `CrawlSession` DB | Auth requirements in OpenAPI & Postman | UI lock/shield indicators | **CONNECTED** |
| **G. Resume Investigation** | `InvestigationRuntime.resume_investigation()` | `InvestigationRuntime` | Restored `Supervisor` with rehydrated state | Re-invoked specialized agents | `PlaywrightBrowserAdapter` | Re-linked historical observations | Deserialized `ApplicationGraph.from_dict()` | Loaded from PostgreSQL `CrawlSession` | Regenerated from restored graph | Reconnected WebSocket / Stream | **CONNECTED** |
| **H. Human Approval** | `PolicyEngine.evaluate()` returning `REQUIRE_APPROVAL` | `InvestigationRuntime.approve_action()` | `Supervisor.execute_action()` unblocks approved keys | Delegated to specialized agent | `PlaywrightBrowserAdapter` / `probe_http_endpoint` | Action recorded post-approval | Graph updated with approved action node | Appends to approved action list in DB | Included in action traces | UI Approval Modal / Action Card | **CONNECTED** |
| **I. Frontend Event Rendering** | `apps/client/src/features/chatbot/` | WebSocket connection to `/ws/chat/{id}` | Broadcast over `AgentEventBus` → `EventBridge` | Real-time tool telemetry | Browser status badges | Observation summaries | Graph topology visualization | Local session cache + DB sync | Generated specs & download buttons | Dynamic step cards, tool accordions, markdown renderer | **CONNECTED** |
| **J. Gateway WS Proxy** | `apps/gateway/app/api/v1/endpoints/ws.py:ws_proxy` | Reverse proxy `/ws/*` to `agent-service` | Transparent WebSocket forwarding | N/A | N/A | Bidirectional JSON message streaming | N/A | Injects user auth headers | N/A | Frontend WebSocket client | **CONNECTED** |

---

## 2. Component Ownership Governance

```
                    INVESTIGATION RUNTIME
             (Lifecycle, Persistence, Artifacts)
                             │
                             ▼
                         SUPERVISOR
              (Autonomous Planning & Decisions)
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
    ExplorerAgent       NetworkAgent      VerificationAgent
    (DOM & Browser)     (Traffic & REST)   (Skeptical Probes)
         └───────────────────┬───────────────────┘
                             ▼
                        OBSERVATION
                             │
                             ▼
                     APPLICATION GRAPH
               (Behavioral World Model Truth)
```

1. **InvestigationRuntime** (`app/runtime/service.py`):
   - **Owns**: Session lifecycle, database session injection, state loading/resuming, artifact generation dispatch, and client stream coordination.
   - **Does NOT own**: Autonomous while loop or action planning.
2. **Supervisor** (`app/runtime/supervisor.py`):
   - **Owns**: The single canonical autonomous loop (`Supervisor.run()`), information-gain action selection, policy enforcement checks, and ensuring every agent observation is recorded in `ApplicationGraph`.
   - **Does NOT own**: Client HTTP/WS wire serialization or DB connection pooling.
3. **Specialized Agents** (`app/runtime/agents/`):
   - **Owns**: Specialized execution (`ExplorerAgent` for browser navigation & AXTree, `NetworkAgent` for HTTP/HAR traffic, `VerificationAgent` for multi-identifier parameter probes).
   - **Does NOT own**: Global planning or artifact creation.
4. **ApplicationGraph** (`app/runtime/world_model.py`):
   - **Owns**: Structured application topology (Pages, UI Elements, Endpoints, Parameters, Relationships, Dependencies).
   - **Does NOT own**: Ephemeral chat transcript history.
5. **AgentStateStore** (`app/runtime/persistence.py`):
   - **Owns**: Durable PostgreSQL persistence and serialization for `AgentState`, `ApplicationGraph`, and `Hypotheses` to survive process restarts.

---

## 3. P0 Action Items & Implementation Plan

1. **Remove Autonomous Execution Duplication**:
   - Verify that `InvestigationRuntime.stream_investigation()` and `start_investigation()` solely delegate the action loop to `Supervisor.run()` or step execution via `Supervisor`.
2. **Observation Flow Guarantee**:
   - Ensure `Supervisor.run()` and `Supervisor.execute_action()` unconditionally update `self.world_model.record_observation(obs)` for all observations produced by child agents.
3. **Database Session Injection**:
   - Ensure `app/routers/chat.py` passes the `db: AsyncSession` dependency to `stream_agentic_chat(...)` and `InvestigationRuntime` so every WebSocket message writes to PostgreSQL.
4. **Isolate Legacy ReActEngine**:
   - Ensure `ReActEngine` in `app/services/react_engine.py` is strictly restricted to general conversational pair-programming Q&A and ad-hoc single-step developer tools (cURL, HAR parsing), with zero autonomous discovery capabilities.
5. **Reports Sourced from ApplicationGraph**:
   - Ensure `app/api/v1/endpoints/reports.py` uses `InvestigationRuntime.get_artifacts(session_id, db=db)` as the authoritative source of truth.
