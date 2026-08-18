# InsightAPI V3 — Master Architecture Audit & Production Unification

**Date**: 2026-08-19  
**Status**: Comprehensive Architecture Audit (Phase 0)  
**Author**: Principal Engineer & Agent Runtime Architect

---

## 1. Executive Summary

InsightAPI AI is evolving from a multi-step ReAct tool-calling loop into a **single, stateful, goal-driven, evidence-producing autonomous computer-use intelligence runtime**.

A complete modular runtime has already been constructed under `apps/agent-service/app/runtime/`:
- Canonical Typed Models (`Goal`, `AgentBudget`, `AgentState`, `Action`, `Observation`, `Evidence`, `Hypothesis`, `AgentEvent`, `DiscoveredEndpoint`, `Artifact`)
- `AgentEventBus` & `EventBridge`
- `BrowserAdapter` ABC & `PlaywrightBrowserAdapter`
- `ApplicationGraph` Behavioral World Model
- `PolicyEngine` (SSRF guardrails, budget limits, risk classification, approval routing)
- Specialized Agents (`ExplorerAgent`, `NetworkAgent`, `VerificationAgent`)
- `Supervisor` Information-Gain Planning Loop
- `HypothesisEngine` & Verification Engine
- `AgentStateStore` & `SessionTelemetryTracker`
- `ArtifactGenerator` (OpenAPI, Postman, Pytest, Markdown Reports)

However, **the production execution paths are currently fractured**:
1. `chat_service.py` and `chat.py` still invoke legacy `ReActEngine.run()`.
2. `reports.py` falls back to in-memory `CRAWL_SESSIONS` dictionaries.
3. `AgentStateStore` currently uses in-memory Python dictionaries rather than durable PostgreSQL tables.
4. There is no unified `InvestigationRuntime` service entrypoint shared across HTTP, WebSocket, CLI, and Background Workers.

This audit maps the current execution paths, identifies all duplicated concepts, resolves the 10 critical architecture questions with code evidence, and defines the exact step-by-step migration to make the new runtime the **ONE authoritative execution path**.

---

## 2. Section A: Current Execution Path Trace

| Execution Path | Entry Point | Service Layer | Agent / Engine | Tools Used | Browser Implementation | State & Persistence | Output & Artifacts |
|---|---|---|---|---|---|---|---|
| **1. WebSocket Agentic Chat** | `GET /ws/chat/{chat_session_id}` in `app/routers/chat.py` | `chat_service.py:stream_agentic_chat` | `ReActEngine.run()` in `services/react_engine.py` (legacy) | `probe_http_endpoint`, `execute_curl`, `parse_har_traffic`, `explore_web_app_browser` | `PlaywrightBrowserAdapter` (via `browser_explorer.py`) | DB `ChatMessage`, `ChatSession`; in-memory ReAct list | Raw dict events: `tool_start`, `tool_result`, `token`, `done` |
| **2. Crawl HTTP API** | `GET /api/v1/reports/{session_id}` in `app/api/v1/endpoints/reports.py` | `CrawlRepository` / `CRAWL_SESSIONS` | None (reads pre-existing crawl outputs) | N/A | N/A | PostgreSQL `CrawlSession` / memory dict | `OpenAPIExporter`, `PostmanExporter`, `MarkdownExporter` |
| **3. Authenticated Crawl** | Auth credentials resolved via `auth_vault.py:resolve_auth_headers` | Injected into `stream_agentic_chat(auth_headers=...)` | `ReActEngine` passes headers to tool calls | `probe_http_endpoint`, `explore_web_app_browser` | Playwright browser context with custom cookies/headers | `AuthProfile` in DB | Injected request headers |
| **4. Report & Artifact Export** | `GET /api/v1/reports/{session_id}/export` | `reports.py:export_report` | `OpenAPIExporter`, `PostmanExporter`, `MarkdownExporter`, `playwright_test_gen.py` | Exporters | N/A | Reads `CrawlSession` in DB | OpenAPI JSON, Postman v2.1.0 JSON, Markdown docs, Playwright scripts |
| **5. Autonomous Runtime Path** *(New)* | `Supervisor.run()` in `app/runtime/supervisor.py` | `Supervisor` + `HypothesisEngine` | `ExplorerAgent`, `NetworkAgent`, `VerificationAgent` | `PlaywrightBrowserAdapter`, `probe_http_endpoint`, `infer_openapi_schema`, `execute_curl` | `PlaywrightBrowserAdapter` | `AgentStateStore` (in-memory) + `ApplicationGraph` | `ArtifactGenerator` (OpenAPI, Postman, Pytest, Evidence Report) |

---

## 3. Section B: Runtime Duplication Analysis

