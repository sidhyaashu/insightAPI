# InsightAPI V3 — Master Architecture Audit & Production Unification

**Date**: 2026-08-19  
**Status**: Migration Complete — Unified Authoritative Runtime  
**Author**: Principal Engineer & Agent Runtime Architect

---

## 1. Executive Summary

InsightAPI AI has successfully migrated from a legacy ReAct tool-calling loop into a **single, stateful, goal-driven, evidence-producing autonomous computer-use intelligence runtime**.

The modular runtime under `apps/agent-service/app/runtime/` is now the **ONE authoritative execution path**:
- **Canonical Typed Models**: `Goal`, `AgentBudget`, `AgentState`, `Action`, `Observation`, `Evidence`, `Hypothesis`, `AgentEvent`, `DiscoveredEndpoint`, `Artifact`
- **`InvestigationRuntime`**: Single service entrypoint for HTTP, WebSocket, CLI, and Workers
- **`Supervisor.run()`**: Single canonical execution loop owning planning, delegation, policy checks, and observation recording
- **`AgentEventBus` & `EventBridge`**: Lossless wire event streaming without private chain-of-thought exposure
- **`BrowserAdapter` & `PlaywrightBrowserAdapter`**: Hands and eyes actuator querying AXTree and intercepting traffic
- **`ApplicationGraph`**: Behavioral world model capturing Pages, UI Elements, Endpoints, Parameters, and Dependencies
- **`PolicyEngine`**: Deterministic SSRF guardrails, budget limits, risk classification, and approval routing
- **Specialized Agents**: `ExplorerAgent`, `NetworkAgent`, and `VerificationAgent`
- **`HypothesisEngine`**: Multi-identifier hypothesis testing (valid, alternate, and invalid negative probes)
- **`AgentStateStore`**: Durable PostgreSQL database persistence for restart resilience
- **`ArtifactGenerator`**: OpenAPI 3.1, Postman v2.1.0, Pytest regression suites, and Markdown reports backed by real observed schemas

---

## 2. Section A: Current Execution Path Trace

| Execution Path | Entry Point | Service Layer | Agent / Engine | Tools Used | Browser Implementation | State & Persistence | Output & Artifacts | Status |
|---|---|---|---|---|---|---|---|:---:|
| **1. WebSocket Agentic Chat** | `GET /ws/chat/{chat_session_id}` in `app/routers/chat.py` | `chat_service.py:stream_agentic_chat` → `InvestigationRuntime` | `Supervisor.run()` + Specialized Agents | `PlaywrightBrowserAdapter`, `probe_http_endpoint` | `PlaywrightBrowserAdapter` | DB `ChatMessage`, `ChatSession`, PostgreSQL `CrawlSession` | Emitted wire events (`tool_start`, `tool_result`, `token`, `done`) | **UNIFIED & MIGRATED** |
| **2. Crawl HTTP API** | `GET /api/v1/reports/{session_id}` in `app/api/v1/endpoints/reports.py` | `InvestigationRuntime.get_artifacts()` / `CrawlRepository` | `Supervisor` (stored results) | N/A | N/A | PostgreSQL `CrawlSession` | `ArtifactGenerator` (OpenAPI, Postman, Pytest, Markdown) | **UNIFIED & MIGRATED** |
| **3. Authenticated Crawl** | Auth credentials resolved via `auth_vault.py:resolve_auth_headers` | Injected into `InvestigationRequest(auth_headers=...)` | `Supervisor` + `VerificationAgent` | `probe_http_endpoint`, `PlaywrightBrowserAdapter` | Playwright browser context with custom cookies/headers | `AuthProfile` in DB, `AgentState.auth_context` | Injected request headers with verified auth tags | **UNIFIED & MIGRATED** |
| **4. Report & Artifact Export** | `GET /api/v1/reports/{session_id}/export` | `reports.py:export_report` → `InvestigationRuntime.get_artifacts()` | `ArtifactGenerator` | Exporters | N/A | Reads `CrawlSession` in DB | OpenAPI JSON, Postman v2.1.0 JSON, Markdown docs, Pytest suites | **UNIFIED & MIGRATED** |
| **5. Autonomous CLI** | `python -m app.cli investigate <url>` in `app/cli.py` | `InvestigationRuntime.stream_investigation()` | `Supervisor.run()` | `PlaywrightBrowserAdapter`, `probe_http_endpoint` | `PlaywrightBrowserAdapter` | `AgentStateStore` | Exported directory (`openapi.json`, `postman.json`, `test_suite.py`) | **UNIFIED & MIGRATED** |

---

## 3. Section B: Runtime Duplication Resolution

| Architectural Concept | Legacy Implementation | New Runtime Implementation | Action Taken |
|---|---|---|---|
| **Autonomous Action Loop** | `ReActEngine.run()` while loop | `Supervisor.run()` | `ReActEngine` stripped of autonomous crawling; `Supervisor.run()` is the single autonomous loop. |
| **State Storage** | Flat in-memory dicts / strings | `AgentStateStore` with PostgreSQL DB sync | Integrated with `CrawlSession` model to survive complete process restarts. |
| **World Model Representation** | Flat `captured_endpoints` list | Typed `ApplicationGraph` | Structured graph with `Page`, `UIElement`, `Endpoint`, `Entity`, `CONTAINS`, `TRIGGERS`, `DEPENDS_ON`. |
| **Verification Logic** | Single-request status check | Multi-ID `HypothesisEngine` | Tests multiple valid and invalid resource IDs for parameterized route verification. |
| **Artifact Generation** | Mock/placeholder string substitutions | Evidence-backed `ArtifactGenerator` | Sourced strictly from observed schemas in `ApplicationGraph`. |
| **Budget Enforcement** | Hardcoded `min(5, max_pages)` loop cap | Typed `AgentBudget` | Replaced hardcoded constants with dynamic budget counters. |

---

## 4. Key Questions & Resolution Evidence

1. **Where should autonomous orchestration live?**
   - In `Supervisor.run()`. `InvestigationRuntime` coordinates lifecycle, DB sessions, and artifacts.
2. **How does state persist across restarts?**
   - `AgentStateStore` serializes `AgentState`, `ApplicationGraph`, and `Hypotheses` to PostgreSQL `CrawlSession` columns.
3. **How does ReActEngine fit in?**
   - It is strictly restricted to conversational pair-programming Q&A and ad-hoc single-step developer tools (cURL, HAR parsing).
4. **How are observations guaranteed to enter the graph?**
   - `Supervisor.run()` and `Supervisor.execute_action()` unconditionally invoke `self.world_model.record_observation(obs)`.
5. **How are parameterized endpoints verified?**
   - `HypothesisEngine.design_experiment()` formulates multi-ID probes (e.g. `/1`, `/2`, `/99999999`) and updates `HypothesisStatus`.
6. **How are artifacts sourced?**
   - Sourced from real observations and schemas in `ApplicationGraph` via `ArtifactGenerator`.
