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

### 🔍 6. API Drift Detection (PRO/ENTERPRISE)

* **`crawl_snapshots` Table**:
  * New PostgreSQL table persisting one row per endpoint per crawl: `(crawl_id, project_id, endpoint_key, schema_json, status_code, created_at)`.
  * Unique constraint `(crawl_id, endpoint_key)` with PostgreSQL `ON CONFLICT DO NOTHING` for idempotent upserts.
  * Written automatically on every crawl completion (fire-and-forget, non-fatal on failure).
* **`app/core/drift.py` — Drift Comparison Engine**:
  * `compare_snapshots(base_crawl_id, compare_crawl_id, db)` → `DriftReport` Pydantic model.
  * **Breaking change taxonomy**: `endpoint_removed`, `type_changed`, `required_field_removed`, `required_field_added`, `auth_added`.
  * **Non-breaking change taxonomy**: `endpoint_added`, `optional_field_added`, `optional_field_removed`, `field_made_optional`, `description_changed`, `auth_removed`.
* **REST Endpoints** (PRO tier gate):
  * `GET /api/v1/projects/{project_id}/drift?base={crawl_id}&compare={crawl_id}` — Returns `DriftReport` JSON. `base` is optional; auto-detects the most recent prior crawl when omitted.
  * `POST /api/v1/projects/{project_id}/drift/webhook` — Fires outbound HTTP POST to a CI webhook URL when `has_breaking_changes=True`. 3-attempt retry with exponential backoff (1s → 2s → 4s). SSRF protection applied to webhook URL.
* **GitHub Actions Workflow** (`.github/workflows/drift-check.yml`):
  * Triggers on PR to `main`/`master`.
  * Runs a crawl against staging URL, polls completion, compares against pinned main-branch snapshot, fails the check if `has_breaking_changes=true`.
* **Frontend** (`/reports/[id]/drift`):
  * PRO tier gate (lock overlay + upgrade CTA for lower tiers).
  * 4 animated summary cards: Breaking, Non-Breaking, Added, Removed.
  * Breaking changes table (rose-tinted rows with old→new type diff).
  * Non-breaking changes table (emerald-tinted rows).
  * Added/removed endpoint chips with HTTP method badges.
  * "Drift Reports" nav item added to sidebar.


* **Stripe Checkout Integration**:
  * Dynamically creates checkout sessions (`POST /api/v1/payments/checkout`) for Starter, Pro, and Enterprise subscription tiers.
* **Webhook Tier Synchronization**:
  * Robust webhook listener (`/api/v1/payments/webhook`) handling `checkout.session.completed`, `customer.subscription.updated`, and `customer.subscription.deleted`, automatically keeping PostgreSQL and Redis tiers synchronized in real time.
* **Self-Service Customer Portal**:
  * Redirects users to Stripe Customer Portal (`POST /api/v1/payments/portal`) for invoice downloads, credit card updates, and subscription cancellations.
  * Displays active period-end cancellation notices (`cancel_at_period_end`).

---

### 🛡️ 7. Human-in-the-Loop Schema Review & Approval Gate

* **`pending_review` Lifecycle State**:
  * Crawl execution supports opt-in review gate via `require_review: bool = True`.
  * After `AnalyzerNode` merges schemas and scores confidence, the session enters `pending_review` (exporters are paused).
  * WebSockets emit `{"type": "pending_review", "captured_count": N}` to alert the client interface.
* **Review REST Endpoints**:
  * `GET /api/v1/crawls/{id}/endpoints` — returns captured endpoints sorted by `confidence` ascending (surfacing lowest confidence first for immediate inspection), combining raw snapshots with any applied `reviewed_endpoints` overrides.
  * `PATCH /api/v1/crawls/{id}/endpoints/{endpoint_key}` — allows field rename, type override, and `is_excluded` toggles, persisting modifications into `CrawlSession.reviewed_endpoints`.
  * `POST /api/v1/crawls/{id}/approve` — accepts optional `confidence_threshold` (auto-excluding below threshold), merges reviewed overrides over raw snapshot schemas, executes `OpenAPIExporter`, `PostmanExporter`, and `MarkdownExporter` on the reviewed data, and transitions the session to `completed`.
