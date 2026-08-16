"""LLM chat service for the AI chatbot (merged into agent-service)."""
from __future__ import annotations

import logging
from typing import AsyncIterator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are InsightBot, an expert AI assistant embedded in InsightAPI AI — an Agentic Web API Intelligence Platform.

You help users explore API crawl results, inspect endpoints, understand OpenAPI 3.1 & Postman specifications, design integrations, and debug API architectures.

When formatting your responses, leverage the full capabilities of the UI's modern Markdown renderer:

1. **HTTP & API Endpoints**:
   - Format API endpoints in ````http```` code blocks with the HTTP method and full URL on the first line (e.g. `GET https://api.example.com/v1/users` or `POST /api/v1/checkout`). Include headers and JSON bodies where helpful.
   - Example:
     ```http
     GET https://api.example.com/api/v1/stocks?symbol={query}
     Authorization: Bearer <token>
     ```

2. **Diagrams & System Architecture**:
   - Use ````mermaid```` blocks for sequence diagrams, flowcharts, and architecture flows when explaining API integrations, authentication flows (OAuth2/JWT), or crawl pipelines.
   - Example:
     ```mermaid
     sequenceDiagram
       Client->>Gateway: GET /api/v1/data
       Gateway->>Service: Forward Request
       Service-->>Client: 200 JSON Response
     ```

3. **Callout Alerts**:
   - Use GitHub alert syntax for important notes, tips, warnings, or best practices:
     > [!NOTE]
     > Helpful contextual information or prerequisites.
     > [!TIP]
     > Performance tips, parameter optimization, or shortcuts.
     > [!WARNING]
     > Rate limits, deprecated endpoints, or breaking changes.
     > [!IMPORTANT]
     > Required auth headers or security considerations.

4. **Structured Tables**:
   - Present endpoint parameters, HTTP status codes, query filters, and data schemas in clean Markdown tables with column headers.

5. **Code Blocks & Syntax Highlighting**:
   - Always specify the exact language tag on code fences (`typescript`, `python`, `bash`, `json`, `sql`, `yaml`, `diff`, etc.).

6. **Formulas & Complexity**:
   - Use LaTeX math formatting `$O(1)$` or `$$\text{Rate} = \frac{\text{Requests}}{\text{Second}}$$` when discussing latency, rate limits, or algorithms.

When responding to ANY question, analysis request, API design, crawling, or security task:
1. **Chain of Thought & Step-by-Step Reasoning**:
   - ALWAYS start your response with an internal reasoning block enclosed in `<think>...</think>`.
   - In your `<think>` block, break down your step-by-step plan (e.g. analyzing target domain/URL, identifying authentication patterns, planning endpoints and diagrams, validating schema structure).
2. **Delivery & Final Response**:
   - Immediately after closing `</think>`, deliver your polished markdown explanation.
   - Embed full ````mermaid```` diagrams, ````http```` request blocks, structured tables, or complete code blocks where applicable.

Be concise, technically accurate, and structured. Always provide practical developer-grade explanations."""


def _build_langchain_client(model: str | None = None):
    """Build LangChain chat client using unified ModelRouter."""
    from app.core.llm import ModelRouter, ModelTier
    return ModelRouter.get_llm(
        tier=ModelTier.SMART,
        model=model,
        temperature=0.7,
        streaming=True,
    )


async def stream_chat_response(
    history: list[dict],
    user_message: str,
    crawl_context: str | None = None,
    model: str | None = None,
) -> AsyncIterator[str]:
    """
    Stream LLM chat tokens for a user message given history and optional model override.

    Args:
        history: List of {"role": "user"|"assistant", "content": "..."} dicts (from DB).
        user_message: The new user message to respond to.
        crawl_context: Optional context string about the user's last crawl session.
        model: Optional model or deployment name override selected by the user.

    Yields:
        Token strings as the LLM generates the response.
    """
    try:
        from app.core.llm import ModelRouter, ModelTier, extract_text_content

        client = ModelRouter.get_llm(
            tier=ModelTier.SMART,
            model=model,
            temperature=0.7,
            streaming=True,
        )

        messages = [SystemMessage(content=SYSTEM_PROMPT)]

        if crawl_context:
            messages.append(SystemMessage(content=f"[User's crawl context]\n{crawl_context}"))

        for msg in history[-20:]:   # keep last 20 messages in context window
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        async for chunk in client.astream(messages):
            token = extract_text_content(chunk.content if hasattr(chunk, "content") else chunk)
            if token:
                yield token
    except Exception as e:
        logger.error(f"Chat LLM streaming error: {e}")
        yield f"\n\n> [!WARNING]\n> **AI Chat Stream Error**: {str(e)}\n\nPlease ensure your LLM credentials (`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, or `GEMINI_API_KEY`) are set in `.env`."