| Architectural Concept | Legacy Implementation | New Runtime Implementation | Action Required |
|---|---|---|---|
| **Planning & Orchestration** | Hardcoded loop in `ReActEngine.run()` (`react_engine.py`) | Information-gain planning in `Supervisor` (`supervisor.py`) | Route all chat/crawl execution through `Supervisor`; deprecate `ReActEngine` as legacy fallback. |
| **Agent State Model** | Informal `history: list[dict]` + `telemetry_log: list[str]` | Typed `AgentState` with budget, visited URLs, observations, hypotheses | Use `AgentState` as the sole working memory across all services. |
| **Browser Execution** | `explore_web_app_browser` in `tools/browser_explorer.py` | `PlaywrightBrowserAdapter` (`app/runtime/browser/`) | `browser_explorer.py` now delegates to `PlaywrightBrowserAdapter`; enforce all browser interactions through `BrowserAdapter`. |
| **Endpoint Discovery & Schema** | Ad-hoc `discovered_endpoints: list[dict]` in `react_engine.py` | `ApplicationGraph.add_endpoint` & `DiscoveredEndpoint` models | Ingest all discovered endpoints directly into `ApplicationGraph`. |
| **Verification** | Single-shot re-probes inside ReAct execution | `HypothesisEngine` + `VerificationAgent` (parameter testing & auth checks) | Unify verification onto `VerificationAgent` & `HypothesisEngine`. |
| **Event Streaming** | Raw dicts `{"type": "tool_start", ...}` | Typed `AgentEvent` on `AgentEventBus` bridged to wire format | `EventBridge` handles wire serialization; emit `AgentEvent` everywhere. |
| **Artifact Generation** | Standalone exporters in `app/services/` | `ArtifactGenerator` in `app/runtime/artifacts.py` wrapping exporters | Standardize on `ArtifactGenerator` as product artifact pipeline. |
| **Policy & Safety** | `_is_action_destructive()` helper in `react_engine.py` | `PolicyEngine` (SSRF, allowed domains, budgets, approval routing) | Eliminate duplicate regex checks; use `PolicyEngine` exclusively. |
| **Persistence** | In-memory `CRAWL_SESSIONS` dict + `CrawlSession` DB table | `AgentStateStore` (in-memory dict cache) | Bridge `AgentStateStore` to durable PostgreSQL models (`agent_sessions`, `agent_events`). |

---

## 4. Section C: Runtime Integration Status Matrix

| Capability | Status | Notes |
|---|:---:|---|
| **Canonical Models (`AgentState`, `Goal`, `Observation`, etc.)** | **IMPLEMENTED + WIRED** | Fully typed, 100% test coverage in `tests/runtime/`. |
| **Agent Event Bus (`AgentEventBus`)** | **IMPLEMENTED + WIRED** | High performance pub/sub, bridged to ReAct wire protocol. |
| **Browser Adapter (`PlaywrightBrowserAdapter`)** | **IMPLEMENTED + WIRED** | Stealth evasion, shadow DOM piercing, AXTree, GraphQL/REST interception. |
| **Application World Model (`ApplicationGraph`)** | **IMPLEMENTED BUT NOT WIRED** | Fully built & tested, but `chat_service.py` currently bypasses it. |
| **Specialized Agents (`Explorer`, `Network`, `Verifier`)** | **IMPLEMENTED BUT NOT WIRED** | Built & tested, but production WebSocket route calls `ReActEngine`. |
| **Supervisor Planning Loop (`Supervisor`)** | **IMPLEMENTED BUT NOT WIRED** | Ready for production wiring; needs service-level entrypoint. |
| **Hypothesis & Verification Engine** | **IMPLEMENTED BUT NOT WIRED** | Tested in isolation; needs integration into main runtime pipeline. |
| **Durable Database Persistence** | **PARTIAL** | DB has `CrawlSession` & `ChatSession`; `AgentStateStore` needs SQLAlchemy bridge. |
| **Observability & Telemetry** | **IMPLEMENTED + WIRED** | `SessionTelemetryTracker` auto-subscribes to `AgentEventBus`. |
| **Artifact Pipeline (`ArtifactGenerator`)** | **IMPLEMENTED + WIRED** | Produces OpenAPI, Postman, Pytest, and Evidence Reports. |

---

## 5. Section D: Answers to Critical Questions (§36)

### A. Is the new Supervisor actually used by production crawl/chat paths?
- **Answer**: **NO.** Currently, `app/routers/chat.py` calls `stream_agentic_chat()`, which delegates directly to `ReActEngine.run()`. `Supervisor` is only invoked in `tests/runtime/test_supervisor.py`.
- **Evidence**: `apps/agent-service/app/services/chat_service.py:72` calls `ReActEngine.run(...)`.

### B. Is services/react_engine.py still acting as a second agent runtime?
- **Answer**: **YES.** `ReActEngine` contains its own ReAct step counter, regex extractors, and hardcoded tool calling logic, acting as an ununified second runtime.

### C. Is AgentState persistence truly durable or currently in-process only?
- **Answer**: **IN-PROCESS ONLY.** `AgentStateStore` in `app/runtime/persistence.py` stores data in Python dictionaries (`_state_cache`, `_graph_cache`, `_hypotheses_cache`). A process crash or restart wipes all active state.

