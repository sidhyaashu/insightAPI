"""
insightapi login <url> — Interactive authenticated-session capture helper.

Opens a visible (non-headless) Chromium window, lets the user log in manually,
then serialises the resulting cookies + localStorage to a local JSON file that
can be passed to ``insightapi crawl --session-file <path>`` or directly to
``AgentEngine.crawl(session_state=...)``.

Security contract:
  - The session JSON is written only to the local path specified by --output.
  - Its contents are never printed, logged, or transmitted.
  - The file should be treated with the same sensitivity as a password.
"""
import asyncio
import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from app.engine.browser.manager import BrowserManager

console = Console()


async def _run_login_flow(url: str, output_path: Path) -> None:
    """
    Launches a visible Chromium window, waits for the user to authenticate,
    then saves the browser context's storage state to *output_path*.
    """
    browser_manager = BrowserManager(headless=False)  # Visible window — user must see the UI

    try:
        page = await browser_manager.new_page()

        console.print(Rule("[bold cyan]Browser Launched[/bold cyan]"))
        console.print(
            f"\n[bold white]A Chromium window has opened and is navigating to:[/bold white]\n"
            f"  [bold yellow]{url}[/bold yellow]\n"
        )
        console.print(
            "[bold white]Please log in to the site in the browser window.[/bold white]\n"
            "Once you are fully authenticated (dashboard visible, no login form),\n"
            "return here and press [bold green]Enter[/bold green] to save your session.\n"
        )

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Block until the user confirms login is complete
        typer.prompt(
            "Press Enter when you have finished logging in",
            default="",
            show_default=False,
        )

        # Persist the browser context's cookies + localStorage to disk
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await browser_manager.save_storage_state(str(output_path))

        console.print(Rule())
        console.print(
            Panel.fit(
                f"[bold green]✔ Session saved successfully![/bold green]\n\n"
                f"File: [bold yellow]{output_path.resolve()}[/bold yellow]\n\n"
                "[dim]Keep this file secure — it contains live session cookies.[/dim]\n"
                "[dim]Never commit it to version control.[/dim]\n\n"
                "To use it for an authenticated crawl, run:\n"
                f"  [bold cyan]insightapi crawl {url} --session-file {output_path}[/bold cyan]",
                title="Login Session Captured",
                border_style="green",
            )
        )

    finally:
        await browser_manager.stop()


def run_login(
    url: str = typer.Argument(..., help="URL of the login page to open in the browser"),
    output: Path = typer.Option(
        Path("session.json"),
        "--output",
        "-o",
        help="Local path where the session JSON file will be saved",
        metavar="PATH",
    ),
) -> None:
    """
    Open a browser window, log in manually, then save the session for authenticated crawls.

    Steps:
      1. A visible Chromium window opens and navigates to <url>.
      2. Log in to the site as you normally would.
      3. Return to this terminal and press Enter.
      4. The session (cookies + localStorage) is saved to --output.

    The saved file can then be passed to the crawl command:

        insightapi crawl https://app.example.com --session-file session.json

    Or used directly in the Python SDK:

        engine = AgentEngine()
        result = await engine.crawl(url, session_state=json.load(open("session.json")))

    \\b
    Security note: The session file is written only to the local path you specify.
    Its contents are never displayed, logged, or transmitted anywhere.
    """
    console.print(
        Panel.fit(
            f"[bold cyan]InsightAPI AI — Session Login Helper[/bold cyan]\n"
            f"Target URL:   [bold yellow]{url}[/bold yellow]\n"
            f"Output file:  [bold yellow]{output}[/bold yellow]",
            title="Authenticated Session Capture",
            border_style="cyan",
        )
    )

    asyncio.run(_run_login_flow(url, Path(output)))
