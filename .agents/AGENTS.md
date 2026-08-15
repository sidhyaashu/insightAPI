# InsightAPI AI — Workspace Rules & Agent Guidelines

> This file (`.agents/AGENTS.md`) defines workspace-scoped guidelines and architectural constraints for AI coding agents working on **InsightAPI AI**. All agents working on this codebase MUST follow these instructions.

---

## 1. Project Context & Stack

* **Project Goal**: InsightAPI AI is an Agentic Web API Intelligence Platform and Python SDK that autonomously explores web applications, observes network traffic, analyzes API behavior, infers endpoint relationships, and generates structured OpenAPI/Postman documentation.
* **Distribution Model**: **Python SDK + CLI Engine + Standalone REST API**. Embeddable in CI/CD pipelines or Python scripts.
* **Technology Stack**:
  * **Core Engine, SDK & CLI**: Python (Typer + Rich + Asyncio)
  * **Backend & REST API**: FastAPI (Python)
  * **Agent Framework**: LangGraph + LangChain
  * **Browser Automation**: Playwright (Async Python)
  * **AI Models**: OpenAI GPT-4o / GPT-4o-mini (or Ollama/Local OpenAI-compatible endpoints)
  * **Storage**: PostgreSQL + pgvector + Redis (or optional in-memory storage for lightweight SDK runs)
  * **Frontend (Phase 5 Deferred)**: Next.js 14 + TypeScript + shadcn/ui + React Flow + Tailwind CSS

---

## 2. Core Architectural Guidelines & Constraints

### A. Python SDK Architecture
* Keep the core engine decoupled from web-server specifics so users can import `insightapi` directly as a Python library:
  ```python
  from insightapi import AgentEngine
  
  engine = AgentEngine()
  results = await engine.crawl("https://example.com")
  ```
* Support zero-dependency lightweight mode (in-memory session state when running in CI/CD without Postgres).

### B. Autonomous UI Exploration
* **DO NOT** pass raw, un-distilled HTML (100k+ tokens) or full page screenshots to LLMs for routine navigation.
* **ALWAYS** extract an **Interactive DOM Snapshot (Accessibility Tree)** containing only interactive and semantic controls (`a`, `button`, `input`, `select`, `textarea`, `[role]`, `[onclick]`).
* **LLM Vision Fallback**: Use Vision LLMs with Set-of-Mark screenshots ONLY when interactive DOM extraction fails or when interacting with Canvas/complex UIs.

### C. Action Safety & Two-Tier Risk Classification
* **DO NOT** click or submit elements blindly on arbitrary URLs.
* **ALWAYS** evaluate element target context through the **Two-Tier Risk Classifier** before execution:
  * **Tier 1 (Fast Guardrails)**: Sub-millisecond regex pre-filtering for obvious `SAFE` navigation/view/filter targets vs `UNSAFE` destructive actions (`delete`, `pay`, `purchase`, `update password`, `cancel subscription`).
  * **Tier 2 (Context Enrichment)**: Ambiguous elements (`Submit`, `Save`) evaluate parent form labels, surrounding text, and page titles.
* Skip **UNSAFE** actions automatically, log them in the crawl report, and proceed to the next item without stopping execution.

### D. Dynamic Runtime Execution & Reliability
* **Structured Action Interpreter**: Execute browser UI actions via `DynamicRuntimeExecutor` using Playwright action handlers.
* **Overlay Interstitial Auto-Dismissal**: Automatically detect and clear blocking cookie banners, dialog backdrops, and modals (`Accept`, `Close`).
* **Form Dummy Value Injection**: Contextually populate search fields, emails, dates, quantities, and input text prior to interaction.

