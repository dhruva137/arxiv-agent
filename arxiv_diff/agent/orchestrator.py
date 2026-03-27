import json
import traceback
from typing import Callable, Any
from rich.console import Console

import ollama

from arxiv_diff.config import settings
from arxiv_diff.tools import arxiv_api, pdf_extractor, section_parser, text_differ, metadata_compare, figure_detector
from arxiv_diff.agent.prompts import SYSTEM_PROMPT, SIGNIFICANCE_PROMPT

class ArxivDiffAgent:
    def __init__(self, callback: Callable[[str], None] | None = None):
        # Using Ollama AsyncClient
        self.client = ollama.AsyncClient(host=settings.ollama_host)
        self.model = settings.ollama_model
        self.callback = callback
        self.console = Console()
        
    def _log(self, msg: str):
        self.console.print(f"[bold magenta]Agent:[/bold magenta] {msg}")
        if self.callback:
            self.callback(msg)

    async def _analyze_change_significance_inner(self, section_name: str, paper_context: str, diff_text: str) -> dict:
        prompt = SIGNIFICANCE_PROMPT.format(
            section_name=section_name,
            paper_context=paper_context,
            diff_text=diff_text
        )
        
        response = await self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert academic reviewer. You only output valid JSON."},
                {"role": "user", "content": prompt}
            ],
            format="json"
        )
        content = response['message']['content']
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Fallback parsing
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1:
                try:
                    return json.loads(content[start_idx:end_idx+1])
                except:
                    pass
        return {"overall_significance": "SUBSTANTIVE", "changes": [{"description": "Failed to parse LLM analysis", "significance": "SUBSTANTIVE", "detail": None}], "likely_reviewer_response": False, "reasoning": "Parse Error"}

    def _get_tool_definitions(self):
        # Ollama/OpenAI format
        return [
            {
                "type": "function",
                "function": {
                    "name": "fetch_paper_versions",
                    "description": "Get the version history and metadata for an arxiv ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {"arxiv_id": {"type": "string"}},
                        "required": ["arxiv_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "download_and_extract_pdf",
                    "description": "Download a specific arxiv version (e.g. 2305.18290v1) and extract its text.",
                    "parameters": {
                        "type": "object",
                        "properties": {"arxiv_id_with_version": {"type": "string"}},
                        "required": ["arxiv_id_with_version"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "parse_sections",
                    "description": "Parse the full document text into semantic sections.",
                    "parameters": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "diff_sections",
                    "description": "Compare two dictionaries of sections to find changes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sections_v1": {"type": "object"},
                            "sections_v2": {"type": "object"}
                        },
                        "required": ["sections_v1", "sections_v2"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "compare_metadata",
                    "description": "Compare two sets of metadata (from fetch_paper_versions).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "meta_v1": {"type": "object"},
                            "meta_v2": {"type": "object"}
                        },
                        "required": ["meta_v1", "meta_v2"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_change_significance",
                    "description": "Ask the LLM to analyze the significance of a section's diff.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "section_name": {"type": "string"},
                            "paper_context": {"type": "string"},
                            "diff_text": {"type": "string"}
                        },
                        "required": ["section_name", "paper_context", "diff_text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_figure_changes",
                    "description": "Detect added/removed figures and tables from paper text.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text_v1": {"type": "string"},
                            "text_v2": {"type": "string"}
                        },
                        "required": ["text_v1", "text_v2"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_changelog",
                    "description": "Generate the final formatted markdown changelog based on all accumulated findings.",
                    "parameters": {
                        "type": "object",
                        "properties": {"data": {"type": "string", "description": "All your findings formatted as a string to be written out."}},
                        "required": ["data"]
                    }
                }
            }
        ]

    async def _execute_tool(self, name: str, input_data: dict) -> Any:
        try:
            if name == "fetch_paper_versions":
                return await arxiv_api.get_paper_versions(input_data["arxiv_id"])
            elif name == "download_and_extract_pdf":
                pdf_bytes = await arxiv_api.download_pdf(input_data["arxiv_id_with_version"])
                return pdf_extractor.extract_text(pdf_bytes)
            elif name == "parse_sections":
                return section_parser.parse(input_data["text"])
            elif name == "diff_sections":
                return text_differ.diff(input_data["sections_v1"], input_data["sections_v2"])
            elif name == "compare_metadata":
                return metadata_compare.compare(input_data["meta_v1"], input_data["meta_v2"])
            elif name == "analyze_change_significance":
                return await self._analyze_change_significance_inner(
                    input_data["section_name"],
                    input_data["paper_context"],
                    input_data["diff_text"]
                )
            elif name == "detect_figure_changes":
                return figure_detector.detect(input_data["text_v1"], input_data["text_v2"])
            elif name == "generate_changelog":
                return input_data["data"]
            else:
                return f"Error: Unknown tool '{name}'"
        except Exception as e:
            return f"Error executing {name}: {str(e)}\n{traceback.format_exc()}"

    def _truncate(self, data: str) -> str:
        if len(data) > 50000:
            return data[:25000] + "\n... [truncated] ...\n" + data[-25000:]
        return data

    async def run(self, query: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]
        tools = self._get_tool_definitions()
        
        self._log(f"Starting ReAct loop using {self.model}")
        for i in range(20):
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                tools=tools
            )
            
            msg = response['message']
            messages.append(msg)
            
            if not msg.get('tool_calls'):
                # Agent decided it's done
                return msg.get('content', "No response generated.")
                
            for tool_call in msg['tool_calls']:
                name = tool_call['function']['name']
                args = tool_call['function']['arguments']
                
                self._log(f"Calling {name}")
                res = await self._execute_tool(name, args)
                
                if isinstance(res, dict) or isinstance(res, list):
                    res_str = json.dumps(res)
                else:
                    res_str = str(res)
                    
                res_str = self._truncate(res_str)
                
                messages.append({
                    "role": "tool",
                    "content": res_str
                })
            
        return "Error: Agent exceeded maximum iterations (20)"
