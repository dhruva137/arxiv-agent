from arxiv_diff import __version__
from arxiv_diff.tools import arxiv_api, pdf_extractor, section_parser, text_differ
from arxiv_diff.agent.orchestrator import ArxivDiffAgent
from watcher import monitor
from db import store
import uvicorn
import asyncio
import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.markdown import Markdown
from typing import Optional

app = typer.Typer(help="arxiv-diff " + __version__ + " — What changed in that paper?")
console = Console()

def run_async(coro):
    return asyncio.run(coro)

@app.command()
def diff(
    arxiv_id: str,
    v1: Optional[int] = typer.Option(None, help="Older version number"),
    v2: Optional[int] = typer.Option(None, help="Newer version number"),
    format: str = typer.Option("markdown", help="Output format: markdown|json|short")
):
    """
    Generate a full agentic changelog strictly using Claude.
    """
    console.print(f"[bold]arxiv-diff v{__version__}[/bold] — What changed in that paper?")
    
    # We construct the query for the agent.
    if v1 is not None and v2 is not None:
        query = f"What changed in {arxiv_id} between v{v1} and v{v2}?"
    else:
        query = f"What changed in {arxiv_id}?"
        
    with Live(console=console, transient=True) as live:
        def agent_callback(msg):
            live.update(f"[bold cyan]Agent Status:[/bold cyan] {msg}")
            
        agent = ArxivDiffAgent(callback=agent_callback)
        try:
            res = run_async(agent.run(query))
        except Exception as e:
            console.print(f"[bold red]Error running agent:[/bold red] {e}")
            raise typer.Exit(1)
            
    if format == "markdown":
        console.print(Markdown(res))
    else:
        console.print(res)

@app.command()
def versions(arxiv_id: str):
    """
    Look up the version history for an arXiv paper.
    """
    with console.status(f"Fetching version history for {arxiv_id}...", spinner="dots"):
        try:
            info = run_async(arxiv_api.get_paper_versions(arxiv_id))
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            raise typer.Exit(1)
            
    table = Table(title=info["title"], show_header=True, header_style="bold magenta")
    table.add_column("Version", justify="center")
    table.add_column("Date", justify="left")
    table.add_column("Size", justify="right")
    
    latest = info.get("latest_version", 1)
    
    for v in info["versions"]:
        is_latest = v["version"] == latest
        style = "bold green" if is_latest else None
        marker = " (Latest)" if is_latest else ""
        table.add_row(
            f"v{v['version']}{marker}",
            v["date"],
            v["size"],
            style=style
        )
        
    console.print(table)

@app.command()
def quick(arxiv_id: str):
    """
    Fast local diff skipping the LLM agent.
    """
    with console.status("Fetching paper metadata...", spinner="dots"):
        info = run_async(arxiv_api.get_paper_versions(arxiv_id))
        
    versions_list = info.get("versions", [])
    if len(versions_list) < 2:
        console.print("[yellow]Paper only has 1 version. Nothing to compare.[/yellow]")
        return
        
    v2_num = versions_list[-1]["version"]
    v1_num = versions_list[-2]["version"]
    
    v1_id = f"{info['id']}v{v1_num}"
    v2_id = f"{info['id']}v{v2_num}"
    
    with console.status(f"Downloading v{v1_num}...", spinner="dots"):
        pdf_v1 = run_async(arxiv_api.download_pdf(v1_id))
    with console.status(f"Downloading v{v2_num}...", spinner="dots"):
        pdf_v2 = run_async(arxiv_api.download_pdf(v2_id))
        
    with console.status("Extracting and parsing text...", spinner="dots"):
        t1 = pdf_extractor.extract_text(pdf_v1)
        t2 = pdf_extractor.extract_text(pdf_v2)
        s1 = section_parser.parse(t1)
        s2 = section_parser.parse(t2)
        
    with console.status("Diffing sections...", spinner="dots"):
        d = text_differ.diff(s1, s2)
        
    console.print(f"\n[bold underline]Quick Diff Stats for {info['title']}[/bold underline]")
    console.print(f"Comparing [cyan]v{v1_num}[/cyan] -> [cyan]v{v2_num}[/cyan]\n")
    console.print(f"[bold green]Added lines:[/bold green]    {d['total_added_lines']}")
    console.print(f"[bold red]Removed lines:[/bold red]  {d['total_removed_lines']}")
    
    if d['added_sections']:
        console.print(f"\n[b]Added Sections:[/b] {', '.join(d['added_sections'])}")
    if d['removed_sections']:
        console.print(f"[b]Removed Sections:[/b] {', '.join(d['removed_sections'])}")
        
    if d['changed_sections']:
        console.print("\n[b]Modified Sections:[/b]")
        for sec, stats in d['changed_sections'].items():
            rewrite_flag = " [red](Major Rewrite)[/red]" if stats['is_major_rewrite'] else ""
            console.print(f" - {sec}: +{stats['added_lines']} -{stats['removed_lines']}{rewrite_flag}")

@app.command()
def watch(arxiv_id: str):
    """Add a paper to the watch list."""
    # optionally fetch to get title and latest_version right now
    try:
        info = run_async(arxiv_api.get_paper_versions(arxiv_id))
        title = info["title"]
        latest = info["latest_version"]
    except Exception:
        title = None
        latest = 1
        
    s = store.add_watched_paper(arxiv_id, title=title, last_known_version=latest)
    if s:
        console.print(f"[green]Added {arxiv_id} to watch list.[/green]")
    else:
        console.print(f"[yellow]{arxiv_id} is already in watch list.[/yellow]")

@app.command()
def unwatch(arxiv_id: str):
    """Remove a paper from the watch list."""
    s = store.remove_watched_paper(arxiv_id)
    if s:
        console.print(f"[green]Removed {arxiv_id} from watch list.[/green]")
    else:
        console.print(f"[yellow]{arxiv_id} was not in watch list.[/yellow]")

@app.command()
def watched():
    """List all watched papers."""
    papers = store.get_watched_papers()
    if not papers:
        console.print("No papers are currently watched.")
        return
        
    table = Table(title="Watched Papers")
    table.add_column("arXiv ID")
    table.add_column("Title")
    table.add_column("Known Version")
    table.add_column("Last Checked")
    
    for p in papers:
        table.add_row(
            p.arxiv_id, 
            p.title or "Unknown", 
            f"v{p.last_known_version}", 
            str(p.last_checked.strftime("%Y-%m-%d %H:%M")) if p.last_checked else "Never"
        )
    console.print(table)

@app.command()
def check():
    """Check all watched papers for updates."""
    with console.status("Checking watched papers...", spinner="dots"):
        results = run_async(monitor.check_all_watched())
        
    for res in results:
        if res.get("error"):
            console.print(f"[red]Error checking {res['arxiv_id']}[/red]")
        elif res["has_update"]:
            console.print(f"[green]Updated {res['arxiv_id']} to v{res['new_version']}! (Generated logs saved)[/green]")
        else:
            console.print(f"[dim]No changes for {res['arxiv_id']} (v{res['old_version']})[/dim]")

@app.command()
def serve(port: int = typer.Option(8000, help="Port to run the API server on")):
    """Start the FastAPI server."""
    # We should run the watcher check on startup in background too as requested
    console.print("[bold cyan]Running startup watcher check...[/bold cyan]")
    run_async(monitor.check_all_watched())
    
    console.print(f"[bold cyan]Starting API server on port {port}...[/bold cyan]")
    uvicorn.run("api.server:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    app()
