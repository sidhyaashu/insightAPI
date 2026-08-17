"""Semantic Form & Dynamic Contextual Input Injector."""
from __future__ import annotations

import re
import random
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

SEARCH_TERMS = ["test", "api", "order", "product", "item", "analytics", "dashboard"]


def get_contextual_value_for_input(input_info: Dict[str, str]) -> str:
    """Generate realistic dummy data based on input semantic attributes."""
    input_type = (input_info.get("type") or "text").lower()
    name = (input_info.get("name") or "").lower()
    placeholder = (input_info.get("placeholder") or "").lower()
    label = (input_info.get("label") or "").lower()
    combined = f"{name} {placeholder} {label} {input_type}"

    # 1. Email inputs
    if input_type == "email" or "email" in combined or "e-mail" in combined:
        return "qa.tester@insightapi.ai"

    # 2. Date inputs
    if input_type == "date" or "date" in combined or "birth" in combined:
        return datetime.now().strftime("%Y-%m-%d")

    # 3. Search queries
    if input_type == "search" or "search" in combined or "query" in combined or "keyword" in combined:
        return random.choice(SEARCH_TERMS)

    # 4. Password inputs
    if input_type == "password" or "pass" in combined:
        return "TestPassword123!"

    # 5. Number / Quantity / Age inputs
    if input_type == "number" or "qty" in combined or "quantity" in combined or "count" in combined:
        return "1"
    if "age" in combined or "year" in combined:
        return "25"
    if "price" in combined or "amount" in combined:
        return "100"

    # 6. Phone / Mobile inputs
    if input_type == "tel" or "phone" in combined or "mobile" in combined:
        return "+1-555-019-2834"

    # 7. Name fields
    if "first_name" in combined or "fname" in combined:
        return "Alex"
    if "last_name" in combined or "lname" in combined:
        return "Morgan"
    if "name" in combined or "user" in combined:
        return "Alex Morgan"

    # 8. Address / City / Zip
    if "city" in combined:
        return "San Francisco"
    if "zip" in combined or "postal" in combined:
        return "94105"
    if "address" in combined or "street" in combined:
        return "100 Market Street"

    # Default general text
    return "InsightAPI Test Value"


async def fill_page_forms(page: Any, max_forms: int = 3) -> List[Dict[str, Any]]:
    """
    Find forms on the page, contextually populate inputs, and submit them
    to discover live background API endpoints.
    """
    filled_forms: List[Dict[str, Any]] = []

    try:
        forms = await page.query_selector_all("form")
        for form_idx, form in enumerate(forms[:max_forms]):
            inputs = await form.query_selector_all("input:not([type='hidden']):not([type='submit']), textarea")
            form_data: Dict[str, str] = {}

            for inp in inputs:
                try:
                    if not await inp.is_visible():
                        continue

                    input_type = (await inp.get_attribute("type")) or "text"
                    name = (await inp.get_attribute("name")) or ""
                    placeholder = (await inp.get_attribute("placeholder")) or ""
                    aria_label = (await inp.get_attribute("aria-label")) or ""

                    val = get_contextual_value_for_input({
                        "type": input_type,
                        "name": name,
                        "placeholder": placeholder,
                        "label": aria_label,
                    })

                    # Handle checkboxes and radio buttons
                    if input_type in ("checkbox", "radio"):
                        await inp.check(timeout=1000)
                        form_data[name or "option"] = "checked"
                    else:
                        await inp.fill(val, timeout=1000)
                        form_data[name or placeholder or "input"] = val

                except Exception:
                    continue

            # Select first non-empty option in dropdowns
            selects = await form.query_selector_all("select")
            for sel in selects:
                try:
                    if not await sel.is_visible():
                        continue
                    options = await sel.query_selector_all("option")
                    for opt in options:
                        opt_val = await opt.get_attribute("value")
                        if opt_val and opt_val.strip():
                            await sel.select_option(value=opt_val, timeout=1000)
                            form_data["select"] = opt_val
                            break
                except Exception:
                    continue

            # Submit the form if populated
            if form_data:
                submit_btn = await form.query_selector("button[type='submit'], input[type='submit'], button:has-text('Search'), button:has-text('Submit'), button:has-text('Apply')")
                if submit_btn and await submit_btn.is_visible():
                    try:
                        await submit_btn.click(timeout=1500)
                        await page.wait_for_timeout(800)  # allow AJAX call to trigger
                    except Exception:
                        pass

                filled_forms.append({
                    "form_index": form_idx + 1,
                    "fields_populated": form_data,
                })

    except Exception as e:
        logger.debug(f"Form filling notice: {e}")

    return filled_forms
