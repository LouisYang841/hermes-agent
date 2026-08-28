#!/usr/bin/env python3
"""
Native Brave Search Tool — no MCP, no Node.js, zero constant memory.

Calls Brave Search REST API directly and returns results as JSON.
Key restored from git history (config.yaml d6a6392, removed 2026-07-31
in the MCP→native-tool migration; brave never got its native replacement).
"""

import json
import urllib.error
import urllib.parse
import urllib.request

TOOLSET = "web"
BRAVE_API_KEY = "BSAWPNpHG2LMiZje_UgmU5gLotJO7xo"


def brave_search(
    query: str,
    count: int = 5,
    country: str = "all",
    search_lang: str = "",
) -> str:
    """Search the web using Brave Search API.

    Args:
        query: The search query
        count: Number of results (1-20, default 5)
        country: Country code for regional results (e.g. 'us', 'cn', 'all'; empty = unset)
        search_lang: Language code (e.g. 'zh-hans', 'zh-hant', 'en', 'ja'; empty = auto)
    """
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
        {k: v for k, v in {
            "q": query,
            "count": count,
            "country": country,
            "search_lang": search_lang,
        }.items() if v}
    )
    req = urllib.request.Request(
        url,
        headers={
            "X-Subscription-Token": BRAVE_API_KEY,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        # Return a clean readable format
        output = {"results": []}
        for r in result.get("web", {}).get("results", []):
            output["results"].append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "description": r.get("description", ""),
                }
            )
        output["total_results"] = len(output["results"])
        return json.dumps(output, indent=2, ensure_ascii=False)
    except urllib.error.HTTPError as e:
        return json.dumps({"error": f"HTTP {e.code}: {e.read().decode()}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


# --- Registry ---
from tools.registry import registry

registry.register(
    name="brave_search",
    toolset=TOOLSET,
    schema={
        "name": "brave_search",
        "description": "Search the web using Brave Search. Returns structured results with titles, URLs, and descriptions. Use for general web searches, news, and local/business queries.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results (1-20, default 5)",
                    "default": 5,
                },
                "country": {
                    "type": "string",
                    "description": "Country code for regional results (e.g. 'us', 'cn', 'all')",
                    "default": "all",
                },
                "search_lang": {
                    "type": "string",
                    "description": "Search language (e.g. 'zh', 'en', 'all')",
                    "default": "zh",
                },
            },
            "required": ["query"],
        },
    },
    handler=lambda args, **kw: brave_search(
        query=args.get("query", ""),
        count=args.get("count", 5),
        country=args.get("country", "all"),
        search_lang=args.get("search_lang", ""),
    ),
    check_fn=lambda: bool(BRAVE_API_KEY),
    emoji="🔍",
)
