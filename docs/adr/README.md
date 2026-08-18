# InsightAPI Architecture Decision Records (ADRs)

This directory documents the foundational architectural decisions made for the **InsightAPI Autonomous Agent Runtime** (Phases 0–10) in alignment with [.agents/AGENTS.md](file:///c:/Users/ashut/Devlopments/InsightAPI/.agents/AGENTS.md).

---

## ADR Index

1. [ADR-001: Agent Runtime Architecture](#adr-001-agent-runtime-architecture)
2. [ADR-002: AgentState Design & Working Memory](#adr-002-agentstate-design--working-memory)
3. [ADR-003: Application Graph World Model](#adr-003-application-graph-world-model)
4. [ADR-004: Observation & Event Bus Model](#adr-004-observation--event-bus-model)
5. [ADR-005: Playwright BrowserAdapter Abstraction](#adr-005-playwright-browseradapter-abstraction)
6. [ADR-006: Information-Gain Planner Architecture](#adr-006-information-gain-planner-architecture)
7. [ADR-007: Specialized Agent Boundaries & Delegation](#adr-007-specialized-agent-boundaries--delegation)
8. [ADR-008: Evidence & Confidence Classification Model](#adr-008-evidence--confidence-classification-model)
9. [ADR-009: Policy, SSRF Guardrails & Human Approval](#adr-009-policy-ssrf-guardrails--human-approval)
10. [ADR-010: Session Persistence & Resumability](#adr-010-session-persistence--resumability)
11. [ADR-011: Multi-Model Task Routing](#adr-011-multi-model-task-routing)
12. [ADR-012: Evaluation Strategy & Deterministic Verification](#adr-012-evaluation-strategy--deterministic-verification)

---

### ADR-001: Agent Runtime Architecture
- **Problem**: ReAct tool-calling loops were unstructured, lacked persistent state, and treated LLM guesses as immediate ground truth.
- **Decision**: Introduce a stateful runtime loop: `Goal → State → World Model → Hypotheses → Planner → Action → Observation → Evidence → Verification → Memory → Next Action`.
- **Alternatives**: Retain simple LLM `tool_calls` loop, migrate wholesale to LangGraph, or adopt generic AutoGPT-like agents.
- **Reason**: InsightAPI needs domain-specific API/web intelligence rather than generic LLM chatbot wrappers.
- **Consequences**: Deterministic governance over actions, zero chain-of-thought leakage, and clean separation between planning and computer-use actuation.
- **Future Migration Path**: Higher-level modules (SecurityAgent, API Drift Detector) sit directly on top of this runtime.

---

### ADR-002: AgentState Design & Working Memory
- **Problem**: Hot state held enormous raw HTML/network payloads, causing context bloating and high token costs.
- **Decision**: `AgentState` holds normalized metadata, visited URLs, action history capped at 50, and budget counters; large payloads are referenced by IDs.
- **Alternatives**: Store raw payloads directly in `AgentState` or rely purely on vector search.
- **Reason**: Keeps working memory lightweight and serializable for instantaneous checkpointing.
- **Consequences**: Fast serialization and zero risk of token exhaustion during state reflection.
- **Future Migration Path**: Seamless sync to Redis / Postgres via `AgentStateStore`.

---

### ADR-003: Application Graph World Model
- **Problem**: Discovery output was just a flat list of URL strings without behavioral context.
- **Decision**: Model discovery as an `ApplicationGraph` containing typed nodes (`Page`, `UIElement`, `Endpoint`, `Entity`) and relationships (`CONTAINS`, `TRIGGERS`, `CAUSES`, `DEPENDS_ON`, `RETURNS`).
- **Alternatives**: Flat list of endpoints or immediate Neo4j graph database migration.
- **Reason**: In-memory relational graph with JSON/JSONB serialization provides instant graph traversal without heavyweight database dependencies.
- **Consequences**: Discoveries reflect how applications actually communicate from UI actions to background network requests.
- **Future Migration Path**: Export to Graphviz, D3, or dedicated graph engines if user scale warrants.

---

### ADR-004: Observation & Event Bus Model
- **Problem**: Tools returned arbitrary raw dictionaries, making multi-agent communication brittle and tightly coupled.
- **Decision**: All tool execution produces normalized `Observation` objects and emits typed `AgentEvent` payloads over `AgentEventBus`.
- **Alternatives**: Direct agent-to-agent function calls or raw JSON pub/sub.
- **Reason**: Decouples UI streaming, telemetry tracking, and subagent collaboration onto a single event-driven bus.
- **Consequences**: Backward compatible with wire protocol via `EventBridge`.
- **Future Migration Path**: Attach Kafka/RabbitMQ adapters for distributed agent clusters.

---

### ADR-005: Playwright BrowserAdapter Abstraction
- **Problem**: Direct calls to Playwright were scattered across tools, making alternative browser backends impossible.
- **Decision**: Create `BrowserAdapter` ABC with `PlaywrightBrowserAdapter` implementing stealth scripts, shadow DOM piercing, AXTree extraction, and multi-protocol network interception.
- **Alternatives**: Replace Playwright with Puppeteer or direct CDP connections.
- **Reason**: Playwright is the battle-tested actuator; abstracting it preserves existing strengths while enabling remote cloud execution.
- **Consequences**: Tools interact strictly with `BrowserAdapter`.
- **Future Migration Path**: Implement `RemoteBrowserAdapter` or `BrowserlessAdapter` without touching agent logic.

---

### ADR-006: Information-Gain Planner Architecture
- **Problem**: LLMs frequently revisited known pages and repeatedly hit the same endpoints without discovering new surface area.
- **Decision**: `Supervisor` scores candidate actions using an explainable heuristic: `score = information_gain + goal_relevance + novelty + confidence_improvement - risk - cost - duplication`.
- **Alternatives**: Reinforcement learning or purely LLM-driven planning.
- **Reason**: Deterministic scoring guarantees bounded exploration and prevents wasteful loops.
- **Consequences**: Unexplored areas, dynamic parameters, and auth-protected routes receive priority.
- **Future Migration Path**: Configurable domain-specific scoring weights per investigation tier.

---

### ADR-007: Specialized Agent Boundaries & Delegation
- **Problem**: Monolithic agents attempted to handle browser clicks, HTTP headers, GraphQL parsing, and schema generation all at once.
- **Decision**: Segregate roles into `ExplorerAgent` (UI/DOM/forms), `NetworkAgent` (HTTP/HAR/GraphQL), and `VerificationAgent` (skeptical replay & auth checks) under `Supervisor` coordination.
- **Alternatives**: Single mega-agent or dozens of micro-agents.
- **Reason**: Clear single-responsibility boundaries prevent tool confusion and simplify unit testing.
- **Consequences**: Supervisor delegates bounded tasks with strict timeouts and tool whitelists.
- **Future Migration Path**: Add `SecurityAgent` and `DocGenAgent` following the exact same `BaseAgent` contract.

---

### ADR-008: Evidence & Confidence Classification Model
- **Problem**: Inferred parameters and speculative routes were presented as facts.
- **Decision**: Strict confidence hierarchy: `UNOBSERVED < INFERRED < WEAK < PROBABLE < TESTED < VERIFIED < STRONGLY_VERIFIED`.
- **Alternatives**: Binary True/False flag or floating-point LLM self-confidence.
- **Reason**: Proves discoveries through repeatable network evidence before marking endpoints as certified.
- **Consequences**: OpenAPI and Postman exports distinguish observed facts from inferences.
- **Future Migration Path**: Embed verification evidence hashes directly into OpenAPI `x-evidence` vendor extensions.

---

### ADR-009: Policy, SSRF Guardrails & Human Approval
- **Problem**: LLMs could theoretically execute destructive `DELETE` requests or pivot to internal cloud metadata IP addresses (`169.254.169.254`).
- **Decision**: `PolicyEngine` evaluates every action against allowed domains, blocks private/SSRF IP ranges, classifies risk (`READ_ONLY` to `DESTRUCTIVE`), and forces `APPROVAL_REQUIRED` on high-risk actions.
- **Alternatives**: Prompt-based safety guidelines.
- **Reason**: Deterministic code must always hold ultimate authority over execution permissions.
- **Consequences**: Safe autonomous exploration with zero SSRF risk.
- **Future Migration Path**: Role-based access control (RBAC) policies mapped to organizational teams.

---

### ADR-010: Session Persistence & Resumability
- **Problem**: Process crashes or container recycles caused total loss of exploratory progress.
- **Decision**: `AgentStateStore` provides serialization and restoration of `AgentState`, `ApplicationGraph`, and `Hypotheses`.
- **Alternatives**: In-memory-only state or heavy transactional database commits after every step.
- **Reason**: Allows long-running investigations to be paused, reviewed, and resumed seamlessly.
- **Consequences**: Zero loss of discovered graph topology upon reconnection.
- **Future Migration Path**: Pluggable Redis cache / PostgreSQL JSONB storage backends.

---

### ADR-011: Multi-Model Task Routing
- **Problem**: Running expensive reasoning models on simple deterministic tasks wasted budget and increased latency.
- **Decision**: Router routes tasks into tiers: `FAST` (cheap/fast extraction), `SMART` (reasoning/planning), and `VISION` (multimodal layout inspection).
- **Alternatives**: Single model provider across all tasks.
- **Reason**: Optimizes token budget while maintaining high analytical fidelity.
- **Consequences**: Provider-agnostic interface (Gemini, Claude, OpenAI, Local).
- **Future Migration Path**: Dynamic routing based on real-time latency and remaining budget.

---

### ADR-012: Evaluation Strategy & Deterministic Verification
- **Problem**: Testing against live public websites led to non-deterministic test failures and network flakiness.
- **Decision**: Build comprehensive unit and integration test fixtures covering SPA state, dynamic parameters, GraphQL, auth protection, and error recovery.
- **Alternatives**: End-to-end testing exclusively on external websites.
- **Reason**: Ensures deterministic CI/CD validation with 100% reproducible results.
- **Consequences**: 117 tests passing cleanly in <25 seconds.
- **Future Migration Path**: Synthetic target app Docker container for automated benchmarking.
