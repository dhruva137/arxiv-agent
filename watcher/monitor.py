import httpx
from rich.console import Console

from db import store
from arxiv_diff.tools import arxiv_api
from arxiv_diff.agent.orchestrator import ArxivDiffAgent

console = Console()

async def check_all_watched() -> list[dict]:
    results = []
    papers = store.get_watched_papers()
    
    if not papers:
        return results
        
    for p in papers:
        arxiv_id = p.arxiv_id
        old_v = p.last_known_version
        
        try:
            info = await arxiv_api.get_paper_versions(arxiv_id)
            current_v = info.get("latest_version", 1)
            
            if current_v > old_v:
                # Update found
                console.print(f"[bold green]Update found for {arxiv_id}: v{old_v} -> v{current_v}[/bold green]")
                
                # Run agent
                agent = ArxivDiffAgent()
                query = f"What changed in {arxiv_id} between v{old_v} and v{current_v}?"
                res = await agent.run(query)
                
                log_data = {
                    "arxiv_id": arxiv_id,
                    "version_from": old_v,
                    "version_to": current_v,
                    "severity": "UNKNOWN",
                    "tldr": "See full markdown",
                    "changelog_markdown": res,
                    "changelog_json": None
                }
                
                store.save_changelog(log_data)
                store.update_last_checked(arxiv_id, current_v)
                
                if p.webhook_url:
                    try:
                        async with httpx.AsyncClient() as client:
                            await client.post(p.webhook_url, json={"arxiv_id": arxiv_id, "changelog": res})
                    except Exception as we:
                        console.print(f"[yellow]Webhook failed for {arxiv_id}: {we}[/yellow]")
                        
                results.append({"arxiv_id": arxiv_id, "has_update": True, "old_version": old_v, "new_version": current_v})
            else:
                store.update_last_checked(arxiv_id, current_v)
                results.append({"arxiv_id": arxiv_id, "has_update": False, "old_version": old_v, "new_version": current_v})
                
        except Exception as e:
            console.print(f"[bold red]Error checking {arxiv_id}:[/bold red] {e}")
            results.append({"arxiv_id": arxiv_id, "has_update": False, "error": str(e)})
            
    return results
