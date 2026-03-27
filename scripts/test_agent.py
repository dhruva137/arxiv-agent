import asyncio
from rich.console import Console
from rich.markdown import Markdown
from arxiv_diff.agent.orchestrator import ArxivDiffAgent

async def main():
    console = Console()
    agent = ArxivDiffAgent(callback=lambda msg: console.print(f"[dim]{msg}[/dim]"))
    
    query1 = "What changed in 2305.18290?"
    console.print(f"\n[bold green]Running Query:[/bold green] {query1}")
    try:
        res1 = await agent.run(query1)
        console.print(Markdown(res1))
    except Exception as e:
        console.print(f"[bold red]Agent Error:[/bold red] {e}")

    query2 = "What changed in 2301.13688?"
    console.print(f"\n[bold green]Running Query:[/bold green] {query2}")
    try:
        res2 = await agent.run(query2)
        console.print(Markdown(res2))
    except Exception as e:
        console.print(f"[bold red]Agent Error:[/bold red] {e}")

if __name__ == "__main__":
    asyncio.run(main())