* **Exporters Integration**:
  * `OpenAPIExporter`, `PostmanExporter`, and `MarkdownExporter` consume the reviewed/edited schemas, ensuring corrected field types and exclusions are reflected in the final generated artifacts.
* **Frontend Interactive Review Workspace** (`/crawls/[id]/review`):
  * **Confidence Sorting & Visualizations**: Lowest-confidence endpoints surfaced first with red (<50%), amber (50-75%), and green (>=75%) indicators.
  * **Dual-Mode Schema Editor**: Inline structured properties editor (field name, type selection, required checkbox, add/delete properties) + Raw JSON Schema editor with real-time JSON syntax validation.
  * **Selective Exclusions & Bulk Thresholds**: Per-endpoint exclude toggle + interactive threshold slider to auto-exclude endpoints below confidence cutoffs.
  * **Approve & Export Action**: Floating action bar to lock reviewed schemas, synthesize specs, and trigger exports.
* **Reports Dashboard** (`/reports`):
  * Overview list showing all crawl sessions with `pending_review` call-to-actions, completion badges, and direct links to review schemas or compare API drift diffs.

---

### 💳 8. Pay-Per-Crawl & Usage-Based Metered Billing

* **Metered Stripe Pricing & Price Configuration**:
  * Added `STRIPE_PRICE_METERED_CRAWL` configuration supporting Stripe metered prices (`POST /api/v1/payments/usage-records`) or fallback $1.50/crawl metered invoice items.
  * Plan price dictionary (`GET /api/v1/payments/plans`) exposes `PAY_PER_CRAWL` price mapping.
* **Overage Safeguard & User Preferences**:
  * Stored `allow_overage: bool = False` column on the `User` model, off by default to guarantee a strict "zero surprise bills" policy.
  * User preferences API (`PATCH /api/v1/users/me/preferences`) updates database and re-caches `allow_overage` in Redis session hash `user:session:{user_id}`.
  * Gateway auth middleware automatically inspects Redis cache and injects `x-user-allow-overage` header into downstream services.
* **Dynamic Daily Quota Branching**:
  * `start_crawl` checks Redis daily crawl counter against tier quotas (`FREE: 1`, `STARTER: 20`, `PRO: 100`, `PAYG: unlimited`).
  * If daily quota is exceeded and `allow_overage=True` (or user is on `PAYG` tier), the request bypasses the 429 rate limit block, executes normally, and flags `is_overage=True`.
  * If `allow_overage=False`, the request is rejected with a clear 429 prompt to enable overage in Billing settings.
* **Automated Metered Usage Reporting**:
  * On crawl completion (`run_background_crawl`), if `is_overage=True` or `tier == "PAYG"`, the engine automatically dispatches an HTTP POST request to `core-service` (`/api/v1/payments/usage-records`), creating an invoice item or metered usage record in Stripe for the user's customer profile.
* **Frontend Pricing & Billing UI**:
  * **Landing Page (`Pricing.tsx`)**: Added "Pay-as-you-go" plan card ($1.50/crawl, zero monthly commitment, full OpenAPI 3.1 & Postman export).
  * **Billing Dashboard (`/billing`)**: Interactive "Pay-Per-Crawl Overage Protection" toggle switch with instant Redux state synchronization, overage policy notice, and active Pay-as-you-go plan selector.
  * **Settings (`/settings`)**: Added direct link and status badge to configure Pay-Per-Crawl overage settings.

---

## 9. Domain Ownership Verification & ToS Gating

* **Domain Verification Architecture**:
  * Added `verified_domains` table tracking `user_id`, `domain`, `verification_token`, `verification_method` (`dns_txt` or `well_known`), `is_verified`, `verified_at`, and timestamps.
  * Added `tos_acceptances` table maintaining immutable audit records (`user_id`, `domain`, `target_url`, `user_ip`, `tos_version`, `accepted_at`) for legal defense and CFAA compliance.
