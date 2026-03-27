import asyncio
import re
import httpx
import feedparser

# Global last request time to enforce 3s rate limit across async tasks
_last_request_time = 0.0

USER_AGENT = "arxiv-diff/0.1 (mailto:contact@arxiv-diff.dev)"

async def _throttle():
    global _last_request_time
    # Use asyncio to enforce at least 3 seconds between requests
    now = asyncio.get_event_loop().time()
    elapsed = now - _last_request_time
    if elapsed < 3.0:
        await asyncio.sleep(3.0 - elapsed)
    _last_request_time = asyncio.get_event_loop().time()


def _strip_version(arxiv_id: str) -> str:
    # "2301.00001v2" -> "2301.00001"
    return re.sub(r"v\d+$", "", arxiv_id)


async def get_paper_versions(arxiv_id: str) -> dict:
    base_id = _strip_version(arxiv_id)
    query_url = f"https://export.arxiv.org/api/query?id_list={base_id}"
    abs_url = f"https://arxiv.org/abs/{base_id}"

    await _throttle()
    
    # We fetch both simultaneously or sequentially? Sequential to keep it simple, but we must throttle between them.
    # The prompt implies 1 request per 3 seconds. So it's better to throttle each physical request.
    
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
        # 1. Fetch metadata via API
        api_resp = await client.get(query_url)
        api_resp.raise_for_status()
        
        feed = feedparser.parse(api_resp.text)
        if not feed.entries:
            raise ValueError(f"Paper not found: {base_id}")
        
        entry = feed.entries[0]
        title = entry.title.replace("\n", " ")
        abstract = entry.summary.replace("\n", " ").strip()
        authors = [author.name for author in entry.get("authors", [])]
        categories = [tag.term for tag in entry.get("tags", [])]
        
        await _throttle()
        
        # 2. Fetch versions from abstract page HTML
        abs_resp = await client.get(abs_url)
        abs_resp.raise_for_status()
        html = abs_resp.text
        
        # Updated pattern to be more robust to HTML tags between version number and date
        pattern = r"\[v(\d+)\].*?(\d+\s+\w+\s+\d+\s+[\d:]+\s+UTC)\s+\((.+?)\)"
        matches = re.findall(pattern, html, re.DOTALL)
        
        versions = []
        latest_version = 1
        for match in matches:
            v_num = int(match[0])
            date_str = match[1].strip()
            size_str = match[2].strip()
            versions.append({
                "version": v_num,
                "date": date_str,
                "size": size_str
            })
            if v_num > latest_version:
                latest_version = v_num
                
        # If no versions found through regex (maybe old paper), default to 1
        if not versions:
            versions = [{"version": 1, "date": "Unknown", "size": "Unknown"}]
            
        pdf_base_url = f"https://arxiv.org/pdf/{base_id}"
        
        return {
            "id": base_id,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "categories": categories,
            "latest_version": latest_version,
            "versions": versions,
            "pdf_base_url": pdf_base_url
        }


async def download_pdf(arxiv_id_with_version: str) -> bytes:
    await _throttle()
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id_with_version}"
    
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client:
        resp = await client.get(pdf_url, follow_redirects=True, timeout=60.0)
        resp.raise_for_status()
        return resp.content
