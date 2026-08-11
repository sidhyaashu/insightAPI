import asyncio
import logging
import traceback
from typing import Dict, Any, Optional, Union
from playwright.async_api import Page

logger = logging.getLogger(__name__)

COMMON_OVERLAY_SELECTORS = [
    "button:has-text('Accept')",
    "button:has-text('Accept All')",
    "button:has-text('Allow')",
    "button:has-text('Close')",
    "button:has-text('Got it')",
    ".cookie-banner button",
    "[aria-label='Close']"
]


class FormDummyInjector:
    """
    Infers form field intent from element metadata (name, placeholder, type, ariaLabel)
    and resolves plausible dummy data to populate form inputs.
    Used as a fallback when LLMFormInjector is disabled or unavailable.
    """
    @staticmethod
    def get_dummy_value(element_meta: Dict[str, Any]) -> str:
        name = (element_meta.get("name") or "").lower()
        placeholder = (element_meta.get("placeholder") or "").lower()
        input_type = (element_meta.get("type") or "").lower()
        aria_label = (element_meta.get("ariaLabel") or "").lower()
        text = (element_meta.get("text") or "").lower()

        combined = f"{name} {placeholder} {input_type} {aria_label} {text}"

        import re
        if re.search(r"\b(search|query|filter)\b", combined) or name == "q":
            return "test search"
        if re.search(r"\b(email|mail)\b", combined):
            return "user@example.com"
        if re.search(r"\b(date|time|year|month)\b", combined):
            return "2026-01-01"
        if re.search(r"\b(num|number|count|amount|price|qty|quantity|zip)\b", combined):
            return "10"
        if re.search(r"\b(name|user|username)\b", combined):
            return "John Doe"

        return "sample input"


class LLMFormInjector:
    """
    Uses an LLM to generate contextually-aware form field values in a single
    batched call per form, producing realistic inputs that are far more likely
    to trigger meaningful API calls than keyword-matched dummy values.

    A flight search form gets ``origin: JFK, destination: LAX``.
    A product filter gets ``category: electronics, min_price: 100``.

    Falls back to ``FormDummyInjector`` when:
    - ``settings.LLM_SMART_FORM_ENABLED`` is False
    - Token budget is exhausted
    - LLM call raises an exception

    Caches results per (form_context_hash) to avoid re-calling on the same form.
    """
    # Class-level cache: form_context_hash -> {selector: value}
    _cache: Dict[str, Dict[str, str]] = {}

    @classmethod
    def _form_cache_key(cls, action: Dict[str, Any]) -> str:
        import hashlib
        key_parts = [
            action.get("form_context", ""),
            action.get("selector", ""),
            action.get("placeholder", ""),
            action.get("ariaLabel", ""),
        ]
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

    @classmethod
    async def get_value(
        cls,
        action: Dict[str, Any],
        page_context: str = "",
        cost_manager=None,
    ) -> str:
        """
        Returns a contextually appropriate value for the given form input element.

        Parameters
        ----------
        action       : Interactive element dict from DOMDistiller.
        page_context : Optional string summarising page title / section heading.
        cost_manager : LLMCostManager for budget enforcement and caching.
        """
        from app.core.config import settings

        if not settings.LLM_SMART_FORM_ENABLED:
            return FormDummyInjector.get_dummy_value(action)

        if cost_manager and cost_manager.is_budget_exhausted():
            return FormDummyInjector.get_dummy_value(action)

        # Class-level cache hit
        cache_key = cls._form_cache_key(action)
        if cache_key in cls._cache:
            selector = action.get("selector", "")
            cached_val = cls._cache[cache_key].get(selector)
            if cached_val:
                return cached_val

        prompt = (
            f"You are filling out a web form to trigger API calls for testing purposes.\n"
            f"Page context: {page_context or 'unknown'}\n"
            f"Form context: {action.get('form_context', 'unknown')}\n"
            f"Field details:\n"
            f"  - name/id: {action.get('name') or action.get('selector', '')}\n"
            f"  - placeholder: {action.get('placeholder', '')}\n"
            f"  - type: {action.get('type', 'text')}\n"
            f"  - aria-label: {action.get('ariaLabel', '')}\n"
            f"  - visible text: {action.get('text', '')}\n\n"
            "What is a realistic, plausible value to enter in this field?\n"
            "Respond with ONLY the value string, nothing else. No quotes."
        )

        try:
            from app.agents.nodes.llm_client import get_llm, ModelTier
            llm = get_llm(ModelTier.FAST)
            response = await llm.ainvoke(prompt)
            value = (response.content if hasattr(response, "content") else str(response)).strip()

            tokens_est = (len(prompt) + len(value)) // 4
            if cost_manager:
                from app.core.config import settings as s
                model_name = s.AZURE_OPENAI_DEPLOYMENT_FAST if s.AZURE_OPENAI_ENDPOINT else s.OPENAI_MODEL_FAST
                cost_manager.record_usage(tokens_est, model_name)

            # Cache per form context
            cls._cache[cache_key] = {action.get("selector", ""): value}
            return value if value else FormDummyInjector.get_dummy_value(action)

        except Exception as e:
            logger.warning(f"LLMFormInjector failed ({type(e).__name__}: {e}). Using keyword fallback.")
            return FormDummyInjector.get_dummy_value(action)



