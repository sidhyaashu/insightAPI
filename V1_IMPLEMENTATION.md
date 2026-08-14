# InsightAPI AI — v1 Implementation Specification & Tracking Document

> **Document Status**: Production Complete & Verified  
> **Release Version**: v1.0.0  
> **Architecture**: Distributed Multi-Service Architecture (Next.js BFF + API Gateway + Core Service + Agent Service + NGINX + PostgreSQL/pgvector + Redis)

---

## 🏛️ System Architecture Overview

```
                                      ┌────────────────────────┐
                                      │   NGINX Reverse Proxy   │ (Port 80 / Ngrok Tunnel)
                                      └───────────┬────────────┘
                            ┌─────────────────────┼─────────────────────┐
                            ▼                     ▼                     ▼
                 ┌─────────────────────┐┌──────────────────┐┌──────────────────────┐
                 │ Next.js Client / UI ││   API Gateway    ││ WebSocket Proxy (/ws)│
                 └─────────────────────┘└─────────┬────────┘└──────────┬───────────┘
                                                  │                    │
                                    ┌─────────────┴──────┐             │
                                    ▼                    ▼             ▼
                          ┌──────────────────┐  ┌──────────────────────────────────┐
                          │   Core Service   │  │          Agent Service           │
                          │ (Auth & Stripe)  │  │ (AXTree, Crawl, LangGraph, LLM)  │
                          └────────┬─────────┘  └──────────────────┬───────────────┘
                                   │                               │
                                   └──────────────┬────────────────┘
                                                  ▼
                                     ┌─────────────────────────┐
                                     │ PostgreSQL + Redis Hub  │
                                     └─────────────────────────┘
```

---

## 📋 Comprehensive v1 Implementation Matrix

### 🔐 1. Authentication & Security Engine

* **Multi-Method Identity System**:
  * **Email & Password**: Registration (`POST /api/auth/register`), verification email delivery via Gmail SMTP (`GET /api/auth/verify-email`), rate-limited verification resend (`POST /api/auth/resend-verification`), login (`POST /api/auth/login`), password reset request (`POST /api/auth/forgot-password`), and password reset execution (`POST /api/auth/reset-password`).
  * **OAuth 2.0 Providers**: Native GitHub OAuth (`GET /api/auth/github/login`) and Google OAuth 2.0 (`GET /api/auth/google/login`).
  * **Identity Account Unification**: Seamlessly unifies user records across Email, Google, and GitHub logins under a single verified UUID account without creating duplicate accounts or losing subscription entitlements.
* **Dual-Cookie HttpOnly Security Model**:
  * **Access Token**: Short-lived JWT (15-minute lifespan) stored in an `HttpOnly; Secure; SameSite=Lax; Path=/` cookie, automatically attached to both REST API and WebSocket upgrade handshakes without exposing tokens in URL query strings.
  * **Refresh Token**: Long-lived single-use token (7-day lifespan) stored in an `HttpOnly; Secure; SameSite=Lax; Path=/api/auth/refresh` cookie.
  * **Automated Single-Use Token Rotation**: Rotating refresh tokens on every refresh call. Detects token reuse attempts and instantly invalidates all active sessions for that user.
  * **Silent Session Bootstrap**: `AuthProvider` automatically restores user state and permissions on application load via the HttpOnly cookie.

---

### 🤖 2. Autonomous Web UI Exploration Engine

* **Interactive AXTree DOM Distillation**:
  * Scans and distills the page Accessibility Tree to extract only semantic, interactive controls (`a`, `button`, `input`, `select`, `textarea`, `[role]`, `[onclick]`).
  * Compresses 100k+ tokens of raw HTML down to ~500 clean tokens, dramatically reducing LLM latency and cost.
* **Two-Tier Action Safety Guardrails**:
  * **Tier 1 (Sub-millisecond Regex Guardrails)**: Pre-filters obviously safe actions (`view`, `filter`, `navigate`, `expand`) from destructive operations (`delete`, `pay`, `purchase`, `update password`, `cancel subscription`).
  * **Tier 2 (Contextual Risk Evaluation)**: Evaluates surrounding form labels, parent headers, and page titles for ambiguous buttons (e.g. `Submit`, `Save`). Destructive actions are automatically skipped and noted in the report without halting execution.
