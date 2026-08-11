import typer
from rich.console import Console
from app import __version__
from app.cli.commands.crawl import run_crawl
from app.cli.commands.list import list_endpoints
from app.cli.commands.export import export_docs
from app.cli.commands.login import run_login

console = Console()

app = typer.Typer(
    name="insightapi",
    help="InsightAPI AI — Agentic Web API Intelligence Platform CLI",
    add_completion=False
)

# Register CLI sub-commands
app.command(name="crawl")(run_crawl)
app.command(name="list-endpoints")(list_endpoints)
app.command(name="export")(export_docs)
app.command(name="login")(run_login)



@app.command(name="version")
def version():
    """Display InsightAPI AI CLI version"""
    console.print(f"[bold cyan]InsightAPI AI CLI[/bold cyan] version [bold green]{__version__}[/bold green]")


if __name__ == "__main__":
    app()
