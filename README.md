<div align="center">

# 🤖 InsightAPI AI

### *Agentic Web API Intelligence Platform & Open-Source Python SDK*

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Framework: LangGraph](https://img.shields.io/badge/Agentic-LangGraph-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Automation: Playwright](https://img.shields.io/badge/Browser-Playwright-green.svg)](https://playwright.dev/python/)

**Autonomously explore web applications, capture network traffic, analyze API behavior, infer dynamic parameters, and generate structured OpenAPI & Postman specifications.**

[Quickstart](#-quickstart) • [Python SDK](#-python-sdk-usage) • [CLI Engine](#-cli-engine-usage) • [Docker Setup](#-docker--local-deployment) • [Compliance](#%EF%B8%8F-compliance--responsible-crawling-guardrails) • [Crawling Policy](CRAWLING_POLICY.md)

</div>

---

## ⚡ What is InsightAPI AI?

Modern web applications expose dozens or hundreds of internal API endpoints. Discovering and documenting them manually via Browser DevTools is tedious, error-prone, and doesn't scale.

**InsightAPI AI** automates this end-to-end. Powered by **Playwright** browser automation and **LangGraph** agent orchestration, it:
1. **Explores Web UIs**: Navigates pages, expands menus, applies filters, and opens modals autonomously.
2. **Observes Network Traffic**: Captures REST, GraphQL, WebSocket, and SSE requests while stripping out telemetry and static asset noise.
3. **Infers Schemas & Relationships**: Uses LLMs to parameterize dynamic URL routes (`/users/101` $\rightarrow$ `/users/{id}`), generate JSON schemas, and infer authentication rules.
4. **Exports Specs**: Automatically outputs production-ready **OpenAPI 3.0.3**, **Postman Collections (v2.1)**, and **Markdown API documentation**.

---

## ✨ Core Features

* 🧠 **Interactive DOM Distillation (AXTree)**: Extracts lightweight Accessibility Tree snapshots (reducing prompt tokens from 100k+ to ~500) to feed LLM agents without raw HTML bloat.
* 🛡️ **Autonomous Action Safety**: Evaluates element contexts to automatically execute safe navigation actions while skipping high-risk actions (`delete`, `pay`, `purchase`, `modify permissions`).
* 🔄 **Self-Healing Runtime Scraper**: Dynamically generates, executes, and self-corrects Playwright interaction scripts when encountering complex custom UI widgets.
* 🔍 **API Noise Filtering**: Filters out static web assets (`.js`, `.css`, images) and third-party tracking domains (`google-analytics.com`, `sentry.io`).
* 🧬 **Dynamic Route Parameterization**: Normalizes dynamic IDs, hashes, and UUIDs into clean parameterized routes (`/products/{id}`).
* 📦 **Triple Distribution**: Usable as a **Python SDK**, an interactive **CLI tool**, or a **REST API service**.

---

## 🚀 Quickstart

### Installation

Install the open-source Python SDK and CLI via `pip`:

```bash
git clone https://github.com/your-org/InsightAPI.git
cd InsightAPI/backend
pip install -e .
playwright install chromium
```

### Environment Setup

Create a `.env` file in your root folder:

```env
# Azure OpenAI Credentials (or Standard OpenAI)
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=your_azure_api_key
AZURE_OPENAI_DEPLOYMENT=gpt-5.4

# Or Standard OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

---

## 🐍 Python SDK Usage

Import `insightapi` directly into your Python scripts or CI/CD pipelines:

```python
import asyncio
from insightapi import AgentEngine

async def main():
    # 1. Initialize Engine
    engine = AgentEngine(headless=True)
    
    # 2. Run Autonomous Exploration
    result = await engine.crawl("https://example.com", max_pages=5)
    
    # 3. Export API Specs
    print("--- OpenAPI 3.0 Spec ---")
    print(result.to_openapi())
    
    print("\n--- Postman Collection ---")
    print(result.to_postman())
    
    print("\n--- Markdown Docs ---")
    print(result.to_markdown())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 💻 CLI Engine Usage

Run interactive exploration sessions directly from your terminal:

```bash
# 1. Start an autonomous crawl session
insightapi crawl https://example.com --max-pages 10

# 2. List discovered API endpoints
insightapi list-endpoints <session_id>

# 3. Export OpenAPI 3.0 spec or Postman collection to file
insightapi export --session-id <session_id> --format openapi --output ./openapi.json
insightapi export --session-id <session_id> --format postman --output ./postman.json
insightapi export --session-id <session_id> --format markdown --output ./API_DOCS.md
```

---

## 🔐 Crawling Authenticated Apps

InsightAPI AI never asks for or stores credentials. Instead you save a **session file** once
(by logging in manually in a real browser window) and then reuse it for as many crawls as you want.

### Step 1 — Save your session

```bash
insightapi login https://app.example.com --output session.json
```

A visible Chromium window opens and navigates to the URL. Log in as you normally would, then return
to the terminal and press **Enter**. InsightAPI saves the resulting cookies + localStorage to
`session.json` and closes the browser.

> **Security**: `session.json` contains live session cookies. Treat it like a password.
> Keep it local — never commit it to version control.

### Step 2 — Crawl with the saved session

```bash
insightapi crawl https://app.example.com --session-file session.json --max-pages 20
```

The crawler starts already authenticated and explores pages behind the login wall.

### Python SDK

```python
import asyncio, json
from app.sdk import AgentEngine

async def main():
    with open("session.json") as f:
        session = json.load(f)

    engine = AgentEngine(headless=True)
    result = await engine.crawl(
        "https://app.example.com",
        max_pages=20,
        session_state=session,   # injected into the Playwright browser context
    )
    print(result.to_openapi())

asyncio.run(main())
```

### REST API

```bash
curl -X POST "http://localhost:8000/api/v1/crawls/start" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://app.example.com",
       "max_pages": 20,
       "session_state": { "cookies": [...], "origins": [...] }
     }'
```

> `session_state` is forwarded only to the Playwright browser context inside the crawl worker
> and is **never** stored in crawl session records or included in exported specs.

---

## 🐳 Docker & Local Deployment

Spin up the complete stack (PostgreSQL with `pgvector`, Redis, and FastAPI Backend) with a single command:

```bash
# Copy template environment file
cp .env.example .env

# Build and start all services
docker compose up --build
```

* **FastAPI Interactive Docs**: `http://localhost:8000/docs`
* **PostgreSQL + pgvector**: `localhost:5432`
* **Redis Cache**: `localhost:6379`

---

## 📐 System Architecture

```
                                 User / CLI / Python SDK
                                           │
                                           ▼
                                    FastAPI Backend
                                           │
                       ┌───────────────────┴───────────────────┐
                       ▼                                       ▼
             LangGraph StateGraph                    Async Playwright Driver
                       │                                       │
     ┌─────────────────┼─────────────────┐                     │
     ▼                 ▼                 ▼                     │
PlannerNode     RiskEvaluatorNode   AnalyzerNode               │
     │                 │                 │                     │
     └─────────────────┴─────────┬───────┘                     │
                                 │                             │
                                 ▼                             ▼
                    Interactive DOM (AXTree) <─── Network Observer Listener
                                                       │
                                                       ▼
                                            Parameterizer & Exporters
                                           (OpenAPI / Postman / Markdown)
```

---

## 🛡️ Compliance & Responsible Crawling Guardrails

InsightAPI AI is built for authorized software engineering, API development, and security auditing. It includes built-in legal and compliance protections:

* 🤖 **robots.txt Parser (`RobotsChecker`)**: Automatically fetches and parses target site `robots.txt` rules. If the target URL or root path is disallowed, the CLI halts and requires interactive confirmation or `--force` (`-F`) override.
* ⏱️ **Per-Domain Rate Limiter (`DomainRateLimiter`)**: Enforces a default minimum **500ms** delay spacing between requests per target domain (`MIN_DOMAIN_DELAY_MS`), preventing burst traffic spikes. Configurable via `--rate-limit <ms>` CLI flag or `rate_limit_ms` SDK argument.
* 🛡️ **Two-Tier Action Risk Classifier**: Evaluates element target contexts before execution to automatically skip destructive or financial actions (`delete`, `pay`, `purchase`, `update password`).
* 🔒 **Data & Token Redaction**: Strips session cookies, Bearer tokens, CSRF/XSRF tokens, and secret keys from generated OpenAPI, Postman, and Markdown outputs.

For full ethical guidelines and permitted use cases, read our **[Crawling Policy](CRAWLING_POLICY.md)**.

---

## 🧪 Running Unit Tests

Run the comprehensive pytest suite to verify browser distillation, network filters, agent nodes, and exporter formats:

```bash
pytest backend/tests
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1. Fork the Repository.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📜 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.
