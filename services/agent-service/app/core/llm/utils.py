"""
utils.py — Text extraction, JSON cleanup, and formatting resilience for LLM outputs.
"""
from __future__ import annotations

import re
from typing import Any


def extract_text_content(content: Any) -> str:
    """
    Safely extracts plain text string from any LLM response or message content.
    Handles:
    - Plain string (ChatOpenAI, AzureChatOpenAI)
    - List of dicts/blocks (ChatGoogleGenerativeAI: [{'type': 'text', 'text': ...}])
    - Objects with .content attribute (AIMessage, BaseMessage, ChatGenerationChunk)
    - Fallback str conversion
    """
    if content is None:
        return ""
    if hasattr(content, "content"):
        content = content.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    parts.append(str(item["text"]))
                elif "text" in item:
                    parts.append(str(item["text"]))
                else:
                    parts.append(str(item))
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


def repair_json_string(raw_text: Any) -> str:
    """
    Cleans and repairs common JSON formatting issues in raw LLM outputs:
    - Extracts text if given an AIMessage/dict list
    - Strips markdown code fences (```json ... ```)
    - Removes trailing commas before closing brackets/braces
    - Strips leading/trailing non-JSON commentary
    """
    if raw_text is None:
        return "{}"
    if not isinstance(raw_text, str):
        raw_text = extract_text_content(raw_text)

    text = raw_text.strip()
    # 1. Strip markdown fences
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # 2. Extract first JSON array or object
    obj_match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if obj_match:
        text = obj_match.group(1).strip()

    # 3. Remove trailing commas before } or ]
    text = re.sub(r",\s*([\}\]])", r"\1", text)
    return text
