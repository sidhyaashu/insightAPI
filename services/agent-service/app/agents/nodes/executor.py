import asyncio
from typing import Dict, Any
from app.agents.state import CrawlState
from app.engine.executor.dynamic_executor import DynamicRuntimeExecutor
from app.engine.browser.dom_distiller import DOMDistiller
from app.core.compliance import DomainRateLimiter
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("agent.executor")


class ExecutorNode:
    """
    LangGraph execution node that performs UI actions using Playwright,
    re-extracts AXTree DOM snapshots, updates captured network endpoints,
    and handles SPA edge cases (login walls, modal traps, popup captures).
    """
    @classmethod
    async def check_login_wall(cls, page: Any, snapshot: list, state: CrawlState) -> bool:
        """
        Checks if the page is blocked by an unauthenticated login wall.
        If detected, sets state['is_complete'] = True, error_message='auth_required', and auth_required_url=page.url.
        
        Fixes failure mode: Agent wasting tokens attempting blind credential entries or button clicks on login screens.
        """
        if await DOMDistiller.detect_login_wall(page, snapshot):
            logger.warning(f"🔒 Login wall detected on URL: {page.url}. Halting crawl graph with 'auth_required'.")
            state["is_complete"] = True
            state["error_message"] = "auth_required"
            state["auth_required_url"] = page.url
            return True
        return False

    @classmethod
    async def handle_popup_navigation(cls, page: Any, state: CrawlState, action_coro) -> Dict[str, Any]:
        """
        Executes action while monitoring for popup / target="_blank" new tab creation.
        If a new page is opened, attaches NetworkObserver to capture its API traffic,
        waits briefly, closes the popup page, and returns focus to the primary page context.
        
        Fixes failure mode: Planner wandering into popup/new-tab windows and getting stranded.
        """
        observer = state.get("network_observer")
        context = getattr(page, "context", None)
        popup_page = None

        if not context:
            return await action_coro

        def on_popup(p):
            nonlocal popup_page
            popup_page = p

        try:
            context.on("page", on_popup)
        except Exception:
            pass

        try:
            res = await action_coro
            await asyncio.sleep(0.5)

            if popup_page:
                logger.info(f"🌐 Popup / target='_blank' page detected: {getattr(popup_page, 'url', '')}. Capturing traffic and closing.")
                if observer:
                    try:
                        observer.attach_to_page(popup_page)
                    except Exception:
                        pass
                try:
                    await popup_page.wait_for_load_state("networkidle", timeout=2000)
                except Exception:
                    pass
                try:
                    await popup_page.close()
                except Exception:
                    pass
                logger.info("Popup page closed. Restored focus to primary crawling page.")
            return res
        finally:
            try:
                context.remove_listener("page", on_popup)
            except Exception:
                pass

    @classmethod
    async def handle_modal_trap(cls, page: Any, next_action: Dict[str, Any], state: CrawlState) -> None:
        """
        Detects if execution is trapped inside an unyielding modal dialog.
        If 3 consecutive actions inside a modal yield 0 new captured endpoints, force-closes
        the modal via Escape key and backdrop removal, and deprioritizes modal selectors in state.
        
        Fixes failure mode: Agent cycling endlessly on unhelpful modal dialog controls.
        """
        parent_text = (next_action.get("parent_text") or "").lower()
        form_context = (next_action.get("form_context") or "").lower()
        selector = (next_action.get("selector") or "").lower()

        is_in_modal = any(
            kw in parent_text or kw in form_context or kw in selector
            for kw in ["modal", "dialog", "backdrop", "popup", "[role=\"dialog\"]"]
        )

        current_endpoints_count = len(state.get("captured_endpoints") or [])
        last_count = state.get("last_endpoint_count", current_endpoints_count)
        modal_action_count = state.get("modal_action_count", 0)

        if is_in_modal:
            if current_endpoints_count <= last_count:
                modal_action_count += 1
            else:
                modal_action_count = 0

            if modal_action_count >= 3:
                logger.warning("⚠️ Modal trap detected! 3 consecutive actions inside modal yielded no new endpoints. Force-closing modal.")
                try:
                    if hasattr(page, "keyboard"):
                        await page.keyboard.press("Escape")
                    await asyncio.sleep(0.3)
                    if hasattr(page, "evaluate"):
                        await page.evaluate("""
                        () => {
                            const modal = document.querySelector('.modal, dialog, [role="dialog"], .modal-backdrop');
                            if (modal) modal.remove();
                        }
                        """)
                except Exception as e:
                    logger.debug(f"Modal force close error: {e}")

                deprioritized = state.get("deprioritized_modal_selectors") or []
                modal_sel = next_action.get("selector") or "modal"
                if modal_sel not in deprioritized:
                    deprioritized.append(modal_sel)
                state["deprioritized_modal_selectors"] = deprioritized
                modal_action_count = 0
        else:
            modal_action_count = 0

        state["modal_action_count"] = modal_action_count
        state["last_endpoint_count"] = current_endpoints_count

    @classmethod
    async def process(cls, state: CrawlState) -> CrawlState:
        page = state.get("page_ref")
        next_action = state.get("next_action")

        if not page or not next_action:
            logger.info("ExecutorNode: No page or next action available. Marking crawl complete.")
            state["is_complete"] = True
            return state

        # Initial login wall check
        if await cls.check_login_wall(page, state.get("interactive_elements", []), state):
            return state

        # Modal trap check
        await cls.handle_modal_trap(page, next_action, state)

        try:
            # Enforce per-domain rate limiting spacing before execution
            min_delay = state.get("rate_limit_ms") or getattr(settings, "MIN_DOMAIN_DELAY_MS", 500)
            logger.debug(f"Enforcing domain rate limit delay ({min_delay}ms) for host '{page.url}'")
            await DomainRateLimiter.enforce_rate_limit(page.url, min_delay_ms=min_delay)

            # 1. Execute interaction safely (with popup trap handling)
            selector = next_action.get("selector", "")
            action_type = next_action.get("action") or next_action.get("tag") or "click"
            action_value = next_action.get("value") or next_action.get("text") or ""
            url_before = state.get("current_url") or getattr(page, "url", "")
            
            observer = state.get("network_observer")
            endpoints_before_idx = len(observer.captured_endpoints) if observer and hasattr(observer, "captured_endpoints") else len(state.get("captured_endpoints") or [])

            logger.info(f"⚡ Executing action [{action_type}] on selector `{selector}`")
            
            dynamic_executor = DynamicRuntimeExecutor(
                page,
                cost_manager=state.get("cost_manager"),
                humanize=state.get("humanize_interactions"),
            )
            res = await cls.handle_popup_navigation(page, state, dynamic_executor.execute_action(next_action))
            logger.info(f"Action execution status: success={res.get('success')} | message='{res.get('message', '')}'")

            # 2. Wait for page network idle and UI loading indicators to settle
            from app.engine.browser.stabilizer import PageNetworkStabilizer
            await PageNetworkStabilizer.wait_until_stable(page, timeout_ms=10000)

            # 3. Update current URL, visited URLs, and captured endpoints
            current_url = page.url
            state["current_url"] = current_url
            visited_list = state.setdefault("visited_urls", [])
            if current_url not in visited_list:
                visited_list.append(current_url)
                logger.info(f"Explored new URL page state: {current_url}")

            # Check if this was a vision-driven interaction
            is_vision = bool(next_action.get("is_vision_action"))
            if is_vision:
                state["vision_action_count"] = state.get("vision_action_count", 0) + 1

            # Check if this was a form submission interaction
            is_form_submit = (
                next_action.get("is_form_submit")
                or action_type in ["submit"]
                or (next_action.get("tag") in ["button", "input"] and (next_action.get("type") in ["submit"] or next_action.get("form_context")))
            )

            if observer and hasattr(observer, "captured_endpoints"):
                triggered_raw = observer.captured_endpoints[endpoints_before_idx:]
                # Flag newly captured endpoints from this step if vision-driven
                if is_vision:
                    for ep in triggered_raw:
                        if hasattr(ep, "is_vision_derived"):
                            ep.is_vision_derived = True
                        elif isinstance(ep, dict):
                            ep["is_vision_derived"] = True

                # Attribute form submission metadata to triggered endpoints
                if is_form_submit and triggered_raw:
                    form_context = next_action.get("form_context") or ""
                    form_action = next_action.get("form_action") or ""
                    form_method = next_action.get("form_method") or "POST"
                    form_fields = next_action.get("form_fields") or []
                    field_names = [f.get("name") for f in form_fields if isinstance(f, dict) and f.get("name")]
                    submitted_values = res.get("submitted_fields") or next_action.get("submitted_fields") or {}

                    triggered_by_data = {
                        "action_type": "form_submit",
                        "selector": selector,
                        "form_context": form_context,
                        "form_action": form_action,
                        "form_method": form_method,
                        "field_names": field_names,
                        "submitted_fields": submitted_values,
                    }

                    if len(triggered_raw) == 1:
                        primary = triggered_raw[0]
                        if hasattr(primary, "triggered_by"):
                            primary.triggered_by = triggered_by_data
                        elif isinstance(primary, dict):
                            primary["triggered_by"] = triggered_by_data
                    else:
                        def _rank_endpoint(ep):
                            m = (getattr(ep, "method", None) or (ep.get("method") if isinstance(ep, dict) else "")).upper()
                            s = int(getattr(ep, "status", None) or (ep.get("status") if isinstance(ep, dict) else 200))
                            u = getattr(ep, "url", None) or (ep.get("url") if isinstance(ep, dict) else "")
                            score = 0
                            if form_action and form_action in u:
                                score += 50
                            if m in ["POST", "PUT", "PATCH"]:
                                score += 30
                            elif m in ["DELETE"]:
                                score += 20
                            if 200 <= s < 400:
                                score += 15
                            return score

                        sorted_raw = sorted(triggered_raw, key=_rank_endpoint, reverse=True)
                        primary = sorted_raw[0]
                        related = [
                            (ep.to_dict() if hasattr(ep, "to_dict") else ep) for ep in sorted_raw[1:]
                        ]
                        if hasattr(primary, "triggered_by"):
                            primary.triggered_by = triggered_by_data
                            primary.related_calls = related
                        elif isinstance(primary, dict):
                            primary["triggered_by"] = triggered_by_data
                            primary["related_calls"] = related

                state["captured_endpoints"] = [
                    ep.to_dict() if hasattr(ep, "to_dict") else ep for ep in observer.captured_endpoints
                ]
            else:
                triggered_raw = (state.get("captured_endpoints") or [])[endpoints_before_idx:]
                if is_vision:
                    for ep in triggered_raw:
                        if isinstance(ep, dict):
                            ep["is_vision_derived"] = True

                if is_form_submit and triggered_raw:
                    form_context = next_action.get("form_context") or ""
                    form_action = next_action.get("form_action") or ""
                    form_method = next_action.get("form_method") or "POST"
                    form_fields = next_action.get("form_fields") or []
                    field_names = [f.get("name") for f in form_fields if isinstance(f, dict) and f.get("name")]
                    submitted_values = res.get("submitted_fields") or next_action.get("submitted_fields") or {}

                    triggered_by_data = {
                        "action_type": "form_submit",
                        "selector": selector,
                        "form_context": form_context,
                        "form_action": form_action,
                        "form_method": form_method,
                        "field_names": field_names,
                        "submitted_fields": submitted_values,
                    }

                    if len(triggered_raw) == 1:
                        if isinstance(triggered_raw[0], dict):
                            triggered_raw[0]["triggered_by"] = triggered_by_data
                    else:
                        def _rank_dict(ep):
                            m = str(ep.get("method", "")).upper()
                            s = int(ep.get("status", 200))
                            u = str(ep.get("url", ""))
                            score = 0
                            if form_action and form_action in u:
                                score += 50
                            if m in ["POST", "PUT", "PATCH"]:
                                score += 30
                            if 200 <= s < 400:
                                score += 15
                            return score

                        sorted_raw = sorted(triggered_raw, key=_rank_dict, reverse=True)
                        sorted_raw[0]["triggered_by"] = triggered_by_data
                        sorted_raw[0]["related_calls"] = sorted_raw[1:]

            network_calls_triggered = [
                ep.to_dict() if hasattr(ep, "to_dict") else ep for ep in triggered_raw
            ]

            # Record ordered action trace item
            traces = state.get("action_traces")
            if traces is None:
                traces = []
            trace_item = {
                "step": len(traces) + 1,
                "action_type": action_type,
                "selector": selector,
                "value": action_value,
                "url_before": url_before,
                "url_after": current_url,
                "network_calls_triggered": network_calls_triggered,
                "is_vision_action": is_vision,
            }
            if is_vision and next_action.get("coordinates"):
                trace_item["coordinates"] = next_action["coordinates"]
            if is_vision and next_action.get("mark"):
                trace_item["mark"] = next_action["mark"]

            traces.append(trace_item)
            state["action_traces"] = traces

            # 4. Re-extract updated interactive AXTree snapshot
            snapshot = await DOMDistiller.extract_interactive_snapshot(
                page,
                goal=state.get("goal"),
                cost_manager=state.get("cost_manager"),
            )
            state["interactive_elements"] = snapshot
            logger.info(f"Re-extracted interactive AXTree snapshot: {len(snapshot)} elements remaining.")

            # Post-navigation login wall check
            if await cls.check_login_wall(page, snapshot, state):
                return state

            # 5. Record yield & update StagnationDetector
            from app.engine.browser.stagnation_detector import StagnationDetector
            endpoints_before = state.get("last_endpoint_count", 0)
            endpoints_after = len(state.get("captured_endpoints") or [])
            state = StagnationDetector.record_action_yield(state, endpoints_before, endpoints_after, current_url)

            if state.get("zero_yield_streak", 0) >= StagnationDetector.ZERO_YIELD_STREAK_THRESHOLD:
                await StagnationDetector.force_unstick(page)

            # 6. Increment explored page counter
            explored_count = state.get("explored_count", 0) + 1
            state["explored_count"] = explored_count

            # 7. Check max pages termination limit
            max_pages = state.get("max_pages", 10)
            if explored_count >= max_pages:
                logger.info(f"Reached max page exploration limit ({explored_count}/{max_pages}). Marking crawl complete.")
                state["is_complete"] = True

        except Exception as e:
            logger.error(f"ExecutorNode failure executing action `{next_action.get('selector')}`: {e}", exc_info=True)
            state["is_complete"] = True

        return state
