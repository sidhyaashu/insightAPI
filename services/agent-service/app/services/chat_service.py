"""LLM chat service for the AI chatbot (merged into agent-service)."""
from __future__ import annotations

import logging
from typing import AsyncIterator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are InsightBot, an AI assistant embedded in InsightAPI AI — an Agentic Web API Intelligence Platform.

You help users understand their API crawl results, interpret OpenAPI specs, explain discovered endpoints, 
suggest next steps, and answer questions about API documentation and integration patterns.

When a user asks about their crawl results, you have access to their session context provided in the conversation.
Be concise, technical, and helpful. Format code examples in markdown."""


def _build_langchain_client():
    """Build LangChain chat client using Gemini, Azure, or standard OpenAI based on config."""
    from app.agents.nodes.llm_client import ModelRouter, ModelTier

    provider = ModelRouter.get_provider()

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL_SMART,
            google_api_key=settings.GEMINI_API_KEY,
            streaming=True,
            temperature=0.7,
        )
    elif provider == "azure":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_SMART or settings.AZURE_OPENAI_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            api_key=settings.AZURE_OPENAI_API_KEY,
            streaming=True,
            temperature=0.7,
        )
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL_SMART,
        streaming=True,
        temperature=0.7,
    )


async def stream_chat_response(
    history: list[dict],
    user_message: str,
    crawl_context: str | None = None,
) -> AsyncIterator[str]:
    """
    Stream LLM chat tokens for a user message given history.

    Args:
        history: List of {"role": "user"|"assistant", "content": "..."} dicts (from DB).
        user_message: The new user message to respond to.
        crawl_context: Optional context string about the user's last crawl session.

    Yields:
        Token strings as the LLM generates the response.
    """
    client = _build_langchain_client()

    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    if crawl_context:
        messages.append(SystemMessage(content=f"[User's crawl context]\n{crawl_context}"))

    for msg in history[-20:]:   # keep last 20 messages in context window
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    try:
        from app.agents.nodes.llm_client import extract_text_content

        async for chunk in client.astream(messages):
            token = extract_text_content(chunk.content if hasattr(chunk, "content") else chunk)
            if token:
                yield token
    except Exception as e:
        logger.error(f"Chat LLM streaming error: {e}")
        yield f"\n\n[Error: {str(e)}]"
