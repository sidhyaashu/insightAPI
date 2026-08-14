# InsightAPI AI — Full Codebase Analysis

## What You Are Building & Why

### The Core Problem You're Solving

> Modern web applications expose dozens or hundreds of internal API endpoints. Discovering and documenting them manually — via Browser DevTools → filter requests → copy payloads → write docs — is **tedious, error-prone, and doesn't scale**.

You are building a tool that **eliminates this manual process entirely** by deploying an autonomous AI agent that:

1. Opens a real browser (Playwright)
2. Clicks through the web app like a human
3. Silently intercepts all API traffic in the background
4. Uses AI to analyze, deduplicate, and understand those APIs
5. Auto-generates **production-ready documentation** (OpenAPI, Postman, Markdown) — zero human effort

---

## What InsightAPI AI Is

**InsightAPI AI** is an **Agentic Web API Intelligence Platform** — a tool that autonomously reverse-engineers the API surface of any web application and documents it.

### Target Audience
Developers, QA engineers, automation testers, technical writers, integration teams — anyone who needs to understand how a web app's frontend talks to its backend, **without reading source code**.

### Distribution
It ships as **three products in one codebase**:
| Mode | What it is |
|------|------------|
| **Python SDK** | `from insightapi import AgentEngine` — import into any Python script or CI/CD |
| **CLI Tool** | `insightapi crawl https://...` — run from terminal |
| **REST API** | `POST /api/v1/crawls/start` — call from any language/tool |

---

## Architecture: How It All Fits Together

```
User (CLI / SDK / REST call)
         │
         ▼
    AgentEngine.crawl()          ← sdk.py — the entry point
         │
    ┌────┴─────┐
    │          │
RobotsChecker  BrowserManager + NetworkObserver
(compliance)   (Playwright browser, network tap)
         │
         ▼
   LangGraph StateGraph          ← agents/graph.py — the brain
   ┌─────────────────────────────────────────────────┐
   │                                                 │
   │  PlannerNode ──► RiskEvaluatorNode              │
   │       ▲               │                        │
   │       │        ┌──────┴──────┐                 │
   │       │        ▼             ▼                 │
   │       └── ExecutorNode   (skip unsafe)         │
   │                │                               │
   │                ▼                               │
   │           [loop until max_pages]               │
   │                │                               │
   │                ▼                               │
   │          AnalyzerNode ──► END                  │
   └─────────────────────────────────────────────────┘
         │
         ▼
   Exporters (OpenAPI / Postman / Markdown)
```

---

## The Four Agent Nodes (LangGraph)

### 1. `PlannerNode` — The Navigator
**File:** [`planner.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/planner.py)

- Extracts the full interactive DOM snapshot (AXTree) — only buttons, inputs, links, selects — ignoring everything else
- Runs a **Priority Queue Frontier** (graph search) over candidate UI elements
- Scores each element by estimated API yield: search inputs (+15), form controls (+10), buttons (+8), links (+3)
- Prunes elements that are robots.txt-disallowed or in saturated route clusters
- Selects the highest-scoring unvisited action and sets it as `next_action`
- Detects when the frontier is empty → marks crawl complete

### 2. `RiskEvaluatorNode` — The Safety Guard
**File:** [`risk_evaluator.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/risk_evaluator.py)

Before any click happens, this evaluates whether it's safe. Two-tier approach:

- **Tier 1 (Fast Regex < 1ms):** Immediately blocks destructive keywords: `delete`, `pay`, `purchase`, `update password`, `revoke`, `grant admin` etc. Immediately allows navigation keywords: `next`, `filter`, `search`, `view`, `tab` etc.
- **Tier 2 (Context-Enriched):** For ambiguous labels like "Submit" or "Save" — inspects the parent form, surrounding section text, page title to determine if it's inside a dangerous form
- Results are cached per selector for efficiency

### 3. `ExecutorNode` — The Actor
**File:** [`executor.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/executor.py)

- Enforces per-domain rate limiting (default 500ms between actions)
- Detects and auto-dismisses cookie banners / overlays (Accept, Close, Got it)
- Executes Playwright actions: click, fill, select, hover, keyboard press
- Self-heals: falls back to `force=True` when elements are covered
- Injects context-aware dummy data into form fields (email → `user@example.com`, search → `test search`, date → `2026-01-01`)
- Detects **login walls** (password input + no session cookie → halt with `auth_required`)
- Detects **modal traps** (3 consecutive modal clicks with 0 new endpoints → force-close via Escape + DOM removal)
- Captures **popup/new-tab traffic** by attaching NetworkObserver to any spawned page before closing it
- Re-extracts fresh AXTree snapshot after each action

### 4. `AnalyzerNode` — The Schema Builder
**File:** [`analyzer.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/nodes/analyzer.py)