* **DNS TXT & Well-Known File Challenges**:
  * Implemented `DomainVerifier` using DNS-over-HTTPS (DoH) JSON queries via Cloudflare (`https://cloudflare-dns.com/dns-query`) and Google (`https://dns.google/resolve`) to verify `_insightapi-challenge.{domain}` TXT records without OS-level socket limitations.
  * Implemented HTTP(S) challenge verification for `https://{domain}/.well-known/insightapi-verification.txt`.
* **Crawl Launch Enforcement**:
  * `POST /api/v1/crawls/start` normalizes target hostname and verifies domain ownership for the user (including apex domain resolution for subdomains).
  * If unverified: Requires explicit `tos_accepted: true` checkbox payload. If absent, immediately returns `403 Forbidden`.
  * If `tos_accepted: true`: Crawl proceeds normally and logs user IP, timestamp, target URL, and ToS version into `tos_acceptances`.
* **Frontend Verification & Compliance Suite**:
  * **Domain Management Dashboard (`/domains`)**: Shows registered targets, verification badges, DNS/HTTP challenge instructions with 1-click copy helpers, and live "Verify Now" button.
  * **Terms of Service & Safe Harbor (`/tos`)**: Comprehensive Acceptable Use Policy covering authorization warranty, CFAA compliance, prohibited destructive operations, and liability indemnification.
  * **Interactive Crawl Launcher (`CrawlSettingsModal.tsx`)**: Debounced real-time domain verification status query, verified target badge, and interactive required ToS checkbox for unverified targets.

---

## 10. Automated Authenticated Login Flows & AuthProfile Management

* **Encrypted Credential Architecture**:
  * Added `auth_profiles` table (`id`, `user_id`, `project_id`, `name`, `target_domain`, `login_url`, `auth_type`, `encrypted_credentials`, `last_tested_at`, `last_test_status`, `last_test_error`, `created_at`, `updated_at`).
  * Implemented Fernet symmetric credential encryption with key derivation from `AUTH_PROFILE_SECRET_KEY` in `app/core/encryption.py`. Secrets are encrypted at rest and never exposed in logs, specs, or unmasked GET responses.
* **Autonomous Login Engine (`AutoLoginExecutor`)**:
  * **Form Authentication (`FormAuthHandler`)**: Uses `DOMDistiller` to automatically detect username/email and password inputs and submit controls, injects credentials, submits form, and waits for post-login redirection and network stabilization.
  * **OAuth & SAML Handlers (`OAuthHandler`)**: Drives automated consent flows for Google OAuth, GitHub OAuth, and SAML SSO for test accounts.
  * **Storage State Extraction**: Captures authenticated Playwright `storage_state` (cookies and localStorage) directly in memory, eliminating manual `session.json` capture.
* **REST Endpoints & Crawl Gating**:
  * `POST /api/v1/auth-profiles` — Create encrypted auth profile.
  * `GET /api/v1/auth-profiles` — List profiles (with masked secrets).
  * `GET /api/v1/auth-profiles/{id}` — Get single profile.
  * `PATCH /api/v1/auth-profiles/{id}` — Update profile.
  * `DELETE /api/v1/auth-profiles/{id}` — Delete profile.
  * `POST /api/v1/auth-profiles/{id}/test` & `POST /api/v1/auth-profiles/test-transient` — Live login test runner with diagnostic feedback.
  * `AgentEngine.crawl` and `start_crawl` accept `auth_profile_id`, automatically executing `AutoLoginExecutor` prior to crawl exploration.
* **Frontend Management Suite**:
  * **Auth Profiles Dashboard (`/auth-profiles`)**: Lists stored profiles, status badges, and interactive live test flow runner with cookie capture counts.
  * **Crawl Settings Modal (`CrawlSettingsModal.tsx`)**: Added AuthProfile selector dropdown to select stored authenticated profiles for crawls.
  * **Sidebar Navigation (`app-sidebar.tsx`)**: Added "Auth Profiles" navigation item.

