import typer
from pathlib import Path
from typing import Optional
from rich.console import Console

from app.services.session_store import get_session
from app.services.openapi_exporter import OpenAPIExporter
from app.services.postman_exporter import PostmanExporter
from app.services.markdown_exporter import MarkdownExporter

console = Console()
export_app = typer.Typer(help="Export discovered API documentation and schemas")


def export_docs(
    session_id: Optional[str] = typer.Option(
        None,
        "--session-id",
        "-s",
        help="Crawl Session ID (defaults to the most recent crawl session if omitted)",
    ),
    format: str = typer.Option(
        "openapi",
        "--format",
        "-f",
        help="Export format: openapi, postman, markdown, or all",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path (or directory path if format is 'all')",
    ),
):
    """
    Export OpenAPI 3.0 specs, Postman Collections, or Markdown documentation from a saved session.
    """
    session = get_session(session_id)
    if not session:
        if session_id:
            console.print(f"[bold red]Error:[/bold red] Crawl session '{session_id}' not found in local store.")
        else:
            console.print("[bold red]Error:[/bold red] No saved crawl sessions found. Run a crawl first:")
            console.print("  [bold cyan]insightapi crawl https://httpbin.org --max-pages 5[/bold cyan]\n")
        raise typer.Exit(code=1)

    target_url = session.get("target_url", "https://example.com")
    captured = session.get("captured_endpoints", [])
    sid = session.get("session_id", "session")
    fmt_lower = format.lower()

    console.print(f"[bold cyan]Exporting API Documentation...[/bold cyan]")
    console.print(f"Session ID:  [bold yellow]{sid}[/bold yellow]")
    console.print(f"Target URL:  [bold yellow]{target_url}[/bold yellow]")
    console.print(f"Format:      [bold magenta]{fmt_lower.upper()}[/bold magenta]\n")

    if fmt_lower == "openapi":
        out_path = Path(output) if output else Path("./openapi.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = OpenAPIExporter.export_to_json("InsightAPI CLI", target_url, captured)
        out_path.write_text(content, encoding="utf-8")
        console.print(f"[bold green]✔ Successfully exported OPENAPI spec to {out_path.resolve()}[/bold green]")

    elif fmt_lower == "postman":
        out_path = Path(output) if output else Path("./postman.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = PostmanExporter.export_to_json("InsightAPI CLI", target_url, captured)
        out_path.write_text(content, encoding="utf-8")
        console.print(f"[bold green]✔ Successfully exported POSTMAN collection to {out_path.resolve()}[/bold green]")

    elif fmt_lower == "markdown":
        out_path = Path(output) if output else Path("./API_DOCS.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content = MarkdownExporter.generate_markdown("InsightAPI CLI", target_url, captured)
        out_path.write_text(content, encoding="utf-8")
        console.print(f"[bold green]✔ Successfully exported MARKDOWN documentation to {out_path.resolve()}[/bold green]")

    elif fmt_lower == "all":
        out_dir = Path(output) if output else Path("./insightapi-output")
        out_dir.mkdir(parents=True, exist_ok=True)

        oa_path = out_dir / "openapi.json"
        pm_path = out_dir / "postman.json"
        md_path = out_dir / "API_DOCS.md"

        oa_path.write_text(OpenAPIExporter.export_to_json("InsightAPI CLI", target_url, captured), encoding="utf-8")
        pm_path.write_text(PostmanExporter.export_to_json("InsightAPI CLI", target_url, captured), encoding="utf-8")
        md_path.write_text(MarkdownExporter.generate_markdown("InsightAPI CLI", target_url, captured), encoding="utf-8")

        console.print(f"[bold green]✔ Exported OPENAPI spec to:[/bold green] {oa_path.resolve()}")
        console.print(f"[bold green]✔ Exported POSTMAN collection to:[/bold green] {pm_path.resolve()}")
        console.print(f"[bold green]✔ Exported MARKDOWN docs to:[/bold green] {md_path.resolve()}")

    else:
        console.print(f"[bold red]Error:[/bold red] Invalid format '{format}'. Choose openapi, postman, markdown, or all.")
        raise typer.Exit(code=1)


@export_app.callback(invoke_without_command=True)
def main(
    session_id: Optional[str] = typer.Option(None, "--session-id", "-s", help="Crawl Session ID"),
    format: str = typer.Option("openapi", "--format", "-f", help="Export format: openapi, postman, markdown, or all"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    export_docs(session_id=session_id, format=format, output=output)
