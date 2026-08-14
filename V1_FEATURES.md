# InsightAPI AI — Implemented v1 Features Specification

This document provides a comprehensive detail of all features implemented in **InsightAPI AI v1 Release**.

---

## 🔐 1. Authentication & Security Engine

* **Multi-Method Authentication**:
  * **Email & Password**: Registration (`POST /api/auth/register`), verification email dispatch, rate-limited resend (`POST /api/auth/resend-verification`), login (`POST /api/auth/login`), password reset request (`POST /api/auth/forgot-password`), and reset execution (`POST /api/auth/reset-password`).
  * **OAuth 2.0 Integrations**: GitHub OAuth (`GET /api/auth/github/login`) and Google OAuth (`GET /api/auth/google/login`).
  * **Identity Account Unification**: Automatically unifies user identity records across email/password, Google, and GitHub logins under a single verified account without duplicate email errors or loss of subscription history.
* **Token Architecture & Rotation**:
  * **Access Token**: Short-lived JWT (15-minute expiry) stored **ONLY in memory** (Redux Auth Store), protecting against XSS token theft.
  * **Refresh Token**: Single-use long-lived token stored in an `HttpOnly; Secure; SameSite=Lax` browser cookie (`path="/api/auth/refresh"`).
  * **Automatic Rotation**: Single-use token rotation on `/api/auth/refresh`. Detects token reuse and instantly revokes all active sessions for that user.
  * **Silent Session Bootstrap**: `AuthProvider` silently restores sessions on app load via `HttpOnly` refresh token cookie.

---

## 📊 2. Autonomous Web UI Exploration Engine

* **Interactive DOM Distillation (AXTree)**:
  * Extracts lightweight Accessibility Tree DOM snapshots containing only semantic elements (`a`, `button`, `input`, `select`, `textarea`, `[role]`, `[onclick]`).
  * Reduces prompt token size from 100k+ HTML bloat down to ~500 tokens.
* **Two-Tier Action Safety Classifier**:
  * **Tier 1 (Fast Guardrails)**: Sub-millisecond regex pre-filtering for safe view/filter targets vs unsafe destructive actions (`delete`, `pay`, `purchase`, `cancel`).
  * **Tier 2 (Context Enrichment)**: Contextually evaluates surrounding form labels and parent headers for ambiguous submit buttons.
* **Dynamic Runtime Execution & Reliability**:
  * Auto-populates search fields, emails, dates, quantities, and input text prior to submission.
  * Auto-detects and clears blocking cookie banners, dialog backdrops, and interstitial modals (`Accept`, `Close`).
* **Stealth & Anti-Detection**:
  * Spoofs WebGL vendor signatures (`Intel Inc.`), overrides hardware concurrency metrics, and patches Permissions API.

---

## 🛰️ 3. Network Traffic Observer & Endpoint Intelligence

* **Telemetry & Static Asset Filtering**: Ignores static web assets (`.js`, `.css`, `.png`, `.svg`, `.woff2`) and third-party tracking domains (`google-analytics.com`, `sentry.io`).
* **Dynamic Parameter Deduplication**: Normalizes dynamic URL paths (`/users/101`, `/users/102`) into template routes (`/users/{id}`).
* **GraphQL Payload Parsing**: Treats distinct `operationName` values (query, mutation, batch) as separate logical endpoints.
* **DOM State Graph Hashing**: Hashes `(normalized_URL, AXTree_structural_fingerprint)` to distinguish SPA modal/tab states at the same URL.

---

## 💬 4. Full SaaS AI Chatbot & Tier Quota System
 
* **Claude-Inspired Charcoal Aesthetic**: Warm charcoal palette (`#1b1b19`), borderless edge-to-edge layout, floating borderless top control, and collapsible sidebar.
* **Streaming WebSocket Intelligence**: Low-latency token-by-token streaming with markdown rendering, syntax highlighting, and conversation history.
* **Tier-Based Usage Quota Enforcement**:
  * **Free**: 15 AI messages / day
  * **Starter**: 50 AI messages / day
  * **Pro**: 250 AI messages / day (Priority inference & reasoning)
  * **Enterprise / Admin**: Unlimited messages
* **Live Quota Tracking**: Real-time daily quota tracking backed by Redis counters (`chat:daily:{user_id}:{date}`) with automatic reset and in-UI upgrade alerts.

---

## 💳 5. Stripe Billing & Subscriptions

* **Stripe Billing & Customer Portal (`/billing`)**:
  * Dynamic price ID loading from `GET /api/v1/payments/plans`.
  * Stripe Checkout integration for `STARTER`, `PRO`, and `ENTERPRISE` plans.
  * Stripe Customer Portal integration (`POST /api/v1/payments/portal`).
  * Period-end cancellation banners (`cancel_at_period_end`).
