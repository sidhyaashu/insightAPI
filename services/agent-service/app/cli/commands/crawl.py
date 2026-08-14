import asyncio
import json
import re
import typer
from pathlib import Path
from urllib.parse import urlparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.sdk import AgentEngine
from app.core.compliance import RobotsChecker

console = Console()


async def execute_crawl_pipeline(
    url: str,
    max_pages: int,
    headless: bool,
    export_format: str = "all",
    output_dir: Path | None = None,
    rate_limit_ms: int = 500,
    session_state: dict | None = None,
    goal: str | None = None,
    parallel: bool = False,
    max_agents: int = 1,
    fast: bool = False,
):
    """Executes the AgentEngine autonomous exploration pipeline and formats terminal output."""
    try:
        engine = AgentEngine(headless=headless, fast_mode=fast)
        result = await engine.crawl(
            url,
            max_pages=max_pages,
            rate_limit_ms=rate_limit_ms,
            session_state=session_state,
            goal=goal,
            parallel=parallel,
            max_agents=max_agents,
            fast=fast,
        )
        captured = result.captured_endpoints

        # ── (a) One-line summary ────────────────────────────────────────────────
        rest_count = result.rest_count
        graphql_count = result.graphql_count
        pages = result.explored_count
        elapsed = result.elapsed_time_seconds

        console.print(
            f"\n[bold green]Found {rest_count} REST endpoints, {graphql_count} GraphQL ops "
            f"across {pages} pages in {elapsed}s[/bold green]\n"
        )

        # ── (b) Endpoint table ─────────────────────────────────────────────────
        table = Table(title=f"Crawl Summary: {len(captured)} Endpoints Discovered", header_style="bold magenta")
        table.add_column("Method", justify="center", style="bold green")
        table.add_column("Template Route", style="yellow")
        table.add_column("Status", justify="center", style="cyan")

        if captured:
            for item in captured:
                table.add_row(
                    item.get("method", "GET"),
                    item.get("template_route", "/"),
                    str(item.get("status", 200))
                )
        else:
            table.add_row("GET", url, "200 (Initial Page Load)")

        console.print(table)

        # ── (c) Auto-export specified formats ─────────────────────────────────
        fmt_lower = export_format.lower()
        if fmt_lower != "none":
            if output_dir:
                out_dir = Path(output_dir)
            else:
                parsed = urlparse(url)
                raw_host = parsed.netloc or parsed.path.split("/")[0] or "target"
                domain_slug = re.sub(r'[^a-zA-Z0-9.-]', '_', raw_host).strip("_")
                out_dir = Path("./insightapi-output") / domain_slug

            out_dir.mkdir(parents=True, exist_ok=True)
            console.print(f"\n[bold cyan]Auto-exporting generated specs to:[/bold cyan] {out_dir.resolve()}")

            if fmt_lower in {"openapi", "all"}:
                oa_path = out_dir / "openapi.json"
                oa_path.write_text(result.to_openapi(), encoding="utf-8")
                console.print(f"  [bold green]✔ Exported OpenAPI 3.0 spec to:[/bold green] {oa_path}")

            if fmt_lower in {"postman", "all"}:
                pm_path = out_dir / "postman.json"
                pm_path.write_text(result.to_postman(), encoding="utf-8")
                console.print(f"  [bold green]✔ Exported Postman collection to:[/bold green] {pm_path}")

            if fmt_lower in {"markdown", "all"}:
                md_path = out_dir / "API_DOCS.md"
                md_path.write_text(result.to_markdown(), encoding="utf-8")
                console.print(f"  [bold green]✔ Exported Markdown docs to:[/bold green] {md_path}")

        # ── (d) Reminder of exact export command ──────────────────────────────
        console.print(f"\n[dim]To export again or in another format, run:[/dim]")
        console.print(
            f"  [bold cyan]insightapi export --session-id {result.session_id} "
            f"--format openapi --output ./openapi.json[/bold cyan]\n"
        )

    except Exception as e:
        console.print(f"[bold red]Crawl Execution Error:[/bold red] {e}")