* **Dynamic Runtime Execution & Reliability**:
  * **Form Value Injection**: Automatically injects realistic context-aware test data into search bars, emails, numbers, and date pickers prior to form submission.
  * **Overlay Interstitial Auto-Dismissal**: Automatically detects and clicks dismiss/accept controls on blocking cookie banners, backdrop overlays, and interstitial dialogs.
* **Stealth & Anti-Detection**:
  * Spoofs WebGL vendor and renderer strings (`Intel Inc.`), patches the Permissions API, and overrides hardware concurrency metrics to avoid headless browser detection.

---

### 🛰️ 3. Network Observer & Endpoint Intelligence

* **Telemetry & Noise Filtering**:
  * Automatically filters out static assets (`.js`, `.css`, `.png`, `.jpg`, `.svg`, `.woff2`) and tracking/analytics domains (`google-analytics.com`, `sentry.io`).
* **Dynamic URL Parameter Normalization**:
  * Uses algorithmic path cluster analysis to normalize dynamic URL parameters (`/users/101`, `/users/102`) into OpenAPI template routes (`/users/{id}`).
* **GraphQL Payload Decomposition**:
  * Parses distinct GraphQL `operationName` queries, mutations, and batch queries into separate, documented endpoints.
* **DOM State Graph Structural Hashing**:
  * Generates hashes of `(normalized_URL, AXTree_structural_fingerprint)` to distinguish SPA modal and tab states at identical URLs.
* **OpenAPI 3.1.0 & Postman 2.1 Specification Generation**:
  * Merges multi-observation payloads into strongly typed OpenAPI 3.1.0 schemas (JSON/YAML) and Postman 2.1 collections ready for import into Postman or Newman CI/CD pipelines.

---

### 💬 4. SaaS AI Chatbot & Production Markdown Rendering System

* **Modular `<MarkdownRenderer />` Component Architecture**:
  * **`MarkdownCode` & `InlineCode`**: Full Prism syntax highlighting for 30+ languages (`typescript`, `javascript`, `python`, `go`, `rust`, `bash`, `sql`, `json`, `yaml`, `diff`, etc.), line-wrapping toggle, and accessible copy button with "Copied!" feedback state.
  * **`MarkdownHttpBlock`**: Specialized API endpoint presenter with colored method badges (`GET` in blue, `POST` in emerald, `PUT` in amber, `PATCH` in purple, `DELETE` in rose), "Copy URL", and structured headers/body preview.
  * **`MarkdownTable`**: Responsive horizontal scroll wrapper with zebra striping, borders, and support for code/links inside cells.
  * **`MarkdownMath`**: KaTeX LaTeX math support for inline `$E=mc^2$` and block `$$...$$` with graceful error fallback.
  * **`MarkdownMermaid`**: Theme-aware dynamic diagram renderer with Preview/Source tabs and error boundaries.
  * **`MarkdownCallout`**: GitHub alerts (`[!NOTE]`, `[!TIP]`, `[!WARNING]`, `[!IMPORTANT]`, `[!CAUTION]`) and standard callouts.
  * **`MarkdownList` & `MarkdownCheckbox`**: Nested lists and accessible checkbox task lists.
  * **`MarkdownLink` & `MarkdownImage`**: XSS validation (blocking `javascript:` URLs), external link icons, and image loading skeletons/fallbacks.
* **Streaming & Malformed Markdown Resilience**:
  * Automatic streaming repair closes unterminated code fences and LaTeX delimiters during active LLM token streaming.
  * Pulsing streaming indicator cursor.
* **Tier-Based Daily Quotas (Redis Counters)**:
  * **Free**: 15 messages/day
  * **Starter**: 50 messages/day
  * **Pro**: 250 messages/day
  * **Enterprise / Admin**: Unlimited messages
  * Live visual quota meter with dynamic alert banners and upgrade shortcuts when limits are reached.
* **Chat Session Management**:
  * Multi-session history drawer, auto-titling from initial prompt, session deletion, and one-click Markdown file export (`.md`).
* **LLM Markdown Optimization**:
  * `SYSTEM_PROMPT` in `chat_service.py` instructs InsightBot to utilize specialized ````http```` blocks, ````mermaid```` diagrams, GitHub alerts, and structured tables.

---

### 💳 5. Stripe Billing & Subscription Management

* **Stripe Checkout Integration**:
  * Dynamically creates checkout sessions (`POST /api/v1/payments/checkout`) for Starter, Pro, and Enterprise subscription tiers.
