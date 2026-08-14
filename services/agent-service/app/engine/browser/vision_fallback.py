"""
vision_fallback.py — GPT-4o Vision Fallback for Complex UI Understanding

Design
------
When DOMDistiller's AXTree extraction returns fewer than VISION_FALLBACK_THRESHOLD
interactive elements (e.g. Canvas UIs, custom web components, obfuscated SPAs),
this fallback takes a page screenshot and calls ModelTier.VISION (gpt-4o-mini).

It asks the Vision LLM to visually analyze the page and identify clickable / interactive
elements, returning them as element descriptors compatible with DOMDistiller.
"""
from __future__ import annotations

import base64
import json
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import Page

from app.core.config import settings

logger = logging.getLogger("agent.vision")


class VisionFallback:
    """
    Vision-powered UI element extractor using GPT-4o Vision (gpt-4o-mini).
    Activated when accessible DOM extraction yields fewer than VISION_FALLBACK_THRESHOLD elements.
    """

    @classmethod
    async def extract_with_fallback(
        cls,
        page: Page,
        snapshot: List[Dict[str, Any]],
        goal: Optional[str] = None,
        cost_manager: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates snapshot length against threshold. If below, triggers Vision model analysis.

        Parameters
        ----------
        page         : Live Playwright Page reference.
        snapshot     : Initial AXTree element list from DOMDistiller.
        goal         : Optional crawl goal for target-focused vision prompt.
        cost_manager : LLMCostManager for budget enforcement and metrics.

        Returns
        -------
        Snapshot list (augmented with vision-detected elements if fallback fired).
        """
        threshold = settings.VISION_FALLBACK_THRESHOLD
        if len(snapshot) >= threshold or not settings.LLM_VISION_FALLBACK_ENABLED:
            return snapshot

        if cost_manager and cost_manager.is_budget_exhausted():
            logger.info("VisionFallback: Token budget exhausted. Skipping vision fallback.")
            return snapshot

        logger.info(
            f"👁️ VisionFallback Triggered! AXTree extracted only {len(snapshot)} elements "
            f"(threshold={threshold}). Capturing screenshot for Vision LLM analysis."
        )

        try:
            # 1. Capture PNG screenshot bytes
            screenshot_bytes = await page.screenshot(type="png", full_page=False)
            b64_image = base64.b64encode(screenshot_bytes).decode("utf-8")
            data_url = f"data:image/png;base64,{b64_image}"

            # 2. Build Vision Prompt
            page_title = ""
            try:
                page_title = await page.title()
            except Exception:
                pass

            prompt_text = (
                f"You are a web automation agent analyzing a webpage that has sparse/canvas/custom DOM controls.\n"
                f"Page title: '{page_title}' | Goal: '{goal or 'Discover API endpoints'}'\n\n"
                "Examine the screenshot and list all visible interactive elements (buttons, search inputs, tabs, dropdowns, navigation links, filters).\n"
                "For each element, respond with a JSON object containing:\n"
                "  - \"text\": visible text label or icon description\n"
                "  - \"tag\": element type (button, input, link, tab, select)\n"
                "  - \"role\": accessible role (button, searchbox, link, tab)\n"
                "  - \"selector\": CSS selector or text-based locator (e.g. \"button:has-text('Search')\", \"a:has-text('Products')\", \"input[placeholder*='search']\")\n\n"
                "Respond ONLY with a JSON array of up to 10 element objects.\n"
                'Example: [{"text": "Search Products", "tag": "button", "role": "button", "selector": "button:has-text(\'Search Products\')"}]'
            )

            # 3. Call Vision Model via ModelRouter
            from langchain_core.messages import HumanMessage
            from app.agents.nodes.llm_client import get_llm, ModelTier, ModelRouter, extract_text_content, repair_json_string

            llm = get_llm(ModelTier.VISION)
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            )

            response = await llm.ainvoke([message])
            response_text = extract_text_content(response)

            # Record token usage (approximate for vision: ~1000 tokens per image + prompt)
            tokens_est = 1200 + len(prompt_text) // 4
            if cost_manager:
                model_name = ModelRouter.get_model_name(ModelTier.VISION)
                cost_manager.record_usage(tokens_est, model_name)

            # 4. Parse Vision Elements
            clean = repair_json_string(response_text)
            vision_items = json.loads(clean)

            added_count = 0
            existing_selectors = {el.get("selector") for el in snapshot if el.get("selector")}

            for i, v_el in enumerate(vision_items):
                sel = v_el.get("selector") or f"text={v_el.get('text', '')}"
                if sel in existing_selectors:
                    continue

                vision_element = {
                    "id": 9000 + i,
                    "tag": v_el.get("tag", "button"),
                    "text": v_el.get("text", "")[:80],
                    "type": "text" if v_el.get("tag") == "input" else "",
                    "role": v_el.get("role", "button"),
                    "placeholder": v_el.get("text", ""),
                    "ariaLabel": v_el.get("text", ""),
                    "selector": sel,
                    "form_context": "vision_detected",
                    "parent_text": "vision_detected",
                    "source": "vision_fallback",
                }
                snapshot.append(vision_element)
                existing_selectors.add(sel)
                added_count += 1

            logger.info(f"👁️ VisionFallback added {added_count} visual UI controls to snapshot.")

        except Exception as e:
            logger.warning(f"VisionFallback execution failed ({type(e).__name__}: {e}). Using original snapshot.")

        return snapshot