class DynamicRuntimeExecutor:
    """
    Executes browser UI actions safely using a structured action interpreter,
    auto-dismisses blocking overlays, and injects realistic form dummy inputs.
    Uses LLMFormInjector for smarter context-aware form filling when enabled.
    """
    def __init__(self, page: Page, cost_manager=None):
        self.page = page
        self.cost_manager = cost_manager

    async def dismiss_interstitials(self, timeout_ms: int = 1000):
        """
        Checks for and dismisses blocking cookie banners, dialog overlays, and modals.
        """
        for sel in COMMON_OVERLAY_SELECTORS:
            try:
                btn = self.page.locator(sel).first
                if await btn.is_visible(timeout=timeout_ms):
                    await btn.click(timeout=timeout_ms)
                    logger.info(f"Dismissed blocking overlay using selector '{sel}'")
                    break
            except Exception:
                continue

    async def execute_action(self, action: Dict[str, Any], timeout_ms: int = 10000) -> Dict[str, Any]:
        """
        Executes a structured action dictionary or selector against the Playwright page.
        """
        if not action:
            return {"success": False, "result": None, "error": "No action specified."}

        # 1. Pre-action check: Auto-dismiss overlays/interstitials
        await self.dismiss_interstitials(timeout_ms=1000)

        selector = action.get("selector")
        action_type = (action.get("action") or "click").lower()

        if not selector:
            text = action.get("text")
            if text:
                selector = f"text={text}"
            else:
                return {"success": False, "result": None, "error": "Action target selector missing."}

        tag = (action.get("tag") or "").lower()
        input_type = (action.get("type") or action.get("inputType") or "").lower()

        try:
            if input_type in ["radio", "checkbox"]:
                try:
                    await self.page.check(selector, timeout=timeout_ms)
                except Exception:
                    # Self-healing fallback for styled hidden/covered radio/checkbox inputs
                    await self.page.click(selector, force=True, timeout=timeout_ms)
            elif input_type in ["button", "submit"] or action_type == "click":
                try:
                    await self.page.click(selector, timeout=timeout_ms)
                except Exception:
                    await self.page.click(selector, force=True, timeout=timeout_ms)
            elif action_type == "type" or tag in ["textarea"] or (tag == "input" and input_type not in ["radio", "checkbox", "button", "submit"]):
                # Use LLMFormInjector for smarter context-aware values; fallback to keyword heuristic
                text_to_type = action.get("text")
                if not text_to_type:
                    try:
                        page_context = ""
                        try:
                            page_context = await self.page.title()
                        except Exception:
                            pass
                        text_to_type = await LLMFormInjector.get_value(
                            action,
                            page_context=page_context,
                            cost_manager=self.cost_manager,
                        )
                    except Exception:
                        text_to_type = FormDummyInjector.get_dummy_value(action)
                try:
                    await self.page.fill(selector, text_to_type, timeout=timeout_ms)
                except Exception:
                    await self.page.fill(selector, text_to_type, force=True, timeout=timeout_ms)

                # Check if input is inside a form or search box with a submit button — auto-trigger submit & verify
                try:
                    form_context = (action.get("form_context") or "").lower()
                    if any(kw in form_context or kw in selector for kw in ["search", "filter", "form", "q", "query"]):
                        # Try pressing Enter or clicking associated submit button
                        await self.page.press(selector, "Enter", timeout=1000)
                        from app.engine.browser.stabilizer import PageNetworkStabilizer
                        await PageNetworkStabilizer.wait_until_stable(self.page, timeout_ms=5000)
                except Exception:
                    pass
            elif action_type == "select" or tag == "select":
                val = action.get("value") or action.get("text")
                try:
                    if val:
                        await self.page.select_option(selector, value=val, timeout=timeout_ms)
                    else:
                        await self.page.select_option(selector, index=0, timeout=timeout_ms)
                except Exception:
                    await self.page.select_option(selector, index=0, timeout=timeout_ms)
            elif action_type == "hover":
                await self.page.hover(selector, timeout=timeout_ms)
            elif action_type == "press":
                key = action.get("key", "Enter")
                await self.page.press(selector, key, timeout=timeout_ms)
            else:
                try:
                    await self.page.click(selector, timeout=timeout_ms)
                except Exception:
                    await self.page.click(selector, force=True, timeout=timeout_ms)

            return {"success": True, "result": f"Executed {action_type} on {selector}", "error": None}

        except Exception as e:
            error_trace = f"{type(e).__name__}: {str(e)}"
            logger.warning(f"Dynamic action execution failed on '{selector}': {error_trace}")
            return {"success": False, "result": None, "error": error_trace}
