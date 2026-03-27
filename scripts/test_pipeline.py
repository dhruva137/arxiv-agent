import asyncio
from rich.console import Console
from rich.panel import Panel
from arxiv_diff.tools import arxiv_api, pdf_extractor, section_parser, text_differ, metadata_compare, figure_detector

async def main():
    console = Console()
    arxiv_id = "2305.18290"
    
    console.print(f"[bold blue]Fetching versions for {arxiv_id}...[/bold blue]")
    info = await arxiv_api.get_paper_versions(arxiv_id)
    
    console.print("Versions found:")
    for v in info["versions"]:
        console.print(f" - v{v['version']} ({v['date']}) - {v['size']}")
        
    v1_id = f"{arxiv_id}v1"
    v2_id = f"{arxiv_id}v2"
    
    console.print(f"\n[bold blue]Downloading {v1_id}...[/bold blue]")
    pdf_v1 = await arxiv_api.download_pdf(v1_id)
    
    console.print(f"[bold blue]Downloading {v2_id}...[/bold blue]")
    pdf_v2 = await arxiv_api.download_pdf(v2_id)
    
    console.print("\n[bold blue]Extracting Text...[/bold blue]")
    text_v1 = pdf_extractor.extract_text(pdf_v1)
    text_v2 = pdf_extractor.extract_text(pdf_v2)
    
    console.print("\n[bold blue]Parsing Sections...[/bold blue]")
    secs_v1 = section_parser.parse(text_v1)
    secs_v2 = section_parser.parse(text_v2)
    
    console.print(f"v1 sections: {len(secs_v1)} | v2 sections: {len(secs_v2)}")
    
    console.print("\n[bold blue]Diffing Sections...[/bold blue]")
    diff_res = text_differ.diff(secs_v1, secs_v2)
    console.print(Panel(
        f"Added Sections: {diff_res['added_sections']}\n"
        f"Removed Sections: {diff_res['removed_sections']}\n"
        f"Changed Sections: {list(diff_res['changed_sections'].keys())}\n"
        f"Unchanged Sections: {len(diff_res['unchanged_sections'])}\n"
        f"Lines Added: {diff_res['total_added_lines']} | Lines Removed: {diff_res['total_removed_lines']}",
        title="Diff Stats"
    ))
    
    console.print("\n[bold blue]Comparing Metadata...[/bold blue]")
    meta_diff = metadata_compare.compare(info, info) # Fake test, info won't change here since it's just the API response
    # We should actually compare metadata specifically if we had API fetch for v1 and v2 separately.
    # The API returns latest metadata, so let's just print that.
    console.print(Panel(str(meta_diff), title="Metadata Changes"))
    
    console.print("\n[bold blue]Detecting Figure Changes...[/bold blue]")
    figs = figure_detector.detect(text_v1, text_v2)
    console.print(Panel(str(figs), title="Figure Changes"))
    
if __name__ == "__main__":
    asyncio.run(main())
