# InsightAPI V3 — Master Runtime Wiring Specification

**Status**: Verified Authoritative Dependency Graph  
**Architecture Reference**: [.agents/AGENTS.md](file:///c:/Users/ashut/Devlopments/InsightAPI/.agents/AGENTS.md) | [docs/ARCHITECTURE_AUDIT.md](file:///c:/Users/ashut/Devlopments/InsightAPI/docs/ARCHITECTURE_AUDIT.md)

---

## 1. End-to-End System Execution Graph

```
                                [USER]
                                   │
                                   ▼
                           [INSIGHTAPI UI]
                      (Next.js Dashboard & Chat)
                                   │
                                   ▼
                           [GATEWAY REVERSE PROXY]
                        (/ws/chat/* & /api/v1/*)
                                   │
                                   ▼
                         [AGENT ROUTER & API]
                        (app/routers/chat.py)
                                   │
                                   ▼
                          [CHAT SERVICE LAYER]
                      (app/services/chat_service.py)
                                   │
                                   ▼
                        [INVESTIGATION RUNTIME]
                      (app/runtime/service.py)
                                   │
                                   ▼
                         [SUPERVISOR ENGINE]
                     (app/runtime/supervisor.py)
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
       [ExplorerAgent]       [NetworkAgent]     [VerificationAgent]
      (DOM / AXTree / UI)    (Traffic / REST)    (Multi-ID Probes)
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   ▼
                          [BROWSER / NETWORK]
                     (PlaywrightBrowserAdapter)
                                   │
                                   ▼
                        [OBSERVATION PIPELINE]
                      (app/runtime/models.py)
                                   │
                                   ▼
                        [APPLICATION WORLD MODEL]
                     (app/runtime/world_model.py)
                                   │
                                   ▼
                         [HYPOTHESIS & VERIFIER]
                     (app/runtime/hypothesis.py)
                                   │
                                   ▼
                      [DURABLE STATE PERSISTENCE]
                     (PostgreSQL CrawlSession DB)
                                   │
                                   ▼
                         [ARTIFACT GENERATOR]
                      (OpenAPI / Postman / Pytest)
                                   │
                                   ▼
                           [STREAMED TO UI]
                      (Real-time Wire Telemetry)
```

---

## 2. Component Role & Boundaries

1. **Frontend (`apps/client/`)**:
   - Renders interactive step cards (`tool_start`, `tool_result`), human-in-the-loop approval dialogs (`approval_required`), live streamed synthesis tokens, and artifact download buttons.
2. **Gateway (`apps/gateway/`)**:
   - Manages JWT authentication, rate limiting, and forwards WebSocket traffic seamlessly to `agent-service`.
3. **Investigation Router (`app/routers/chat.py`)**:
   - Handles WebSocket connections, resolves DB sessions (`AsyncSession`), checks user quotas, and forwards requests to the chat service.
4. **Chat Service (`app/services/chat_service.py`)**:
   - Intent router: Identifies autonomous investigation requests vs conversational pair-programming Q&A.
5. **Investigation Runtime (`app/runtime/service.py`)**:
   - Coordinates session lifecycle, state store initialization, database persistence transactions, and artifact generation.
6. **Supervisor (`app/runtime/supervisor.py`)**:
   - Executes the canonical autonomous loop, plans information-gain actions, delegates tasks to child agents, and enforces observation recording.
7. **Specialized Agents (`app/runtime/agents/`)**:
   - `ExplorerAgent`: Navigates SPAs, queries the accessibility tree (AXTree), and performs safe UI actions.
   - `NetworkAgent`: Intercepts and parses REST, GraphQL, WebSocket, and SSE network traffic.
   - `VerificationAgent`: Replays discovered endpoints with varied parameter values (valid, alternate, and invalid negative probes).
8. **ApplicationGraph (`app/runtime/world_model.py`)**:
   - The authoritative in-memory and relational representation of the target application's behavioral topology.
9. **Persistence Layer (`app/runtime/persistence.py`)**:
   - Saves and reloads `AgentState`, `ApplicationGraph`, and `Hypotheses` to/from PostgreSQL database columns for total crash/restart resilience.
10. **Artifact Pipeline (`app/runtime/artifacts.py`)**:
    - Produces OpenAPI 3.1 specifications, Postman v2.1.0 collections, Pytest regression suites, and Markdown discovery reports backed by real observed network telemetry.