* **Webhook Tier Synchronization**:
  * Robust webhook listener (`/api/v1/payments/webhook`) handling `checkout.session.completed`, `customer.subscription.updated`, and `customer.subscription.deleted`, automatically keeping PostgreSQL and Redis tiers synchronized in real time.
* **Self-Service Customer Portal**:
  * Redirects users to Stripe Customer Portal (`POST /api/v1/payments/portal`) for invoice downloads, credit card updates, and subscription cancellations.
  * Displays active period-end cancellation notices (`cancel_at_period_end`).

---

### 🌐 6. Infrastructure, Reverse Proxy & Networking

* **Unified NGINX Reverse Proxy**:
  * Routes all inbound traffic through a single entrypoint:
    * `/` ➔ Next.js Client / BFF (`client:3000`)
    * `/api/*` ➔ API Gateway (`gateway:8080`)
    * `/ws/*` ➔ Gateway WebSocket Proxy (`gateway:8080`) ➔ Agent Service (`agent-service:8002`)
* **Ngrok Public Tunnel Container**:
  * Out-of-the-box HTTPS tunneling container for external webhook testing and remote API access.
* **Access Log Token Redaction**:
  * Regex map (`$sanitized_request_uri`) redacts sensitive query parameters (`token=[REDACTED]`) from NGINX access logs to prevent token leakage.
* **Database Port Conflict Isolation**:
  * Configurable host port (`POSTGRES_HOST_PORT=5433`) prevents host port 5432 collisions on Windows/macOS while keeping internal container networking on `db:5432`.

---

## 🧪 Verification & Test Results

| Test Category | Command / Procedure | Result |
| :--- | :--- | :---: |
| **TypeScript Compilation** | `npx.cmd tsc --noEmit` (Client) | **0 Errors** (Passed) |
| **Next.js Production Build** | `npm.cmd run build` (Client) | **12/12 Routes Compiled** (Passed) |
| **Markdown & Regex Unit Tests** | `node --experimental-strip-types scripts/verify-markdown.mjs` | **17/17 Tests Passed** |
| **Auth & Security** | Cookie verification, XSS sanitization, Token rotation | **Verified** |
| **Docker Compose Mesh** | Multi-container composition (`client`, `gateway`, `core`, `agent`, `db`, `redis`, `nginx`, `ngrok`) | **Configured & Validated** |

---

## 📁 Key File Map

```text
InsightAPI/
├── client/
│   ├── src/
│   │   ├── components/
│   │   │   ├── markdown/          # Master Markdown Rendering Engine (17 modular files)
│   │   │   │   ├── MarkdownRenderer.tsx
│   │   │   │   ├── MarkdownCode.tsx
│   │   │   │   ├── MarkdownHttpBlock.tsx
│   │   │   │   ├── MarkdownTable.tsx
│   │   │   │   ├── MarkdownCallout.tsx
│   │   │   │   ├── MarkdownMath.tsx
│   │   │   │   ├── MarkdownMermaid.tsx
│   │   │   │   └── ...
│   │   │   └── ui/
│   │   │       ├── message.tsx     # Message bubbles (no avatar icons, responsive layout)
│   │   │       └── conversation.tsx
│   │   ├── app/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── chat/page.tsx   # AI Chatbot workspace
│   │   │   │   └── billing/page.tsx# Stripe billing dashboard
│   │   │   └── globals.css         # KaTeX CSS & Prism syntax themes
│   │   └── lib/api-client/
│   │       ├── websocket.ts        # Clean WS connection without URL tokens
│   │       └── index.ts            # Axios instance with withCredentials
├── services/
│   ├── core-service/
│   │   └── app/api/v1/endpoints/
│   │       ├── auth.py             # HttpOnly cookie auth & token rotation
│   │       └── payments.py         # Stripe checkout & webhooks
│   ├── gateway/
│   │   ├── app/middleware/auth.py  # Cookie-based JWT auth middleware
│   │   └── app/api/v1/endpoints/ws.py # WS reverse proxy with cookie forwarding
│   └── agent-service/
│       ├── app/routers/chat.py     # Streaming chatbot WS endpoint
│       ├── app/services/chat_service.py # System prompt with Markdown formatting guidelines
│       └── app/engine/             # AXTree, Explorer, Risk Evaluator, Network Observer
├── nginx/
│   └── nginx.conf                  # Nginx proxy with cookie forwarding & log token redaction
├── docker-compose.yml              # Container definitions
├── .env                            # Environment configuration (POSTGRES_HOST_PORT=5433)
└── V1_IMPLEMENTATION.md            # This document
```
