**InsightAPI AI** is designed with a **Triple Distribution Model** so you can run it via **Docker Compose**, **CLI**, or **Python SDK** simultaneously.

Here are all the ways to run and manually test your pipeline:

---

### 1. 🖥️ Way 1: Typer CLI (Direct Terminal Execution)
You can run autonomous crawls directly from your command line without starting the web server.

```bash
# Run autonomous crawl on any web app from CLI
python -m app.cli.main crawl https://httpbin.org --max-pages 5

# Check version
python -m app.cli.main version
```
* **Output**: Writes logs to `logs/insightapi.log` and outputs formatted OpenAPI/Postman specs directly to your terminal or target files.

---

### 2. 🐳 Way 2: Docker Compose + FastAPI REST Service
Launch the full backend stack (PostgreSQL + pgvector + Redis + FastAPI Server):

#### A. Start Docker Services
```bash
docker compose up -d
```

#### B. Test via Interactive Swagger UI
Open your browser to: **`http://localhost:8000/docs`**

#### C. Test via `curl` / HTTP Client
```bash
# 1. Start an autonomous crawl session
curl -X POST "http://localhost:8000/api/v1/crawls/start" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://httpbin.org", "max_pages": 5}'

# Response -> {"session_id": "YOUR_SESSION_ID", "status": "running", "target_url": "https://httpbin.org"}

# 2. Check session status and captured endpoints
curl "http://localhost:8000/api/v1/crawls/YOUR_SESSION_ID/status"

# 3. Export generated OpenAPI documentation
curl "http://localhost:8000/api/v1/reports/YOUR_SESSION_ID/export?format=openapi"
```

---

### 3. 🐍 Way 3: Python SDK (Embeddable Library)
Import `AgentEngine` directly into any Python script, CI/CD pipeline, or Jupyter Notebook:

```python
import asyncio
from app.sdk import AgentEngine

async def main():
    # Zero-dependency lightweight mode
    engine = AgentEngine(headless=True)
    result = await engine.crawl("https://httpbin.org", max_pages=5)
    
    # Print generated OpenAPI spec
    print(result.to_openapi())

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 🔐 Crawling Authenticated Apps

InsightAPI never stores credentials. Use the two-step session-file flow:

#### Step 1 — Capture your login session

```bash
# Opens a real (visible) browser window so you can log in manually
python -m app.cli.main login https://app.example.com --output session.json
```

Log in, then press **Enter** in the terminal. The session (cookies + localStorage) is saved to
`session.json`. Treat this file like a password — never commit it to version control.

#### Step 2 — Run an authenticated crawl

```bash
# CLI
python -m app.cli.main crawl https://app.example.com --session-file session.json --max-pages 10

# Or inside Docker container
docker exec -it insightapi_backend \
  python -m app.cli.main crawl https://app.example.com --session-file /path/to/session.json
```

#### Python SDK

```python
import asyncio, json
from app.sdk import AgentEngine

async def main():
    with open("session.json") as f:
        session = json.load(f)

    engine = AgentEngine(headless=True)
    result = await engine.crawl(
        "https://app.example.com",
        max_pages=10,
        session_state=session,   # injected into the Playwright browser context only
    )
    print(result.to_openapi())

asyncio.run(main())
```

#### REST API

```bash
curl -X POST "http://localhost:8000/api/v1/crawls/start" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://app.example.com",
       "max_pages": 10,
       "session_state": { "cookies": [...], "origins": [...] }
     }'
```

> `session_state` is forwarded to the Playwright context only. It is **never** stored in crawl
> session records, logs, or exported OpenAPI/Postman/Markdown output.

---

### 4. ⚡ Way 4: CLI inside Running Docker Container
If your Docker services are running, you can execute the CLI engine directly inside the backend container:

```bash
docker exec -it insightapi_backend python -m app.cli.main crawl https://httpbin.org --max-pages 5
```

---

### Summary Recommendation for Testing
1. **Quickest Local Test**: Run **Way 1** (`python -m app.cli.main crawl https://httpbin.org --max-pages 3`).
2. **Full Infrastructure Test**: Run **Way 2** (`docker compose up -d`) and open `http://localhost:8000/docs`.