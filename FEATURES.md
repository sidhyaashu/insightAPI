# InsightAPI AI — Feature Directory & Capabilities Matrix

This document is the master directory of all features, capabilities, and subsystems built into **InsightAPI AI** (v1.0.0+).

---

## 🤖 1. Core AI Agent Engine (LangGraph Workflow)

| Feature | Module | Description |
| :--- | :--- | :--- |
| **LangGraph State Machine** | [`app/agents/graph.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/graph.py) | Autonomous execution loop coordinating `Planner` → `RiskEvaluator` → `Executor` → `Reflection` → `Analyzer`. |
| **LLM-Powered Planner** | [`app/agents/nodes/planner.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/planner.py) | Evaluates DOM candidates against discovered API categories using tiered model reasoning (`FAST`/`SMART`). |
| **Goal-Directed Crawling** | [`app/sdk.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/sdk.py) | `goal` parameter (`--goal "Find payment APIs"`) to bias exploration toward target objectives. |
| **Periodic Reflection** | [`app/agents/nodes/reflection.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/reflection.py) | Self-critique review every `N` pages using `ModelTier.SMART` (`gpt-4o`/`gpt-5.4`) to identify blind spots and update strategy. |
| **GPT-4o Vision Fallback** | [`app/engine/browser/vision_fallback.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/browser/vision_fallback.py) | Screenshot-based visual UI control extraction when accessible AXTree elements are sparse (< threshold). |
| **Smart Form Field Injector** | [`app/engine/executor/dynamic_executor.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/executor/dynamic_executor.py) | Contextually generates plausible form input values in a single batched call per form (`LLMFormInjector`). |
| **Batched Semantic Summaries** | [`app/agents/nodes/analyzer.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/analyzer.py) | Single batched LLM call enriches endpoints with `ai_summary`, `ai_tags`, and `ai_endpoint_category`. |

---

## ⚡ 2. Browser Automation & Network Engine

| Feature | Module | Description |
| :--- | :--- | :--- |
| **DOM Distillation** | [`app/engine/browser/dom_distiller.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/browser/dom_distiller.py) | Accessibility snapshotting piercing Shadow DOMs, same-origin IFrames, and virtualized scroll containers. |
| **Network Traffic Observer** | [`app/engine/network/listener.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/network/listener.py) | Intercepts REST XHR/fetch, GraphQL operations (`operationName` parsing), WebSockets, and SSE. |
| **URL Path Parameterization** | [`app/engine/network/deduplicator.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/network/deduplicator.py) | Parameterizes dynamic routes (`/users/{id}`) supporting UUIDs, Mongo ObjectIDs, Stripe IDs, hex hashes, and ISO dates. |
| **Page Network Stabilizer** | [`app/engine/browser/stabilizer.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/browser/stabilizer.py) | Enforces 400ms quiet window for in-flight requests and waits for UI spinners (`.spinner`, `.loading`, `[aria-busy]`). |
| **Stagnation Detector (Loop Breaker)** | [`app/engine/browser/stagnation_detector.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/browser/stagnation_detector.py) | Detects zero-yield streaks and state oscillation (`State A <-> State B`), triggering force un-stuck recovery. |
| **Modal & Popup Handling** | [`app/agents/nodes/executor.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/executor.py) | Detects modal traps and handles target="_blank" popups gracefully without stranding focus. |
| **Login Wall Detection** | [`app/agents/nodes/executor.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/executor.py) | Identifies unauthenticated password gates and halts crawl cleanly with `auth_required`. |

---

## 💰 3. Scale, Cost & Memory Subsystems

| Feature | Module | Description |
| :--- | :--- | :--- |
| **Parallel Multi-Agent Crawling** | [`app/agents/coordinator.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/coordinator.py) | Decomposes target application into section goals and runs concurrent browser sub-agents (`--parallel --agents N`). |
| **Vector Store Memory & Search** | [`app/services/vector_store.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/services/vector_store.py) | Cross-session memory and natural language semantic endpoint search (`POST /api/v1/search`). |
| **Token Cost Manager & Router** | [`app/agents/nodes/llm_client.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/llm_client.py) | Model tiering (`FAST`, `SMART`, `VISION`), session token budget caps, decision caching, and per-crawl USD spend metrics. |

---

## 🛡️ 4. Safety, Compliance & Exporters

| Feature | Module | Description |
| :--- | :--- | :--- |
| **Two-Tier Risk Classifier** | [`app/agents/nodes/risk_evaluator.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/risk_evaluator.py) | Fast sub-millisecond regex pre-filtering (`SAFE` vs `UNSAFE`) with context enrichment fallback. |
| **Robots.txt & Rate Limiting** | [`app/core/compliance.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/core/compliance.py) | Compliance checking with `--force` override and per-domain request delay spacing (default: 500ms). |
| **SSRF & Secret Protection** | [`app/engine/network/filter.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/network/filter.py) | Validates target URLs against SSRF and redacts auth tokens, cookies, JWTs, and passwords from payloads. |
| **OpenAPI 3.0.3 Exporter** | [`app/services/openapi_exporter.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/services/openapi_exporter.py) | Exports OpenAPI spec with captured example request/response payloads, confidence scores, and AI descriptions/tags. |
| **Postman Collection Exporter** | [`app/services/postman_exporter.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/services/postman_exporter.py) | Export Postman v2.1 collection ready for API testing and replay. |
| **Markdown Exporter** | [`app/services/markdown_exporter.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/services/markdown_exporter.py) | Human-readable documentation formatted with cURL request examples. |

---

## 📦 5. Distribution & Operations

| Feature | Module | Description |
| :--- | :--- | :--- |
| **Python SDK** | [`app/sdk.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/sdk.py) | Embeddable library: `from insightapi import AgentEngine`. |
| **CLI Engine** | [`app/cli/commands/crawl.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/cli/commands/crawl.py) | `insightapi crawl`, `insightapi export`, `insightapi list-endpoints`, `insightapi login`. |
| **FastAPI REST API** | [`app/main.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/main.py) | REST API endpoints for `/crawls`, `/reports`, `/search`, `/health`, and `/fuzz`. |
| **Container & CI/CD** | [`Dockerfile`](file:///c:/Users/ashut/Devlopments/InsightAPI/Dockerfile) | Production Dockerfile, docker-compose, and GitHub Actions CI/CD workflows (`ci.yml`, `publish.yml`). |

---

## 🧩 6. Third-Party Integrations & Extensions

| Integration | Module / Package | Capability |
| :--- | :--- | :--- |
| **Anti-Bot Stealth** | `playwright-stealth` & `fake-useragent` | Automatic stealth overrides & dynamic UA rotation to bypass Cloudflare / Akamai anti-bot checks. |
| **Local Vector Search** | `chromadb` | Embedded local vector database indexing endpoints for `POST /api/v1/search` without PostgreSQL. |
| **Automated API Fuzzer** | `schemathesis` & [`app/services/fuzzer.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/services/fuzzer.py) | Property-based schema probing against captured specs (`POST /api/v1/reports/{id}/fuzz`). |
| **Protocol Proxy Support** | `mitmproxy` & `PROXY_URL` | Routes Playwright browser traffic through upstream proxy servers (gRPC, HTTP/2 multiplexing). |
| **Chrome Extension Loader** | `CHROME_EXTENSION_PATHS` | Loads custom unpacked Chrome extensions (DevTools, Wappalyzer, Auth extensions) into Chromium context. |

