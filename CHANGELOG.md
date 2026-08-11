# Changelog — InsightAPI AI

All notable changes to **InsightAPI AI** will be documented in this file.

---

## [1.0.0] — 2026-08-10 — Official v1.0.0 Production Release 🎉

### Summary
The initial major release of **InsightAPI AI** — an Agentic Web API Intelligence Platform and Open-Source Python SDK that autonomously explores web applications, observes network traffic, analyzes API behavior, infers endpoint relationships, and generates production-ready OpenAPI, Postman, and Markdown documentation.

### Features Included in v1.0.0

#### 🤖 AI & Agent Engine
- **LangGraph StateGraph Workflow**: Autonomous graph state machine coordinating `PlannerNode`, `RiskEvaluatorNode`, `ExecutorNode`, `ReflectionNode`, and `AnalyzerNode`.
- **LLM-Powered Planner**: Evaluates current page elements against discovered endpoint categories to select high-yield actions that maximize new API discovery.
- **Goal-Directed Crawling**: Threaded `goal` parameter (`--goal "Find payment APIs"`) to bias agent exploration toward target objectives.
- **Periodic Reflection & Self-Critique**: Mid-crawl reflection review every `N` pages using `ModelTier.SMART` (`gpt-4o`/`gpt-5.4`) to identify blind spots and update strategy.
- **GPT-4o Vision Fallback**: Screenshot-based visual UI control extraction when accessible AXTree elements are sparse (Canvas / obfuscated SPAs).
- **Smart LLM Form Injection**: Generates contextually-aware form inputs in a single batched call per form.

#### ⚡ Browser Automation & Network Engine
- **DOM Distillation**: JS-evaluated interactive accessibility snapshotting with Shadow DOM piercing, same-origin iframe piercing, and virtualized container scrolling.
- **Network Traffic Observer**: Intercepts REST XHR/fetch, GraphQL operations (parses `operationName`), WebSockets, and Server-Sent Events.
- **URL Parameterization & Deduplication**: Normalizes dynamic paths (`/users/101`, `/users/102`) into route templates (`/users/{id}`) supporting UUIDs, ObjectIDs, Stripe IDs, hex hashes, and ISO dates.
- **Network Loading & Stability Tracker (`PageNetworkStabilizer`)**: Enforces 400ms quiet window and monitors UI loading indicators (`.spinner`, `.loading`, `[aria-busy]`).
- **Loop Breaker & Stagnation Detector (`StagnationDetector`)**: Detects zero-yield streaks and state oscillation (`State A <-> State B`), forcing un-stuck recovery procedures.

#### 💰 Token Budget & Cost Management
- **`ModelRouter`**: Task-complexity model selection (`FAST` `gpt-4o-mini`, `SMART` `gpt-4o`, `VISION` `gpt-4o-mini`).
- **`LLMCostManager`**: Session token budget enforcement, decision caching, and UI-facing cost metrics (`tokens_used`, `estimated_cost_usd`).

#### 🔀 Scale & Cross-Session Memory
- **Parallel Multi-Agent Crawling (`CrawlCoordinator`)**: Decomposes target application into section goals and runs concurrent browser sub-agents (`--parallel --agents N`).
- **Vector Store Memory (`EndpointVectorStore`)**: Cross-session memory and natural language semantic endpoint search (`POST /api/v1/search`).

#### 📄 Multi-Format Exporters
- **OpenAPI 3.0.3 Exporter**: Generates complete OpenAPI specifications with captured example request/response payloads, confidence scores, and AI descriptions/tags.
- **Postman Collection v2.1 Exporter**: Export collection ready for replay.
- **Markdown Docs Exporter**: Human-readable documentation formatted with cURL examples.

#### 🛡️ Compliance & Safety
- **Two-Tier Risk Classifier**: Fast sub-millisecond regex pre-filtering (`SAFE` vs `UNSAFE` destructive keywords) with context enrichment fallback.
- **Robots.txt & Rate Limiting**: Robots.txt disallow rule checking with `--force` override and per-domain request delay spacing (default: 500ms).
- **SSRF Protection**: REST API target URL validation blocking localhost, RFC1918 private IP ranges, and cloud metadata endpoints.
- **Secret Redaction**: Strips tokens, cookies, JWTs, and passwords from all captured headers and body payloads.

#### 📦 Distribution Interfaces
- **Python SDK**: `from insightapi import AgentEngine, CrawlResult`
- **CLI Engine**: `insightapi crawl`, `insightapi export`, `insightapi list-endpoints`, `insightapi login`
- **REST API**: FastAPI application with `/api/v1/crawls`, `/api/v1/reports`, `/api/v1/search`
