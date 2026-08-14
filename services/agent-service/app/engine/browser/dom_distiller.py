from typing import List, Dict, Any, Optional
from playwright.async_api import Page


JS_DOM_DISTILLER = r"""
() => {
    function getCssSelector(el) {
        if (el.id && typeof el.id === 'string' && !/\s/.test(el.id)) return '#' + CSS.escape(el.id);
        if (el.getAttribute && el.getAttribute('name')) return `${el.tagName.toLowerCase()}[name="${el.getAttribute('name')}"]`;
        
        const classNameStr = (typeof el.className === 'string') ? el.className : (el.className && el.className.baseVal) || '';
        if (classNameStr && typeof classNameStr === 'string') {
            const classes = classNameStr.trim().split(/\s+/).filter(c => c && !c.includes(':') && !c.includes('[')).slice(0, 2).join('.');
            if (classes) return `${el.tagName.toLowerCase()}.${classes}`;
        }
        return el.tagName.toLowerCase();
    }

    const interactiveSelectors = 'a, button, input, select, textarea, [role="button"], [role="link"], [role="option"], [role="menuitem"], [role="combobox"], [role="searchbox"], [role="tab"], [onclick], [tabindex]';
    const items = [];
    let idCounter = 0;

    function processNode(root) {
        if (!root) return;
        const elements = Array.from(root.querySelectorAll(interactiveSelectors));

        for (const el of elements) {
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
                continue;
            }

            let text = (
                el.innerText || 
                el.textContent ||
                el.value || 
                el.placeholder || 
                el.getAttribute('aria-label') || 
                el.getAttribute('title') || 
                el.getAttribute('alt') || ''
            ).trim().replace(/\s+/g, ' ');

            if (!text) {
                const svg = el.querySelector('svg');
                if (svg) {
                    text = (svg.getAttribute('aria-label') || svg.getAttribute('title') || svg.querySelector('title')?.textContent || '').trim();
                }
            }

            if (!text && el.tagName.toLowerCase() !== 'input') {
                continue;
            }

            // Extract surrounding parent form & section context for risk analysis and API attribution
            const closestForm = el.closest('form, [data-form], .form, fieldset');
            const formContext = closestForm ? (closestForm.getAttribute('aria-label') || closestForm.name || closestForm.id || closestForm.innerText || '').slice(0, 150) : '';
            const formAction = closestForm ? (closestForm.getAttribute('action') || '') : '';
            const formMethod = closestForm ? (closestForm.getAttribute('method') || 'POST').toUpperCase() : '';
            const formFields = closestForm ? Array.from(closestForm.querySelectorAll('input, select, textarea')).map(inp => ({
                name: inp.name || inp.id || inp.placeholder || inp.getAttribute('aria-label') || '',
                type: inp.type || inp.tagName.toLowerCase(),
                placeholder: inp.placeholder || '',
                value: inp.value || ''
            })).filter(f => f.name) : [];

            const isFormSubmit = el.type === 'submit' || (el.tagName.toLowerCase() === 'button' && (el.type === 'submit' || !el.type || el.closest('form')));
            const closestSection = el.closest('section, div, modal, dialog, fieldset');
            const parentText = closestSection ? (closestSection.innerText || '').slice(0, 100) : '';

            items.push({
                id: idCounter++,
                tag: el.tagName.toLowerCase(),
                text: text.slice(0, 80),
                type: el.type || '',
                role: el.getAttribute('role') || '',
                placeholder: el.placeholder || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                selector: getCssSelector(el),
                form_context: formContext,
                form_action: formAction,
                form_method: formMethod,
                form_fields: formFields,
                is_form_submit: isFormSubmit,
                parent_text: parentText
            });
        }

        // Recursively pierce Shadow DOMs and Same-Origin IFrames
        const allNodes = Array.from(root.querySelectorAll('*'));
        for (const node of allNodes) {
            if (node.shadowRoot) {
                processNode(node.shadowRoot);
            }
            if (node.tagName && (node.tagName.toLowerCase() === 'iframe' || node.tagName.toLowerCase() === 'frame')) {
                try {
                    const iframeDoc = node.contentDocument || (node.contentWindow && node.contentWindow.document);
                    if (iframeDoc) {
                        processNode(iframeDoc);
                    }
                } catch (e) {
                    console.log('Skipping cross-origin iframe:', node.src || e.message);
                }
            }
        }
    }

    processNode(document);
    return items;
}
"""