- Groups all raw captured observations by `(template_route, method, status_code)` key
- **Incrementally merges JSON schemas** across multiple observations of the same endpoint:
  - Identical schemas → kept as-is
  - `null` vs non-null → adds `nullable: true`
  - Type mismatch → wraps in `oneOf`
  - Object + Object → recursive property merge; fields absent in one side become optional
- Computes **confidence score** per endpoint: `min(0.99, base × stability + auth_bonus)`
  - More observations → higher base
  - Schema stability across observations → stability bonus
  - Auth header present → +0.05 bonus
- Stores up to 3 redacted example request/response pairs per endpoint

---

## The Browser Engine

### DOM Distiller
**File:** [`dom_distiller.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/browser/dom_distiller.py)

Instead of dumping 100k+ tokens of raw HTML to an LLM, this runs **JavaScript inside the browser** to extract only interactive elements:

```
a, button, input, select, textarea, [role="button/link/menuitem/..."], [onclick], [tabindex]
```

Key capabilities:
- **Shadow DOM piercing** — recursively processes all `shadowRoot` trees
- **Same-origin iframe piercing** — processes nested iframes from same domain
- **Virtualized scrolling** — performs up to 3 incremental scroll passes to reveal lazy-loaded content
- Extracts for each element: `tag`, `text`, `role`, `ariaLabel`, `placeholder`, `selector`, `form_context`, `parent_text`
- Filters out hidden/invisible elements (display:none, visibility:hidden, opacity:0)

### Network Observer
**File:** [`listener.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/network/listener.py)

Hooks into Playwright's network events and captures:
- REST API calls (XHR, fetch)
- GraphQL operations (parses `operationName` from POST body or GET query params, handles batch operations)
- WebSocket connections (captures handshake)
- Server-Sent Events (SSE)

Applies **redaction** before storing: strips `Authorization`, `Cookie`, `X-API-Key`, `X-CSRF-Token`, passwords, JWT tokens from both headers and response bodies.

Caps at **10 observations per route** — enough for schema merging, not wasteful.

### Network Filter
**File:** [`filter.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/network/filter.py)

Filters out:
- Static assets (`.js`, `.css`, images, fonts, `.wasm`, `.pdf`, `.zip`)
- 31 known telemetry/analytics domains (Google Analytics, Sentry, Mixpanel, Hotjar, Amplitude, Datadog, Intercom, etc.)
- Non-API content types

### URL Deduplicator
**File:** [`deduplicator.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/engine/network/deduplicator.py)

Normalizes `/api/users/101` and `/api/users/102` into `/api/users/{id}` by detecting:
- UUIDs → `{uuid}`
- MongoDB ObjectIDs (24-char hex) → `{id}`
- Stripe-style IDs (`cus_xxx`, `sub_xxx`) → `{id}`
- Pure numeric IDs → `{id}`
- Hex hashes (32–64 chars) → `{hash}`
- ISO dates → `{date}`
- NanoIDs (16–32 char alphanumeric) → `{id}`
- Query params → all values replaced with `{val}`

**DOMStateHasher:** Hashes `(normalized_URL + AXTree structural fingerprint)` to detect when the same URL has different UI states (SPA modal/tab switches). Sanitizes volatile numbers to prevent hash traps.

**RouteClusterTracker:** Prunes crawl when the last 3 visits to a template route all produced identical DOM hashes (nothing new to discover).

---

## Compliance & Safety

### `RobotsChecker`
**File:** [`compliance.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/core/compliance.py)

- Fetches and parses `robots.txt` from the target domain at crawl start
- Checks every candidate link URL before queuing in the frontier
- Defaults to `allow_all` if `robots.txt` is unreachable (graceful degradation)

### `DomainRateLimiter`
- Enforces minimum 500ms delay between requests to the same domain
- Configurable via `--rate-limit` CLI flag or `rate_limit_ms` SDK argument

### SSRF Protection
**File:** [`crawls.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/api/v1/endpoints/crawls.py)

The REST API endpoint validates all target URLs against SSRF attacks: blocks `localhost`, `127.x.x.x`, private RFC1918 ranges (`10.x`, `172.16.x`, `192.168.x`), and AWS metadata endpoints (`169.254.169.254`).

---

## Exporters

Three exporters convert the analyzed endpoint data:

| Exporter | Output | Notes |
|----------|--------|-------|
| `OpenAPIExporter` | OpenAPI 3.0.3 JSON | Includes `x-confidence` + `x-example-count` vendor extensions; embeds real captured examples in `examples` blocks |
| `PostmanExporter` | Postman Collection v2.1 JSON | Ready to import and replay |
| `MarkdownExporter` | Human-readable `.md` | Good for docs sites |