---

## 11. Playwright Regression Test Generator

* **Ordered Action Trace Recording**:
  * Extended `CrawlState` and `CrawlSession` ORM model with `action_traces` JSON field.
  * `ExecutorNode` logs an ordered sequence of executed UI actions along with before/after URLs, target selectors, filled values, and sliced network calls (`network_calls_triggered`).
  * `CrawlResult` in the SDK exposes `action_traces` and `to_playwright_test(format="python" | "typescript")`.
* **Playwright Test Suite Generator Engine (`PlaywrightTestGenerator`)**:
  * **Python Generator**: Produces runnable `pytest-playwright` scripts with `expect_response` network triggers, status assertions, and response JSON contract field validations.
  * **TypeScript Generator**: Produces runnable `@playwright/test` specs with `Promise.all([page.waitForResponse(...), page.action(...)])` patterns and expected schema field checks.
  * **CI/CD Zip Packager**: Generates downloadable archives containing test files, `pytest.ini` / `playwright.config.ts`, dependencies (`requirements.txt` / `package.json`), and setup instructions in `README.md`.
* **REST Endpoints**:
  * `GET /api/v1/crawls/{id}/generate-tests?format=python|typescript&as_zip=true|false`
  * Extended `GET /api/v1/reports/{id}/export` to support `playwright_python` and `playwright_ts`.
* **Frontend UI & Interactive Test Studio**:
  * **Crawl Report Page (`/reports/[id]`)**: Full report dashboard showing discovered endpoints, replayable action timeline, OpenAPI spec preview, and "Generate Playwright Test Suite" modal.
  * **Interactive Test Studio Modal**: Python/TypeScript tabbed code preview with syntax styling, copy-to-clipboard, 1-click script download, and full CI/CD zip archive export.
  * **Reports Overview (`/reports`)**: Added direct "Report & Tests" action button on completed crawl cards.

---

## 12. Enterprise Multi-Tenant Data Isolation & Audit Logging

* **Enterprise Audit Trail Engine (`AuditLogger` & `audit_logs` Table)**:
  * Persistent `audit_logs` table recording `user_id`, `project_id`, `action`, `target_id`, `ip`, `timestamp`, and `metadata_json`.
  * Captures `crawl.create`, `crawl.delete`, `export.download`, `auth_profile.create`, `auth_profile.update`, `auth_profile.delete`, `auth_profile.test`, and `drift_webhook.trigger`.
  * Safe asynchronous logging pattern ensuring zero failure blast radius for client requests.
* **Enterprise Audit Logs REST API**:
  * `GET /api/v1/audit-logs`: Strictly gated to `ENTERPRISE` tier and `ADMIN` role with action, date range, target entity, and paginated filters. Returns 403 Forbidden for non-enterprise tiers.
* **Row-Level Tenant Boundary Hardening**:
  * Query-layer `user_id` validation enforced across `crawls.py`, `reports.py`, `auth_profiles.py`, `review.py`, and `drift.py`.
  * Any cross-tenant access attempt returns `404 Not Found` (eliminating resource enumeration vulnerabilities).
