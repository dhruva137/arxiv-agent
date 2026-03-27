from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from db import store
from arxiv_diff.tools import arxiv_api
from arxiv_diff.agent.orchestrator import ArxivDiffAgent

router = APIRouter()

class DiffRequest(BaseModel):
    arxiv_id: str
    v1: Optional[int] = None
    v2: Optional[int] = None

class WatchRequest(BaseModel):
    arxiv_id: str
    webhook_url: Optional[str] = None

@router.get("/versions/{arxiv_id}")
async def get_versions(arxiv_id: str):
    try:
        info = await arxiv_api.get_paper_versions(arxiv_id)
        return {
            "id": info["id"],
            "title": info["title"],
            "authors": info["authors"],
            "versions": [{"version": v["version"], "date": v["date"], "size": v["size"]} for v in info["versions"]]
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/diff")
async def generate_diff(req: DiffRequest):
    try:
        # Resolve versions
        info = await arxiv_api.get_paper_versions(req.arxiv_id)
        latest = info.get("latest_version", 1)
        
        v_to = req.v2 if req.v2 is not None else latest
        v_from = req.v1 if req.v1 is not None else max(1, v_to - 1)
        
        if v_from == v_to:
            raise ValueError("v1 and v2 must be different")
            
        # Check cache
        cached = store.get_changelog(info["id"], v_from, v_to)
        if cached:
            return {**cached, "cached": True}
            
        # Not cached, run agent
        agent = ArxivDiffAgent()
        query = f"What changed in {info['id']} between v{v_from} and v{v_to}?"
        res = await agent.run(query)
        
        # We need to save to DB. The agent returns a markdown string.
        # Ideally the agent should return the structured JSON too, but the prompt says 
        # "Your final response... should be the formatted changelog markdown."
        # For db caching, we just store the markdown text as tldr/changelog_markdown.
        
        log_data = {
            "arxiv_id": info["id"],
            "version_from": v_from,
            "version_to": v_to,
            "severity": "UNKNOWN",  # Hard to extract strictly without parsing the markdown or getting JSON output
            "tldr": "See full markdown",
            "changelog_markdown": res,
            "changelog_json": None
        }
        
        store.save_changelog(log_data)
        
        return {
            "arxiv_id": info["id"],
            "version_from": v_from,
            "version_to": v_to,
            "severity": "UNKNOWN",
            "tldr": "See full markdown",
            "changelog_markdown": res,
            "cached": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/changelog/{arxiv_id}")
def get_changelogs(arxiv_id: str):
    return store.get_all_changelogs(arxiv_id)

@router.post("/watch")
def watch_paper(req: WatchRequest):
    success = store.add_watched_paper(req.arxiv_id, req.webhook_url)
    if not success:
        raise HTTPException(status_code=400, detail="Paper already watched")
    return {"status": "success", "arxiv_id": req.arxiv_id}

@router.get("/watched")
def list_watched():
    papers = store.get_watched_papers()
    return [{"arxiv_id": p.arxiv_id, "title": p.title, "last_known_version": p.last_known_version} for p in papers]

@router.delete("/watch/{arxiv_id}")
def unwatch_paper(arxiv_id: str):
    success = store.remove_watched_paper(arxiv_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper not found in watched list")
    return {"status": "removed", "arxiv_id": arxiv_id}