### D. Does every Explorer/Network/Verifier observation reach ApplicationGraph?
- **Answer**: **NO.** When running via `Supervisor`, observations reach `ApplicationGraph`. But when running via `chat_service.py` / `ReActEngine`, observations are stored as strings in `telemetry_log` and never update `ApplicationGraph`.

### E. Does verification genuinely test parameterization, or mainly replay the original URL?
- **Answer**: **PARTIALLY.** `HypothesisEngine` creates test cases with invalid IDs (`99999999`) and unauthenticated requests, but `VerificationAgent` was running basic probes. It must be expanded into a multi-identifier parameter verification pipeline.

### F. Are artifact examples and response bodies sourced from real observations?
- **Answer**: **PARTIALLY.** In `ArtifactGenerator`, real response bodies were previously substituted with `example_url` in example payloads. Real observation bodies from `Observation.response_body` must be passed into `OpenAPIExporter` and `PostmanExporter`.

### G. Are runtime events persisted and streamed consistently?
- **Answer**: **STREAMED YES, PERSISTED NO.** `publish_raw` pushes events to `AgentEventBus` and `SessionTelemetryTracker`, but events are not saved to a PostgreSQL `agent_events` table.

### H. Does Chat UI reflect runtime events rather than legacy tool events?
- **Answer**: **PARTIALLY.** The WebSocket emits `tool_start`, `tool_result`, `approval_required`, and `token` dicts. It needs to emit standard `AgentEvent` payloads (`plan_created`, `endpoint_discovered`, `endpoint_verified`, etc.) while retaining backward compatibility.

### I. Does CLI use the same runtime as web/API execution?
- **Answer**: **NO UNIFIED RUNTIME ENTRYPOINT YET.** There is no shared `InvestigationRuntime` service class.

### J. Can the system resume after service restart?
- **Answer**: **NO.** Because runtime state is in-memory, restarting the container resets the investigation.

---

## 6. Section E: V3 Blocker Ranking

### 🚨 P0 (Must Ship for V3 Beta Launch)
1. **Single Runtime Entrypoint (`InvestigationRuntime`)**: Unified service layer orchestrating `Supervisor`, `AgentState`, `PolicyEngine`, and `ApplicationGraph`.
2. **Wire Production Paths to `InvestigationRuntime`**: Wire `chat_service.py` and `app/routers/chat.py` to stream through `InvestigationRuntime` / `Supervisor`.
3. **Durable Database Persistence**: Bridge `AgentStateStore` to SQLAlchemy (`CrawlSession` / `agent_state_json`, `world_model_json`, `hypotheses_json`) so investigations survive process restarts.
4. **Artifact Integrity Fix**: Ensure real captured request/response bodies from `Observation` are injected into OpenAPI schemas and Postman collections without fakes or mock strings.
5. **Multi-Parameter Verification Pipeline**: Strengthen `VerificationAgent` to test observed IDs vs candidate IDs before certifying endpoints.

### 🟡 P1 (Important Post-Core Solidification)
1. CLI entrypoint script `insightapi investigate <target_url>`.
2. Event replay API endpoint (`GET /api/v1/sessions/{id}/events`).
3. Richer multi-hop graph relationship algorithms.

### ⚪ P2 (Future Post-Launch Roadmap)
1. Offensive security vulnerability automation (see `docs/V3_DEFERRED.md`).
2. Remote cloud browser cluster adapters.
3. Dedicated Neo4j graph database.

---

## 7. Migration Plan to One Authoritative Runtime

```
[Chat WebSocket / REST / CLI]
               │
               ▼
   [InvestigationRuntime] (Single Entrypoint)
               │
         ┌─────┴─────┐
         ▼           ▼
   [Supervisor] [AgentStateStore (PostgreSQL)]
         │
   ┌─────┼─────────────┐
   ▼     ▼             ▼
Explorer Network   Verification
   Agent  Agent       Agent
   └─────┼─────────────┘
         ▼
  [ApplicationGraph]
         │
         ▼
  [ArtifactGenerator]
```

### Execution Steps:
1. **Step 1: Create `InvestigationRuntime` (`app/runtime/service.py`)**:
   - Provide `start_investigation()`, `stream_investigation()`, `resume_investigation()`, `approve_action()`, `get_artifacts()`.
2. **Step 2: Connect Durable PostgreSQL Persistence to `AgentStateStore`**:
   - Save `AgentState`, `ApplicationGraph`, `Hypotheses`, and `AgentEvents` into `CrawlSession` / database models.
3. **Step 3: Route `chat_service.py` & `app/routers/chat.py` through `InvestigationRuntime`**:
   - Seamlessly stream `AgentEvent` payloads over WebSocket with backward-compatible event wrapping.
4. **Step 4: Fix Artifact Generator Data Sourcing**:
   - Ensure real observation response payloads populate OpenAPI 3.1 `examples` and schemas.
5. **Step 5: Verify End-to-End with Regression & Integration Tests**:
   - Confirm all 117+ tests pass and process restart resumes investigation state cleanly.
