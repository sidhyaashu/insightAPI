# Future Client Setup Guide (Phase 5)

When you are ready to add the Web UI Client (Next.js 14 + React Flow + Tailwind CSS + shadcn/ui) to **InsightAPI AI**, follow this blueprint.

---

## 🏛️ The 3 Core Client Sections

```
                                  ┌────────────────────────────────┐
                                  │   InsightAPI Next.js Client    │
                                  └───────────────┬────────────────┘
                                                  │
             ┌────────────────────────────────────┼────────────────────────────────────┐
             ▼                                    ▼                                    ▼
┌──────────────────────────┐        ┌──────────────────────────┐        ┌──────────────────────────┐
│   1. Marketing Landing   │        │ 2. Interactive Dashboard │        │  3. Documentation Portal │
│      Route: `/`          │        │    Route: `/dashboard`   │        │      Route: `/docs`      │
└──────────────────────────┘        └──────────────────────────┘        └──────────────────────────┘
```

### 1. Marketing Landing Page (`/`)
> **Goal:** High-converting, state-of-the-art marketing page that wows visitors at first glance.

- **Hero Section:** Dynamic dark-mode gradient hero with animated tagline *"Browser DevTools on Autopilot — Turn Any Web App Into OpenAPI Specs in Seconds"*.
- **Interactive Live Demo Sandbox:** 15-second interactive preview showing the Playwright agent crawling a mock site and generating an OpenAPI spec live.
- **Key Feature Grid:** Visual cards for Autonomous Browsing, LLM Goal-Directed Planner, Vision Fallback, Parallel Sub-Agents, and API Drift Detection.
- **Pricing Tiers:** Transparent pricing cards for Free (5 crawls/mo), Pro ($29/mo), Team ($99/mo), and Enterprise On-Prem.
- **Interactive Call-to-Action (CTA):** *"Get Started Free"* & *"View Open Source GitHub Repo"*.

---

### 2. Interactive Workspace Dashboard (`/dashboard`)
> **Goal:** The core control center where users trigger, monitor, and explore crawl results.

- **Crawl Launcher Control Panel:**
  - Target URL input box.
  - Natural-language Goal input (`"Find all payment and billing APIs"`).
  - Max Pages budget slider (1–50 pages).
  - Parallel Sub-Agents slider (1–5 workers).
- **Live Streamed Agent Execution:** Real-time log terminal and WebSocket canvas stream showing the agent navigating pages and invoking Playwright actions.
- **Interactive React Flow Endpoint Graph:** Node graph connecting UI screens (pages) to triggered API endpoints.
- **Semantic Endpoint Search Bar:** Search across captured endpoints using natural language (`"find login endpoints"`).
- **Token & USD Cost Spend Monitor:** Live metrics card displaying `tokens_used`, `llm_calls_made`, and `estimated_cost_usd`.

---

### 3. Documentation & Spec Portal (`/docs`)
> **Goal:** Interactive documentation viewer and export hub for generated API specifications.

- **Interactive OpenAPI Spec Viewer:** Embedded Swagger UI / Redoc viewer rendering OpenAPI 3.0 specs with captured example request/response payloads.
- **Export Hub:** One-click downloads for OpenAPI 3.0 JSON, Postman Collection v2.1 JSON, and Markdown docs.
- **SDK & CLI Reference Docs:** Built-in usage guides for `insightapi` Python SDK and CLI commands.

---

## 📁 Monorepo Folder Structure

```
InsightAPI/                       <-- Root Directory
├── backend/                      <-- Python FastAPI Engine (Existing)
│   ├── app/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                     <-- Next.js 14 Client App (Future)
│   ├── app/
│   │   ├── page.tsx              <-- 1. Marketing Landing Page (/)
│   │   ├── dashboard/
│   │   │   └── page.tsx          <-- 2. Interactive Dashboard (/dashboard)
│   │   └── docs/
│   │       └── page.tsx          <-- 3. Documentation Portal (/docs)
│   ├── components/               <-- UI, React Flow canvas, Swagger components
│   ├── public/
│   └── Dockerfile                <-- Frontend Next.js Dockerfile
├── docker-compose.yml            <-- Orchestrates frontend + backend + postgres + redis
└── README.md
```

---

## 🛠️ Step 1: Initializing the Frontend Client

When you're ready to build the client, run this command from the project root:

```bash
npx -y create-next-app@latest frontend --typescript --tailwind --eslint --app --import-alias="@/*"
```

Install key packages inside `frontend/`:
```bash
cd frontend
npm install @xyflow/react lucide-react clsx tailwind-merge socket.io-client swagger-ui-react
```

---

## 📡 Step 2: Communication Channels Matrix

| Channel | Frontend View | Backend API Endpoint |
| :--- | :--- | :--- |
| **REST API** | Launch Crawl (`/dashboard`) | `POST /api/v1/crawls/start` |
| **REST API** | Fetch Crawl Status (`/dashboard`) | `GET /api/v1/crawls/{id}/status` |
| **WebSocket** | Live Agent Monitor (`/dashboard`) | `WS /api/v1/crawls/{id}/live` |
| **Search API** | Semantic Search Bar (`/dashboard`) | `POST /api/v1/search` |
| **Export API** | OpenAPI / Postman Exporter (`/docs`) | `GET /api/v1/reports/{id}/export` |
