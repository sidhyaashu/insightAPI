from typing import List, Dict, Any, Optional
import asyncio
import time
import uuid
from app.engine.browser.manager import BrowserManager
from app.engine.browser.dom_distiller import DOMDistiller
from app.engine.network.listener import NetworkObserver
from app.agents.graph import build_crawl_graph
from app.agents.state import CrawlState
from app.services.openapi_exporter import OpenAPIExporter
from app.services.postman_exporter import PostmanExporter
from app.services.markdown_exporter import MarkdownExporter
from app.services.session_store import save_session
from app.core.compliance import RobotsChecker
from app.core.config import settings
from app.core.logging_config import get_logger, log_step

logger = get_logger("engine.sdk")


class CrawlResult:
    """
    Result container returned by the InsightAPI SDK crawl execution.
    """
    def __init__(
        self,
        target_url: str,
        captured_endpoints: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        explored_count: int = 1,
        elapsed_time_seconds: float = 0.0,
        llm_metrics: Optional[Dict[str, Any]] = None,
        action_traces: Optional[List[Dict[str, Any]]] = None,
        security_findings: Optional[List[Dict[str, Any]]] = None,
    ):
        self.target_url = target_url
        self.captured_endpoints = captured_endpoints
        self.session_id = session_id or str(uuid.uuid4())
        self.explored_count = explored_count
        self.elapsed_time_seconds = elapsed_time_seconds
        self.llm_metrics: Dict[str, Any] = llm_metrics or {}
        self.action_traces: List[Dict[str, Any]] = action_traces or []
        self.security_findings: List[Dict[str, Any]] = security_findings or []
        """UI-facing LLM cost metrics: tokens_used, llm_calls_made, estimated_cost_usd, etc."""

    @property
    def rest_count(self) -> int:
        return sum(1 for ep in self.captured_endpoints if not ep.get("graphql_operation_name") and ep.get("method") != "WS")

    @property
    def graphql_count(self) -> int:
        return sum(1 for ep in self.captured_endpoints if ep.get("graphql_operation_name"))

    @property
    def websocket_count(self) -> int:
        return sum(1 for ep in self.captured_endpoints if ep.get("method") == "WS" or ep.get("resource_type") == "websocket")

    def to_openapi(self) -> str:
        """Export OpenAPI 3.0.3 JSON string."""
        return OpenAPIExporter.export_to_json("InsightAPI SDK", self.target_url, self.captured_endpoints)

    def to_postman(self) -> str:
        """Export Postman Collection v2.1 JSON string."""
        return PostmanExporter.export_to_json("InsightAPI SDK", self.target_url, self.captured_endpoints)

    def to_markdown(self) -> str:
        """Export Markdown API Documentation string."""
        return MarkdownExporter.generate_markdown("InsightAPI SDK", self.target_url, self.captured_endpoints)

    def to_playwright_test(self, format: str = "python") -> str:
        """Generate runnable Playwright regression test script from recorded action traces."""
        from app.generators.playwright_test_gen import PlaywrightTestGenerator
        if format.lower() in ["ts", "typescript"]:
            return PlaywrightTestGenerator.generate_typescript_test(self.target_url, self.action_traces)
        return PlaywrightTestGenerator.generate_python_test(self.target_url, self.action_traces)