### E. Network Observer, State Hashing & Compliance
* Ignore static web assets (`.js`, `.css`, `.png`, `.jpg`, `.svg`, `.woff2`) and telemetry domains (`*.google-analytics.com`, `*.sentry.io`).
* Deduplicate endpoint parameters: Normalize dynamic URL paths (`/users/101`, `/users/102`) into template routes (`/users/{id}`).
* Parse GraphQL payloads: Treat distinct `operationName` values (single, batch, query params) as separate logical endpoints.
* **DOM State Graph Hashing**: Hash `(normalized_URL, AXTree_structural_fingerprint)` to distinguish SPA modal/tab states at the same URL and prune saturated template route clusters.
* **Shadow DOM & Virtualized Scrolling**: Recursively pierce `shadowRoot` trees and perform incremental scroll passes over virtualized list containers (`react-window`, `TanStack Virtual`).
* **Legal & Compliance Guardrails**: Parse and respect target site `robots.txt` disallow rules and enforce per-domain minimum request delay spacing (default: 500ms).
### F. Frontend Markdown Rendering & UI Architecture
* **Modular Renderer**: Always use the modular `<MarkdownRenderer />` component for rendering AI and markdown content.
* **Specialized Blocks**: Support syntax-highlighted code blocks (Prism for 30+ languages), ````http```` API endpoint blocks with method badges, KaTeX math expressions (`$inline$` and `$$block$$`), dynamic theme-aware Mermaid diagrams, GitHub callout alerts (`[!NOTE]`, `[!TIP]`, `[!WARNING]`, `[!IMPORTANT]`, `[!CAUTION]`), and responsive tables with internal horizontal scrolling.
* **Streaming Resilience**: Always pass streaming tokens through `repairStreamingMarkdown` to automatically repair unclosed code fences and math blocks during LLM token streaming.
* **Layout Design**: Never enclose assistant message text in rigid, boxed card borders or fixed widths; keep assistant message layouts full-width, clean, and transparent matching modern AI assistants.

### G. Security & WebSocket Authentication
* **HttpOnly Cookies**: Pass JWT access tokens via `HttpOnly; SameSite=Lax; Path=/` cookies instead of exposing tokens in URL query strings (`?token=...`).
* **Log Redaction**: Ensure NGINX access log mapping redacts any query parameters containing sensitive tokens (`token=[REDACTED]`).
* **URL Sanitization**: Always validate markdown link/image URLs with `isSafeUrl()` to block dangerous protocols (`javascript:`, `vbscript:`, unsafe `data:` URLs).

### H. Active Security Testing, Isolated Sandboxing & Human Approval Guards
* **Sandbox Egress & Runtime Isolation**:
  * All active vulnerability test probes and mutated requests MUST execute through `SandboxExecutor` in `app/engine/sandbox/executor.py` with hard resource limits (10s default timeout, 512KB response caps) and strict egress verification against authorized target domains. Never execute active test probes in the shared passive crawler context.
* **Dual-Requirement Domain Verification Gate**:
  * Security testing (destructive or not) is strictly prohibited unless the target domain is BOTH verified (`is_verified == True`) AND has `active_testing_opt_in == True` explicitly enabled by the user. Hard-block with `403 Forbidden` otherwise.
* **Conservative False-Negative Promotion Safeguards**:
  * `is_destructive=True` test cases can NEVER be auto-promoted to `learned` regardless of repetitions.
  * Zero-token cache replay for non-destructive patterns requires `occurrences >= 20` AND `distinct_target_count >= 15` across distinct domains AND `confidence >= 0.80`.
  * Destructive tests ALWAYS generate a `SecurityApproval` record and require human authorization via `POST /api/v1/security-patterns/{approval_id}/approve-run` before execution.
* **Granular LLM Cost Persistence**:
  * Every LLM call and cache hit across all nodes (Planner, Analyzer, Security Reasoner) must be recorded in the `llm_usage` ledger.

---

## 3. Maintenance of Guidelines & Feature Tracking

* **Mandatory Feature Tracking**: Whenever a new feature, endpoint, or architectural component is implemented:
  1. Update `V1_IMPLEMENTATION.md` to document the new capability, subcomponents, and endpoints.
  2. Update this `.agents/AGENTS.md` file whenever new edge cases, anti-patterns, or architectural guidelines are established during development.