class DOMDistiller:
    """
    Extracts an Interactive DOM Snapshot (Accessibility Tree) containing only
    interactive and semantic controls from a Playwright Page with Shadow DOM & iframe piercing
    and virtualized container scrolling. Fallback to GPT-4o Vision when controls are sparse.
    """
    @staticmethod
    async def extract_interactive_snapshot(
        page: Page,
        scroll_virtualized: bool = True,
        goal: Optional[str] = None,
        cost_manager: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Runs JS evaluation on the page and returns a list of interactive element descriptors.
        Optionally performs up to 3 scroll passes on virtualized and plain infinite-scroll containers
        (where scrollHeight grows after scroll) to discover dynamic content without infinite loops.
        
        If AXTree element count is below VISION_FALLBACK_THRESHOLD, triggers VisionFallback (GPT-4o Vision).
        """
        try:
            snapshot = await page.evaluate(JS_DOM_DISTILLER)
            if not scroll_virtualized:
                return snapshot

            seen_selectors = {el.get("selector") for el in snapshot if el.get("selector")}

            # Incremental scroll pass for virtualized list & plain infinite scroll containers (capped at 3 attempts)
            max_scroll_attempts = 3
            scroll_count = 0

            while scroll_count < max_scroll_attempts:
                scroll_count += 1
                try:
                    scrolled = await page.evaluate("""
                    () => {
                        let didScroll = false;
                        // 1. Check scrollable elements in DOM (virtualized or plain scroll containers)
                        const allNodes = Array.from(document.querySelectorAll('*'));
                        for (const el of allNodes) {
                            if (el.scrollHeight > el.clientHeight && el.clientHeight > 0) {
                                const style = window.getComputedStyle(el);
                                const overflowY = style.overflowY || style.overflow;
                                if (overflowY === 'scroll' || overflowY === 'auto' || el.hasAttribute('data-virtualized')) {
                                    const prevTop = el.scrollTop;
                                    el.scrollTop += 300;
                                    el.dispatchEvent(new Event('scroll'));
                                    if (el.scrollTop > prevTop || el.scrollTop > 0) {
                                        didScroll = true;
                                        break;
                                    }
                                }
                            }
                        }
                        // 2. Fall back to plain window / document infinite scroll
                        if (!didScroll) {
                            const prevScrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
                            const prevY = window.scrollY;
                            window.scrollBy(0, 300);
                            window.dispatchEvent(new Event('scroll'));
                            const newScrollHeight = document.documentElement.scrollHeight || document.body.scrollHeight;
                            if (window.scrollY > prevY || newScrollHeight > prevScrollHeight) {
                                didScroll = true;
                            }
                        }
                        return didScroll;
                    }
                    """)
                    if not scrolled:
                        break

                    await page.wait_for_timeout(300)
                    extra_snapshot = await page.evaluate(JS_DOM_DISTILLER)
                    new_found = False
                    for el in extra_snapshot:
                        sel = el.get("selector")
                        if sel and sel not in seen_selectors:
                            seen_selectors.add(sel)
                            snapshot.append(el)
                            new_found = True
                    
                    if not new_found:
                        break
                except Exception:
                    break

            # ── Trigger Vision Fallback if AXTree element count is sparse ──────
            from app.engine.browser.vision_fallback import VisionFallback
            snapshot = await VisionFallback.extract_with_fallback(
                page=page,
                snapshot=snapshot,
                goal=goal,
                cost_manager=cost_manager,
            )

            return snapshot
        except Exception:
            return []

    @staticmethod
    async def has_canvas_element(page: Page) -> bool:
        """
        Detects if the page contains <canvas>, WebGL, or complex graphical containers
        that lack standard HTML interactive elements.
        """
        try:
            return await page.evaluate("""
            () => !!(
                document.querySelector('canvas') ||
                document.querySelector('svg.dense-canvas') ||
                document.querySelector('[data-interactive-canvas]') ||
                document.querySelector('embed[type*="webgl"]') ||
                document.querySelector('object[type*="webgl"]')
            )
            """)
        except Exception:
            return False

    @staticmethod
    async def detect_login_wall(page: Page, snapshot: List[Dict[str, Any]]) -> bool:
        """
        Detects if the page presents an unauthenticated login wall by checking for password inputs
        when session cookies are missing.
        
        Fixes failure mode: Agent wasting tokens trying to guess credentials or navigate authentication gates.
        """
        has_password_input = any(
            el.get("type") == "password" or (el.get("tag") == "input" and el.get("type") == "password")
            for el in snapshot
        )
        if not has_password_input:
            try:
                has_password_input = await page.evaluate("() => !!document.querySelector('input[type=\"password\"]')")
            except Exception:
                pass

        if not has_password_input:
            return False

        try:
            cookies = await page.context.cookies(page.url)
            if not cookies:
                return True
            has_session = any(
                any(kw in c.get("name", "").lower() for kw in ["session", "token", "auth", "sid", "jwt", "logged_in"])
                for c in cookies
            )
            return not has_session
        except Exception:
            return True


