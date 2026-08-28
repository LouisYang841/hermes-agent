#!/usr/bin/env python3
"""
Native Tavily Search Tool — no MCP, no Node.js, zero constant memory.

Calls Tavily REST API directly and returns results as JSON.
"""

import json
import urllib.request
import urllib.parse
import urllib.error

TOOLSET = "web"
TAVILY_API_KEY = "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"


def tavily_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_raw_content: bool = False,
) -> str:
    """Search the web using Tavily API.

    Args:
        query: The search query
        max_results: Number of results (1-20, default 5)
        search_depth: 'basic' for fast results, 'advanced' for deeper search
        include_raw_content: Include cleaned HTML content of results
    """
    url = "https://api.tavily.com/search"
    body = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": search_depth,
        "include_raw_content": include_raw_content,
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        # Return a clean readable format
        output = {"results": []}
        for r in result.get("results", []):
            output["results"].append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0),
            })
        output["total_results"] = result.get("total_results", 0)
        output["answer"] = result.get("answer", None)
        return json.dumps(output, indent=2, ensure_ascii=False)
    except urllib.error.HTTPError as e:
        return json.dumps({"error": f"HTTP {e.code}: {e.read().decode()}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# --- Registry ---
from tools.registry import registry

registry.register(
    name="tavily_search",
    toolset=TOOLSET,
    schema={
        "name": "tavily_search",
        "description": "Search the web using Tavily. Returns structured results with titles, URLs, and content snippets. Use this for general web searches, news, and research.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results (1-20, default 5)",
                    "default": 5,
                },
                "search_depth": {
                    "type": "string",
                    "enum": ["basic", "advanced"],
                    "description": "'basic' for fast results, 'advanced' for deeper/comprehensive search",
                    "default": "basic",
                },
                "include_raw_content": {
                    "type": "boolean",
                    "description": "Include cleaned HTML content of each result",
                    "default": False,
                },
            },
            "required": ["query"],
        },
    },
    handler=lambda args, **kw: tavily_search(
        query=args.get("query", ""),
        max_results=args.get("max_results", 5),
        search_depth=args.get("search_depth", "basic"),
        include_raw_content=args.get("include_raw_content", False),
    ),
    check_fn=lambda: bool(TAVILY_API_KEY),
    emoji="🔍",
)
