# InsightAPI AI — Third-Party Integrations & Extensions Guide

## Overview

Yes! **InsightAPI AI**'s modular architecture is designed to integrate with third-party libraries and specialized tools. Adding these extensions supercharges your agent's crawling yield, anti-bot stealth, security testing, and vector memory.

---

## 🚀 5 High-Impact Third-Party Integrations

```
                               ┌───────────────────────────┐
                               │  InsightAPI Engine Core   │
                               └─────────────┬─────────────┘
                                             │
      ┌──────────────────┬───────────────────┼───────────────────┬──────────────────┐
      ▼                  ▼                   ▼                   ▼                  ▼
┌───────────┐      ┌───────────┐       ┌───────────┐       ┌───────────┐      ┌───────────┐
│ mitmproxy │      │Stealth JS │       │Schemathesis│      │ ChromaDB  │      │  Browser  │
│ (gRPC/H2) │      │ (Anti-Bot)│       │ (API Fuzz)│       │(Local RAG)│      │ Extensions│
└───────────┘      └───────────┘       └───────────┘       └───────────┘      └───────────┘
```

### 1. `mitmproxy` (Network & gRPC Interception Powerhouse)
- **What it does:** Operates as a Python-scriptable HTTP/2, HTTP/3, and gRPC proxy.
- **How it helps InsightAPI:** Playwright captures standard browser XHR/fetch traffic. `mitmproxy` taps into lower-level protocol streams — capturing **gRPC, Protobuf payloads, and HTTP/2 multiplexed streams** that standard browser listeners miss.
- **Package:** `pip install mitmproxy`

### 2. `playwright-stealth` & `fake-useragent` (Anti-Bot Evasion)
- **What it does:** Overrides browser fingerprints (WebGL vendor, Canvas noise, Navigator metrics, Cloudflare Turnstile bypasses).
- **How it helps InsightAPI:** Enables the agent to autonomously crawl heavily protected enterprise SaaS apps (protected by Cloudflare, Akamai, Datadome, PerimeterX) without getting blocked by CAPTCHAs.
- **Package:** `pip install playwright-stealth fake-useragent`

### 3. `schemathesis` (Automated Property-Based API Fuzzing)
- **What it does:** Takes an OpenAPI specification and automatically generates hundreds of edge-case test payloads.
- **How it helps InsightAPI:** As soon as `AnalyzerNode` generates the OpenAPI spec, `schemathesis` can automatically probe the captured endpoints for 500 server errors, unhandled exceptions, and security vulnerabilities.
- **Package:** `pip install schemathesis`

### 4. `chromadb` / `faiss-cpu` (Zero-Dependency Embedded Vector Search)
- **What it does:** In-memory / embedded vector database requiring zero external services.
- **How it helps InsightAPI:** Currently `EndpointVectorStore` uses PostgreSQL `pgvector`. Adding `chromadb` enables natural language semantic search (`POST /api/v1/search`) **even in zero-dependency SDK mode without PostgreSQL**.
- **Package:** `pip install chromadb`

### 5. Chrome Browser Extensions (CRX Loading in Playwright)
- **What it does:** Playwright allows launching Chromium contexts with custom unpacked Chrome extensions (`--disable-extensions-except=/path/to/extension`).
- **How it helps InsightAPI:** You can load specialized Chrome extensions (e.g. Wappalyzer extension, React/Vue DevTools extension, Auth helpers) directly into the Playwright browser context so the agent gets extra metadata about the target application.

---

## 🛠️ How to Add a New Extension

Adding an extension to InsightAPI is simple:

1. Add the dependency to `backend/pyproject.toml` under `dependencies`.
2. Wrap the extension in an optional import guard so InsightAPI works even if the extension is not installed:
   ```python
   try:
       import chromadb
       HAS_CHROMADB = True
   except ImportError:
       HAS_CHROMADB = False
   ```
3. Register the extension capability in `app/core/config.py` with a feature flag.
