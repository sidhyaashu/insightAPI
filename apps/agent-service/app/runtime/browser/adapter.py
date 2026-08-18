"""
runtime/browser/adapter.py — Abstract Computer-Use Browser Interface for InsightAPI.

Architecture (AGENTS.md §6, §18, §19):
  - The agent must not directly depend on Playwright everywhere.
  - BrowserAdapter provides the standardized hands + eyes computer-use actuator interface.
  - AXTree-first: prefer structured accessibility tree & semantic interactive elements over raw HTML dumps.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PageState(BaseModel):
    """Normalized snapshot of current page status."""
    url: str
    title: str = ""
    status_code: Optional[int] = None
    content_type: str = ""
    state_hash: str = ""
    is_spa: bool = False


class AXNode(BaseModel):
    """A semantic node in the accessibility tree / interactive element index."""
    role: str = ""
    name: str = ""
    value: Optional[str] = None
    description: Optional[str] = None
    tag_name: str = ""
    selector: Optional[str] = None
    ref_id: Optional[str] = None
    is_clickable: bool = True
    children: List["AXNode"] = Field(default_factory=list)


class NetworkEvent(BaseModel):
    """Normalized network observation captured from browser network traffic."""
    method: str
    url: str
    template_path: str
    status_code: int
    content_type: str = "application/json"
    is_graphql: bool = False
    graphql_operation: Optional[str] = None
    graphql_type: Optional[str] = None
    sample_response: Optional[Any] = None
    occurrences: int = 1
    latency_ms: int = 0


class ConsoleEvent(BaseModel):
    """Browser console message event."""
    level: str  # "log" | "warn" | "error" | "info"
    text: str
    location: Optional[str] = None


class BrowserAdapter(ABC):
    """
    Abstract computer-use browser interface.

    Allows any browser implementation (Playwright local, Playwright remote,
    cloud browser, CDP) to plug in seamlessly.
    """

    @abstractmethod
    async def start(self) -> None:
        """Initialize the browser context and underlying engine."""
        pass

    @abstractmethod
    async def navigate(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        timeout_sec: float = 25.0,
    ) -> PageState:
        """Navigate to a target URL and return the page state."""
        pass

    @abstractmethod
    async def get_page_state(self) -> PageState:
        """Get the current page state and state hash."""
        pass

    @abstractmethod
    async def get_accessibility_tree(self) -> List[AXNode]:
        """
        Extract accessibility tree and interactive elements (including pierced Shadow DOMs).
        AXTree-first strategy per AGENTS.md §19.
        """
        pass

    @abstractmethod
    async def click(self, selector_or_ref: str, humanized: bool = True) -> bool:
        """Click on an interactive element by selector, ref, or text."""
        pass

    @abstractmethod
    async def type_text(self, selector_or_ref: str, text: str) -> bool:
        """Input text into an input, textarea, or contenteditable element."""
        pass

    @abstractmethod
    async def scroll(self, direction: str = "down", amount: int = 400) -> None:
        """Perform virtual scrolling on the page to trigger lazy loading."""
        pass

    @abstractmethod
    async def wait(self, ms: int) -> None:
        """Pause execution for DOM hydration or AJAX responses."""
        pass

    @abstractmethod
    async def screenshot(self) -> Optional[bytes]:
        """Capture a screenshot of the current page viewport."""
        pass

    @abstractmethod
    def get_network_events(self) -> List[NetworkEvent]:
        """Retrieve all intercepted network events captured during the session."""
        pass

    @abstractmethod
    def get_console_events(self) -> List[ConsoleEvent]:
        """Retrieve all browser console log events captured during the session."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Gracefully terminate page, context, and browser instances."""
        pass

    async def __aenter__(self) -> "BrowserAdapter":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
