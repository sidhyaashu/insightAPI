import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.services.session_store import get_session, list_sessions

console = Console()
list_app = typer.Typer(help="List discovered endpoints and crawl sessions")


def list_endpoints(
    session_id: Optional[str] = typer.Argument(
        None,
        help="Crawl Session ID to view endpoints for (defaults to latest session if omitted)",
    ),
    all_sessions: bool = typer.Option(
        False,
        "--sessions",
        "-a",
        help="List all saved crawl sessions instead of endpoint details",
    ),
):
    """
    List discovered API endpoints from a saved crawl session, or list all local crawl sessions.
    """
    if all_sessions:
        _display_all_sessions()
        return

    session = get_session(session_id)
    if not session:
        if session_id:
            console.print(f"[bold red]Error:[/bold red] Crawl session '{session_id}' not found in local store.")
        else:
            console.print("[bold red]No crawl sessions found.[/bold red] Run an autonomous crawl first:")
            console.print("  [bold cyan]insightapi crawl https://httpbin.org --max-pages 5[/bold cyan]\n")
        return

    target_url = session.get("target_url", "N/A")
    sid = session.get("session_id", "N/A")
    created = session.get("created_at", "")[:19].replace("T", " ")
    captured = session.get("captured_endpoints", [])

    table = Table(
        title=f"Discovered Endpoints for Session [yellow]{sid[:8]}[/yellow] ({target_url})",
        header_style="bold magenta",
    )
    table.add_column("#", justify="center", style="dim")
    table.add_column("Method", justify="center", style="bold green")
    table.add_column("Endpoint Route", style="yellow")
    table.add_column("Type", justify="center", style="blue")
    table.add_column("Status", justify="center", style="cyan")
    table.add_column("Confidence", justify="center", style="magenta")

    if captured:
        for idx, ep in enumerate(captured, 1):
            method = ep.get("method", "GET").upper()
            route = ep.get("template_route", "/")
            status = str(ep.get("status", 200))
            confidence = ep.get("confidence", 0.85)
            graphql_op = ep.get("graphql_operation_name")

            if graphql_op:
                ep_type = "GraphQL"
                display_route = f"{route} ({graphql_op})" if "(" not in route else route
            elif method == "WS":
                ep_type = "WebSocket"
                display_route = route
            else:
                ep_type = "REST"
                display_route = route

            table.add_row(
                str(idx),
                method,
                display_route,
                ep_type,
                status,
                f"{confidence:.2f}",
            )
    else:
        table.add_row("1", "GET", target_url, "REST", "200", "0.85")

    console.print()
    console.print(table)
    console.print(
        f"[dim]Session ID: {sid} | Created: {created} | "
        f"Pages: {session.get('explored_count', 1)} | Duration: {session.get('elapsed_time_seconds', 0)}s[/dim]\n"
    )
    console.print(f"[dim]To export this session: [bold cyan]insightapi export --session-id {sid}[/bold cyan][/dim]\n")


def _display_all_sessions():
    sessions = list_sessions()
    if not sessions:
        console.print("[bold red]No saved crawl sessions found.[/bold red]")
        return

    table = Table(title=f"Saved Crawl Sessions ({len(sessions)})", header_style="bold magenta")
    table.add_column("Session ID", justify="center", style="bold yellow")
    table.add_column("Target URL", style="cyan")
    table.add_column("Endpoints", justify="center", style="bold green")
    table.add_column("Pages", justify="center", style="blue")
    table.add_column("Duration", justify="center", style="magenta")
    table.add_column("Created At", justify="center", style="dim")

    for s in sessions:
        sid_short = s["session_id"][:12] + "..." if len(s["session_id"]) > 12 else s["session_id"]
        created = s["created_at"][:19].replace("T", " ") if s["created_at"] else ""
        table.add_row(
            sid_short,
            s["target_url"],
            f"{s['endpoint_count']} (REST: {s['rest_count']}, GQL: {s['graphql_count']})",
            str(s["explored_count"]),
            f"{s['elapsed_time_seconds']}s",
            created,
        )

    console.print()
    console.print(table)
    console.print("\n[dim]To view endpoints for a session: [bold cyan]insightapi list-endpoints <session_id>[/bold cyan][/dim]\n")


@list_app.callback(invoke_without_command=True)
def main(
    session_id: Optional[str] = typer.Argument(None, help="Crawl Session ID"),
    all_sessions: bool = typer.Option(False, "--sessions", "-a", help="List all sessions"),
):
    list_endpoints(session_id=session_id, all_sessions=all_sessions)