The OpenAPI spec is particularly rich — it includes actual captured (and redacted) request/response payloads as `examples`, so developers can immediately see what the API actually returned.

---

## CrawlState — The Shared Memory

**File:** [`state.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/backend/app/agents/state.py)

The LangGraph state dict that flows between all nodes:

```python
{
  "target_url": str,                  # where we started
  "current_url": str,                 # where we are now
  "visited_urls": [...],              # deduplication
  "visited_state_hashes": [...],      # SPA state deduplication
  "visited_selectors": [...],         # don't click same thing twice
  "interactive_elements": [...],      # current page AXTree
  "captured_endpoints": [...],        # all API observations so far
  "next_action": {...},               # what to do next
  "is_safe_action": bool,             # risk evaluator result
  "frontier": [...],                  # priority queue of pending actions
  "explored_count": int,              # pages explored so far
  "max_pages": int,                   # stop condition
  "is_complete": bool,                # termination flag
  "modal_action_count": int,          # modal trap counter
  "deprioritized_modal_selectors": [...],  # selectors to avoid
  "network_observer": <object>,       # live reference to observer
  "page_ref": <object>,               # live Playwright page reference
  "rate_limit_ms": int,               # delay between actions
}
```

---

## What's Built vs. What's Planned

### ✅ Fully Built & Working (v1.0.0 Release)
- **Production Next.js Web UI Client**: Built with Next.js 16, TypeScript, Tailwind CSS, shadcn/ui, and Redux Toolkit. Features Claude-inspired warm charcoal aesthetic, borderless layout, and zero mock fallbacks.
- **Authentication & Identity Unification**: Email/Password authentication, verification emails, password resets, Google OAuth, GitHub OAuth, and automatic Identity Account Unification.
- **Security & Token Rotation**: Memory-only access tokens + HttpOnly/Secure/SameSite refresh token rotation with single-use reuse detection.
- **Interactive Workspace Dashboard (`/dashboard`)**: Crawl launcher with tier-based max pages budget, goal focus, and real-time recent crawl history table.
- **Crawl Live Stream (`/crawls/[id]`)**: REST hydration on mount + real-time WebSocket log streaming with manual reconnect controls.
- **Crawl History Manager (`/crawls`)**: Table pagination (`limit` & `offset`), row deletion (`DELETE /crawls/{id}`) with confirm dialog, and status filtering.
- **Multi-Format Report Export (`/reports/[id]`)**: OpenAPI 3.0.3/3.1, Postman v2.1, and Markdown exports with server-side tier quota gating.
- **API Key Management (`/settings`)**: SHA-256 hashed API key issuance, show-once key modal, 5-key max quota, and key revocation.
- **Stripe Billing & Customer Portal (`/billing`)**: Dynamic plan pricing, Stripe Checkout for STARTER/PRO/ENTERPRISE tiers, and Stripe Customer Portal integration.
- **LangGraph Agent Loop**: PlannerNode → RiskEvaluatorNode → ExecutorNode → ReflectionNode → AnalyzerNode state machine.
- **LLM-Powered Planner**: Coverage gap reasoning, goal-directed selection, anti-loop stagnation guidance.
- **Smart Form Injection**: Contextually-aware form field value generation via `LLMFormInjector`.
- **DOM Distillation**: Accessibility Tree (AXTree) extraction, Shadow DOM piercing, iframe piercing, virtualized container scroll support.
- **Network Observer & Deduplication**: REST XHR/fetch, GraphQL operation parsing, WebSocket handshakes, SSE, dynamic route parameterization (`/users/{id}`), DOM state hashing, route cluster pruning.
- **Safety & Compliance**: Two-tier risk evaluator (regex fast-path + context fallback), robots.txt checking, per-domain rate limiting, SSRF protection, secret redaction.
- **Distribution Interfaces**: Python SDK (`AgentEngine`), Typer CLI (`insightapi`), FastAPI REST API.

### 🚧 Future Roadmap (Post-v1.0.0)
- **Automated API Drift Detection**: Compare OpenAPI specs across releases to highlight breaking changes.
- **Vision Set-of-Mark (SoM) Fallback Classifier**: Screenshot coordinate overlay for Canvas/WebGL controls.
- **GitHub Action & CI/CD Pipeline Plugin**: Automated PR crawl checks in CI pipelines.
- **Self-Healing Test Suite Generator**: Auto-generate Playwright test scripts from recorded crawl traces.


---

## Summary: The One-Line Pitch

**You are building the "browser DevTools on autopilot" — point it at any web app and get a complete, structured, ready-to-use API specification automatically.**