def run_crawl(
    url: str = typer.Argument(..., help="Target website URL to autonomously explore"),
    max_pages: int = typer.Option(10, "--max-pages", "-m", help="Maximum number of pages to navigate"),
    depth: int = typer.Option(3, "--depth", "-d", help="Maximum crawl depth"),
    rate_limit: int = typer.Option(
        500,
        "--rate-limit",
        "-r",
        help="Minimum per-domain delay spacing between requests in milliseconds (default: 500ms)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-F",
        help="Force crawl execution even if target URL/root is disallowed in robots.txt",
    ),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="Run browser in headless mode"),
    format: str = typer.Option(
        "all",
        "--format",
        "-f",
        help="Export format to generate automatically: openapi, postman, markdown, all, or none",
    ),
    output_dir: Path = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory for auto-exported specs (defaults to ./insightapi-output/<domain>/)",
        metavar="PATH",
    ),
    session_file: Path = typer.Option(
        None,
        "--session-file",
        "-s",
        help=(
            "Path to a Playwright storage_state JSON file previously saved by "
            "'insightapi login'. Injects cookies/localStorage so the agent starts "
            "already authenticated. Never transmitted outside your machine."
        ),
        exists=False,
        metavar="PATH",
    ),
    goal: str = typer.Option(
        None,
        "--goal",
        "-g",
        help="Optional natural-language crawl objective (e.g. 'Find all billing and invoice endpoints')",
    ),
    parallel: bool = typer.Option(
        False,
        "--parallel",
        "-p",
        help="Decompose application into sections and run parallel crawler sub-agents",
    ),
    agents: int = typer.Option(
        1,
        "--agents",
        "-a",
        help="Number of parallel crawler sub-agents to spawn when --parallel is enabled (default: 1, max: 5)",
    ),
    fast: bool = typer.Option(
        False,
        "--fast",
        "-f",
        help="Fast mode: disables humanized Bezier mouse curves and typing jitter for trusted/internal targets",
    ),
):
    """
    Start an autonomous AI exploration session on a target URL.

    Compliance Guardrails:
    - Parses target site robots.txt. If root path or target URL is disallowed, prints a warning
      and asks for confirmation unless --force is passed.
    - Respects per-domain rate limiting spacing (--rate-limit, default 500ms).
    """
    session_state: dict | None = None

    if session_file is not None:
        if not Path(session_file).exists():
            console.print(f"[bold red]Error:[/bold red] Session file not found: {session_file}")
            raise typer.Exit(code=1)
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session_state = json.load(f)
            console.print(
                f"[bold yellow]⚠  Authenticated session loaded from:[/bold yellow] {session_file}\n"
                "   The browser context will start with injected cookies/localStorage.\n"
                "   Session data is used only within this process and never transmitted."
            )
        except (json.JSONDecodeError, OSError) as e:
            console.print(f"[bold red]Error:[/bold red] Failed to read session file '{session_file}': {e}")
            raise typer.Exit(code=1)

    # ── Check robots.txt compliance before starting ───────────────────────────
    asyncio.run(RobotsChecker.fetch_and_parse(url))
    warning = RobotsChecker.check_disallowed_warning(url)

    if warning:
        console.print(
            Panel.fit(
                f"[bold yellow]⚠ COMPLIANCE WARNING: robots.txt Restriction Detected[/bold yellow]\n\n"
                f"Target path '[bold red]{warning['disallowed_path']}[/bold red]' is marked DISALLOWED in robots.txt.\n"
                "Crawling this site may violate target site Terms of Service or crawling policy.",
                title="robots.txt Restriction",
                border_style="yellow",
            )
        )

        if not force:
            try:
                proceed = typer.confirm("Do you want to force proceed with crawling anyway?", default=False)
            except Exception:
                proceed = False

            if not proceed:
                console.print(
                    "\n[bold red]Crawl aborted due to robots.txt restriction.[/bold red]\n"
                    "Pass [bold cyan]--force[/bold cyan] to override if you own this application or have explicit permission.\n"
                    "See CRAWLING_POLICY.md for legal and ethical guidelines.\n"
                )
                raise typer.Exit(code=1)
            else:
                console.print("[bold yellow]Proceeding crawl with --force override...[/bold yellow]\n")

    console.print(Panel.fit(
        f"[bold cyan]InsightAPI AI Agent[/bold cyan]\n"
        f"Target URL: [bold yellow]{url}[/bold yellow]\n"
        f"Max Pages: {max_pages} | Rate Limit: {rate_limit}ms | Headless: {headless} | Format: {format.upper()} | "
        f"Fast Mode: {'[bold red]Yes[/bold red]' if fast else '[bold green]No (Humanized)[/bold green]'} | "
        f"Authenticated: {'[bold green]Yes[/bold green]' if session_state else '[dim]No[/dim]'}",
        title="Starting Autonomous Crawl Session",
        border_style="cyan"
    ))

    asyncio.run(
        execute_crawl_pipeline(
            url=url,
            max_pages=max_pages,
            headless=headless,
            export_format=format,
            output_dir=output_dir,
            rate_limit_ms=rate_limit,
            session_state=session_state,
            goal=goal,
            parallel=parallel,
            max_agents=agents,
            fast=fast,
        )
    )