* **PostgreSQL Row-Level Security (RLS) & Schema Isolation Blueprint**:
  * [`deploy/rls_and_isolation.sql`](file:///c:/Users/ashut/Devlopments/InsightAPI/deploy/rls_and_isolation.sql): Complete production DDL script with RLS policies using `app.current_user_id` and dedicated per-tenant schema generation functions (`create_tenant_schema()`).
* **Customer-Managed VPC & On-Premises Docker Compose**:
  * [`docker-compose.enterprise.yml`](file:///c:/Users/ashut/Devlopments/InsightAPI/docker-compose.enterprise.yml): Blueprint for air-gapped / customer VPC deployment with customer-managed PostgreSQL (`EXTERNAL_POSTGRES_HOST`), customer-managed Redis (`EXTERNAL_REDIS_HOST`), private network bridging, and local LLM endpoint support.
  * [`docs/ENTERPRISE_DEPLOYMENT.md`](file:///c:/Users/ashut/Devlopments/InsightAPI/docs/ENTERPRISE_DEPLOYMENT.md): Enterprise security, multi-tenancy trade-offs, SOC2/ISO27001 audit compliance, and deployment guide.

---

## 13. Vision LLM Fallback & Set-of-Mark (SoM) Navigation

* **Set-of-Mark (SoM) Visual Candidate Generator (`app/engine/vision/som.py`)**:
  * `SetOfMarksAnnotator`: Detects `<canvas>`, WebGL, and graphical container rects on the page.
  * Generates spatial bounding box proposals across toolbars, tool strips, and interactive quadrants.
  * Overlays high-contrast numbered mark badges (`[1]`, `[2]`, `[3]`, ...) and borders using Pillow on captured viewport screenshots.
* **Canvas Detection & Triggering (`DOMDistiller`)**:
  * `DOMDistiller.has_canvas_element()`: Detects `<canvas>`, WebGL embed/object tags, and dense graphical containers.
  * Triggers `needs_vision_fallback: true` in `CrawlState` when AXTree extraction yields sparse/zero interactive elements on canvas pages.
* **Autonomous Vision Planner (`VisionPlannerNode`)**:
  * [`vision_planner.py`](file:///c:/Users/ashut/Devlopments/InsightAPI/services/agent-service/app/agents/nodes/vision_planner.py): Sends Set-of-Mark annotated screenshots to `ModelTier.VISION` (GPT-4o / GPT-4o-mini).
  * Prompts the Vision LLM to analyze the graphical UI and select the optimal numbered mark for API discovery.
  * Maps the chosen mark back to screen coordinates `(x, y)`.
* **Playwright Coordinate Mouse Execution (`DynamicRuntimeExecutor`)**:
  * Executes coordinate-based mouse clicks (`await page.mouse.click(x, y)`) and typing without requiring DOM selectors.
  * `ExecutorNode` logs `is_vision_action: true`, coordinate metadata, and increments `vision_action_count`.
* **Confidence Scoring & Report Surface**:
  * `AnalyzerNode.compute_confidence()`: Applies a 15% uncertainty discount on vision-derived endpoints reflecting coordinate interaction vs semantic DOM contracts.
  * `OpenAPIExporter`: Emits `x-vision-derived: true` vendor extension.
  * `MarkdownExporter`: Displays `Source: Vision Fallback` in endpoint details.

---

## 14. Form Submission Attribution & JS Fetch/XHR Correlation

* **DOM Form Extraction & Context Gathering (`dom_distiller.py`)**:
  * Extracts form action URL, HTTP method, and full array of form input fields (`name`, `type`, `placeholder`, `value`, `label`).
  * Flags form submit controls (`button[type="submit"]`, `input[type="submit"]`, or buttons within form containers).
* **Live Network Observation & Diff Window Attribution (`dynamic_executor.py`, `executor.py`)**:
  * Snapshots `NetworkObserver` captured count before form interaction.
  * Auto-populates unfilled sibling form fields with realistic context-aware dummy data.
  * Executes submit and settles network requests via `PageNetworkStabilizer`.
  * Diffs observer captures in the execution window to attribute resulting API requests.
* **Multi-Request Submission Classification**:
  * Distinguishes primary mutation endpoints (`POST/PUT/PATCH` with `2xx/3xx` status) from auxiliary validation or telemetry calls.
  * Attaches full `triggered_by` metadata to the primary endpoint:
    ```json
    {
      "action_type": "form_submit",
      "selector": "form#signup button",
      "form_context": "Create your organization account",
      "form_action": "/api/v1/auth/signup",
      "form_method": "POST",
      "field_names": ["email", "password", "org_name"],
      "submitted_fields": { "email": "user@example.com", "org_name": "Acme Corp" }
    }
    ```
  * Attaches all secondary preflight/validation calls under `related_calls`.
* **OpenAPI & Markdown Schema Enrichment**:
  * `AnalyzerNode`: Maps form field names and data types directly into OpenAPI `requestBody` schema properties (`form_inferred_request_schema`).
  * `OpenAPIExporter`: Emits `x-triggered-by` and `x-related-calls` vendor extensions on the operation object.
  * `MarkdownExporter`: Displays `Triggered By` form context and lists all related network calls.

---

### 🛡️ 15. Humanized Playwright Interaction Engine & Anti-Bot Footprint Reduction

* **`Humanizer` Module (`services/agent-service/app/engine/browser/humanizer.py`)**:
  * **Cubic Bezier-Curve Mouse Trajectories (`compute_bezier_points`)**: Calculates smooth, non-linear trajectories between last known mouse position (`page._last_mouse_pos`) and target coordinates with randomized perpendicular arc curvature.
  * **Smooth Jittered Movement (`humanized_move`)**: Navigates across 8–18 discrete intermediate steps with 5–15ms randomized micro-pauses, targeting randomized interior points rather than robotic dead-centers.
  * **Authentic Click Dynamics (`humanized_click`)**: Glides cursor smoothly to target, executes randomized pre-click hesitation (50–150ms), holds `mouse.down()` (30–90ms), releases `mouse.up()`, and adds post-click settling micro-pauses (20–60ms).
  * **Per-Keystroke Typing Cadence (`humanized_type`)**: Types character-by-character with variable speed (30–70ms base), word-boundary & punctuation pauses (60–140ms), and occasional cognitive hesitation (100–220ms).
  * **Incremental Wheel Scrolls (`humanized_scroll`)**: Divides large scrolls into 3–7 randomized wheel increments with 25–75ms inter-step pauses.
* **Stealth Configuration & Fast Mode**:
  * `Settings.HUMANIZE_INTERACTIONS`: Enabled by default (`True`) across the SDK, REST API, and CLI.
  * `DynamicRuntimeExecutor(page, humanize=...)`: Seamlessly switches between `Humanizer` methods and instant direct Playwright calls.
  * `--fast / -f` CLI Option & SDK `fast_mode`: Allows instant execution on local/trusted targets where speed takes priority over anti-bot stealth.

---

## 🧪 Verification & Test Results

| Test Category | Command / Procedure | Result |
| :--- | :--- | :---: |
| **TypeScript Compilation** | `npx.cmd tsc --noEmit` (Client) | **0 Errors** (Passed) |
| **Next.js Production Build** | `npm.cmd run build` (Client) | **14/14 Routes Compiled** (Passed) |
| **Humanizer & Interaction Engine Tests** | `pytest services/agent-service/tests/test_humanizer.py` | **6/6 Tests Passed** |
| **Form Submission Attribution Tests** | `pytest services/agent-service/tests/test_form_submission_attribution.py` | **5/5 Tests Passed** |
| **Vision Fallback & SoM Unit Tests** | `pytest services/agent-service/tests/test_vision_fallback.py` | **6/6 Tests Passed** |
| **Tenant Isolation & Audit Integration Tests** | `pytest services/agent-service/tests/test_tenant_isolation_and_audit.py` | **6/6 Tests Passed** |
| **Playwright Test Generator Tests** | `pytest services/agent-service/tests/test_playwright_test_gen.py` | **6/6 Tests Passed** |
| **Auto-Login & AuthProfile Tests** | `pytest services/agent-service/tests/test_auto_login.py` | **6/6 Tests Passed** |
| **Domain Verification Unit Tests** | `pytest services/agent-service/tests/test_domain_verification.py` | **7/7 Tests Passed** |
| **Pay-Per-Crawl Unit Tests** | `pytest services/agent-service/tests/test_pay_per_crawl.py` | **4/4 Tests Passed** |
| **Review Gate Unit Tests** | `pytest services/agent-service/tests/test_review_gate.py` | **3/3 Tests Passed** |
| **Comprehensive Feature Suite** | `pytest (59 collected tests)` | **59/59 Tests Passed** |
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
