# InsightAPI AI — Backend Core & CLI Engine

InsightAPI AI is an Agentic Web API Intelligence Platform that autonomously explores web applications, observes network traffic, analyzes API behavior, infers endpoint relationships, and generates structured OpenAPI/Postman documentation.

## CLI Usage

```bash
# Install locally in editable mode
pip install -e .

# Run CLI
insightapi crawl https://example.com --max-pages 10
insightapi list-endpoints <session_id>
insightapi export --session-id <id> --format openapi --output ./openapi.json
```

## Running Backend Server

```bash
uvicorn app.main:app --reload --port 8000
```
