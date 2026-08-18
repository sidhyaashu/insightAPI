InsightAPI = an autonomous computer-use intelligence layer for discovering hidden, undocumented APIs and understanding how modern web applications actually communicate.
---
An autonomous intelligence runtime that builds a behavioral model of a web application.
---
You have built:

InsightAPI v1 — an intelligent API discovery system.

The next architectural generation should become:

InsightAPI v2 — an autonomous application intelligence runtime.

And eventually:

InsightAPI Platform — autonomous computer-use intelligence for web/API/security technology.
---


<div align="center">

# 🤖 InsightAPI AI

### *Agentic Web API Intelligence Platform*

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Framework: LangGraph](https://img.shields.io/badge/Agentic-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Automation: Playwright](https://img.shields.io/badge/Browser-Playwright-green.svg)](https://playwright.dev/python/)

**Autonomously explore web applications, capture network traffic, analyze API behavior, infer dynamic parameters, and generate structured OpenAPI & Postman specifications.**

[Implemented v1 Features](V1_FEATURES.md) • [Future Roadmap](FUTURE.md) • [Docker Deployment](#-docker--local-deployment) • [Python SDK](#-python-sdk-usage) • [CLI Engine](#-cli-engine-usage)

</div>

---

## ⚡ What is InsightAPI AI?

Modern web applications expose dozens or hundreds of internal API endpoints. Discovering and documenting them manually via Browser DevTools is tedious, error-prone, and doesn't scale.

**InsightAPI AI** automates this end-to-end. Powered by **Playwright** browser automation and **LangGraph** agent orchestration, it:
1. **Explores Web UIs**: Navigates pages, expands menus, applies filters, and opens modals autonomously.
2. **Observes Network Traffic**: Captures REST, GraphQL, WebSocket, and SSE requests while stripping out telemetry and static asset noise.
3. **Infers Schemas & Relationships**: Uses LLMs to parameterize dynamic URL routes (`/users/101` $\rightarrow$ `/users/{id}`), generate JSON schemas, and infer authentication rules.
4. **Exports Specs**: Automatically outputs production-ready **OpenAPI 3.0.3 / 3.1**, **Postman Collections (v2.1)**, and **Markdown API documentation**.

---

## ✨ Core Features

* 🧠 **Interactive DOM Distillation (AXTree)**: Extracts lightweight Accessibility Tree snapshots (reducing prompt tokens from 100k+ to ~500) to feed LLM agents without raw HTML bloat.
* 🛡️ **Autonomous Action Safety**: Evaluates element contexts to automatically execute safe navigation actions while skipping high-risk actions (`delete`, `pay`, `purchase`, `modify permissions`).
* 🔄 **Self-Healing Runtime Scraper**: Dynamically generates, executes, and self-corrects Playwright interaction scripts when encountering complex custom UI widgets.
* 🔍 **API Noise Filtering**: Filters out static web assets (`.js`, `.css`, images) and third-party tracking domains (`google-analytics.com`, `sentry.io`).
* 🧬 **Dynamic Route Parameterization**: Normalizes dynamic IDs, hashes, and UUIDs into clean parameterized routes (`/products/{id}`).
* 🔑 **Hashed API Key Credentials & Stripe Billing**: Key issuance, key revocation, Stripe Checkout, and Customer Portal integration.

---

## 🐳 Docker & Local Deployment

Launch the full platform (FastAPI Gateway, Core Service, Agent Service, Next.js Web UI, PostgreSQL + pgvector, Redis) via Docker Compose:

### 1. Start Services
```bash
docker compose up -d --build
```

### 2. Verify Services Health
- **Web App UI**: `http://localhost:3000` (or your ngrok domain)
- **API Gateway**: `http://localhost:8080/health`
- **Core Service**: `http://localhost:8001/health`
- **Agent Service**: `http://localhost:8002/health`

---

## 💬 AI Chatbot SaaS & Intelligence

The InsightAPI platform features a full-screen, streaming **AI Intelligence Chatbot** with tiered daily usage quotas:

- **Free Tier**: 15 AI messages / day
- **Starter Tier**: 50 AI messages / day
- **Pro Tier**: 250 AI messages / day (Priority inference & reasoning)
- **Enterprise / Admin**: Unlimited AI messages

---

## 💻 CLI Engine Usage

Run autonomous crawls directly from your command line:

```bash
# Run autonomous crawl
insightapi crawl https://example.com --max-pages 20 --output ./openapi.json
```

---

## 🐍 Python SDK Usage

Import `insightapi` directly into any Python script, automation pipeline, or test suite:

```python
import asyncio
from insightapi import AgentEngine

async def main():
    engine = AgentEngine()
    results = await engine.crawl("https://example.com/app", max_pages=15)
    
    print(f"Captured {len(results.captured_endpoints)} endpoints")
    
    # Export OpenAPI & Postman specifications
    openapi_json = results.to_openapi()
    postman_json = results.to_postman()

asyncio.run(main())
```

---

## 🔐 Crawling Authenticated Apps

To crawl authenticated web applications, use the two-step session flow:

### Step 1 — Capture Session
```bash
python -m app.cli.main login https://app.example.com --output session.json
```

### Step 2 — Run Authenticated Crawl
```python
import asyncio, json
from insightapi import AgentEngine

async def main():
    with open("session.json") as f:
        session = json.load(f)

    engine = AgentEngine()
    result = await engine.crawl(
        "https://app.example.com",
        max_pages=10,
        session_state=session,
    )
    print(result.to_openapi())

asyncio.run(main())
```
> **Note**: `session_state` is injected into the Playwright browser context only. Credentials are **never** stored in logs, databases, or exported OpenAPI specs.
