"""
runtime/browser/__init__.py — InsightAPI Computer-Use Browser Abstraction Layer.

Defines the BrowserAdapter interface and PlaywrightBrowserAdapter implementation.
Reference: AGENTS.md §6, §18, §19.
"""
from app.runtime.browser.adapter import (
    BrowserAdapter,
    PageState,
    AXNode,
    NetworkEvent,
    ConsoleEvent,
)
from app.runtime.browser.playwright_adapter import PlaywrightBrowserAdapter

__all__ = [
    "BrowserAdapter",
    "PageState",
    "AXNode",
    "NetworkEvent",
    "ConsoleEvent",
    "PlaywrightBrowserAdapter",
]