class AgentEngine:
    """
    Open-Source Python SDK Interface for InsightAPI AI.
    
    Usage::

        import asyncio, json
        from insightapi import AgentEngine

        async def main():
            engine = AgentEngine(headless=True)

            # Unauthenticated crawl
            result = await engine.crawl("https://example.com", max_pages=5)

            # Authenticated crawl (load a session file previously saved by `insightapi login`)
            with open("session.json") as f:
                session = json.load(f)
            result = await engine.crawl("https://app.example.com", max_pages=5, session_state=session)

            print(result.to_openapi())

        asyncio.run(main())
    """
    def __init__(
        self,
        headless: bool = True,
        humanize_interactions: bool = True,
        fast_mode: bool = False,
        enable_security_testing: bool = False,
        allow_destructive_tests: bool = False,
    ):
        self.headless = headless
        self.humanize_interactions = humanize_interactions
        self.fast_mode = fast_mode
        self.enable_security_testing = enable_security_testing
        self.allow_destructive_tests = allow_destructive_tests

    async def crawl(
        self,
        url: str,
        max_pages: int = 10,
        rate_limit_ms: int = 500,
        session_state: Optional[Dict[str, Any]] = None,
        auth_profile: Optional[Any] = None,
        auth_profile_id: Optional[str] = None,
        goal: Optional[str] = None,
        parallel: bool = False,
        max_agents: int = 1,
        humanize_interactions: Optional[bool] = None,
        fast: bool = False,
        crawl_id: Optional[str] = None,
        user_id: Optional[str] = None,
        enable_security_testing: Optional[bool] = None,
    ) -> CrawlResult:
        effective_humanize = False if (fast or self.fast_mode) else (self.humanize_interactions if humanize_interactions is None else humanize_interactions)
        sec_testing = self.enable_security_testing if enable_security_testing is None else enable_security_testing

        if parallel and max_agents > 1:
            from app.agents.coordinator import CrawlCoordinator
            return await CrawlCoordinator.run_parallel_crawl(
                url=url,
                max_pages=max_pages,
                max_agents=max_agents,
                rate_limit_ms=rate_limit_ms,
                session_state=session_state,
                goal=goal,
                headless=self.headless,
            )

        # ── Automated AuthProfile Login Execution ──────────────────────────
        if session_state is None and (auth_profile or auth_profile_id):
            try:
                from app.engine.auth.executor import AutoLoginExecutor
                active_profile = auth_profile
                if not active_profile and auth_profile_id:
                    from sqlalchemy import select
                    from app.core.database import AsyncSessionLocal
                    from app.models.auth_profile import AuthProfile
                    async with AsyncSessionLocal() as db:
                        stmt_res = await db.execute(select(AuthProfile).where(AuthProfile.id == auth_profile_id))
                        active_profile = stmt_res.scalar_one_or_none()

                if active_profile:
                    log_step(logger, 0, "Executing Automated Login", f"Profile: {active_profile.name} [{active_profile.auth_type}] -> {active_profile.login_url}")
                    session_state = await AutoLoginExecutor.execute_login(active_profile, headless=self.headless)
                    logger.info(f"✓ AutoLoginExecutor: Session state acquired ({len(session_state.get('cookies', []))} cookies).")
            except Exception as auth_err:
                logger.error(f"Failed to execute automated login for profile: {auth_err}")

        start_time = time.time()
        session_id = crawl_id or str(uuid.uuid4())

        log_step(logger, 1, "Initializing Engine Session", f"Target URL: {url} | Max Pages: {max_pages} | Rate Limit: {rate_limit_ms}ms | Headless: {self.headless} | Humanized: {effective_humanize} | Authenticated: {session_state is not None} | Goal: {goal or 'all APIs'}")

        # Initialize per-session LLM cost manager
        from app.agents.nodes.llm_client import make_cost_manager
        cost_manager = make_cost_manager(crawl_id=session_id, user_id=user_id)
        logger.info(f"LLMCostManager initialized | Budget: {settings.LLM_TOKEN_BUDGET_PER_CRAWL} tokens | Planner cap: {settings.LLM_PLANNER_MAX_CALLS} calls")

        browser_manager = BrowserManager(headless=self.headless, storage_state=session_state)
        observer = NetworkObserver()

        try:
            # Wire RobotsChecker compliance parser for target domain
            log_step(logger, 2, "Parsing robots.txt Compliance Rules", f"Domain target: {url}")
            await RobotsChecker.fetch_and_parse(url)

            log_step(logger, 3, "Launching Browser & Navigating", f"URL: {url}")
            page = await browser_manager.new_page()
            observer.attach_to_page(page)

            await browser_manager.navigate_safely(page, url, timeout_ms=30000)
            dom_snapshot = await DOMDistiller.extract_interactive_snapshot(page)
            logger.info(f"Initial AXTree DOM snapshot extracted: {len(dom_snapshot)} interactive elements found.")

            # Publish initial navigation event
            if crawl_id:
                try:
                    from app.api.v1.endpoints.crawls import publish_ws_event
                    await publish_ws_event(crawl_id, {
                        "type": "page_visited",
                        "url": page.url,
                        "title": await page.title(),
                        "page_number": 1,
                        "max_pages": max_pages,
                        "interactive_count": len(dom_snapshot),
                    })
                except Exception:
                    pass

            initial_state: CrawlState = {
                "target_url": url,
                "current_url": page.url,
                "visited_urls": [url],
                "visited_state_hashes": [],
                "visited_selectors": [],
                "interactive_elements": dom_snapshot,
                "captured_endpoints": [ep.to_dict() for ep in observer.captured_endpoints],
                "next_action": None,
                "is_safe_action": True,
                "risk_reason": None,
                "frontier": [],
                "explored_count": 1,
                "max_pages": max_pages,
                "is_complete": False,
                "error_message": None,
                "auth_required_url": None,
                "modal_action_count": 0,
                "deprioritized_modal_selectors": [],
                "last_endpoint_count": 0,
                "network_observer": observer,
                "page_ref": page,
                "rate_limit_ms": rate_limit_ms,
                "humanize_interactions": effective_humanize,
                # Session identity for DB-writing nodes
                "crawl_id": session_id,
                "user_id": user_id,
                # Intelligence-layer fields
                "goal": goal,
                "planner_reasoning": None,
                "reflection_notes": None,
                "endpoint_categories": [],
                "cost_manager": cost_manager,
                "llm_planner_call_count": 0,
                # Security testing
                "security_testing_enabled": sec_testing,
                "allow_destructive_tests": self.allow_destructive_tests,
                "security_findings": [],
            }

            log_step(logger, 4, "Starting Autonomous Exploration Loop", "Invoking LangGraph Agent Graph")
            graph = build_crawl_graph()

            timeout_sec = getattr(settings, "CRAWL_TIMEOUT_SECONDS", 120)
            try:
                final_state = await asyncio.wait_for(graph.ainvoke(initial_state), timeout=timeout_sec)
            except asyncio.TimeoutError:
                logger.warning(f"Crawl execution timed out after {timeout_sec}s.")
                final_state = initial_state
                final_state["error_message"] = f"Crawl execution timed out after {timeout_sec}s."

            # Update final captured endpoints from observer
            latest_captured = [ep.to_dict() for ep in observer.captured_endpoints]
            final_state["captured_endpoints"] = latest_captured
            logger.info(f"Exploration complete. Total captured network calls: {len(latest_captured)}")

            log_step(logger, 5, "Running Endpoint Disambiguation & Schema Analyzer")
            from app.agents.nodes.analyzer import AnalyzerNode
            analyzed_state = await AnalyzerNode.process(final_state)

            captured = analyzed_state.get("captured_endpoints", [])
            explored_count = analyzed_state.get("explored_count", len(analyzed_state.get("visited_urls", [url])))
            elapsed_sec = round(time.time() - start_time, 1)

            log_step(logger, 6, "Session Completed Successfully", f"Final Unique Endpoints Discovered: {len(captured)}")

            # Persist session to local JSON store for CLI commands
            save_session(
                session_id=session_id,
                target_url=url,
                captured_endpoints=captured,
                explored_count=explored_count,
                elapsed_time_seconds=elapsed_sec,
                status="completed" if not analyzed_state.get("error_message") else "completed_with_errors",
                error_message=analyzed_state.get("error_message"),
            )

            return CrawlResult(
                target_url=url,
                captured_endpoints=captured,
                session_id=session_id,
                explored_count=explored_count,
                elapsed_time_seconds=elapsed_sec,
                llm_metrics=cost_manager.get_metrics(),
                action_traces=analyzed_state.get("action_traces", []),
                security_findings=analyzed_state.get("security_findings", []),
            )
        finally:
            await browser_manager.stop()




