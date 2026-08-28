#!/usr/bin/env python3
"""
Native Octen Search Tool — no MCP, no Node.js, zero constant memory.

Wraps the existing ~/.hermes/scripts/octen.py logic as a native Hermes tool.
"""

import json
import os
import sys
import urllib.request
import urllib.error

TOOLSET = "web"
API_KEY = "octen-63ddd37852e44eab9ca5d10decbb4089"
BASE = "https://api.octen.ai"


def _post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-API-Key": API_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}"}
    except Exception as e:
        return {"error": str(e)}


def octen_search(query: str, count: int = 5, time_range: str | None = None) -> str:
    """Search the web using Octen AI.

    Args:
        query: The search query
        count: Number of results (default 5)
        time_range: Optional time filter: day, week, month, year
    """
    body = {"query": query, "count": count}
    if time_range:
        body["time_range"] = time_range
    result = _post("/search", body)
    if "error" in result:
        return json.dumps(result)
    return json.dumps(result, indent=2, ensure_ascii=False)


def octen_extract(urls: list) -> str:
    """Extract content from URLs using Octen.

    Args:
        urls: List of URLs to extract content from
    """
    result = _post("/extract", {"urls": urls})
    if "error" in result:
        return json.dumps(result)
    return json.dumps(result, indent=2, ensure_ascii=False)


# --- Registry ---
from tools.registry import registry

registry.register(
    name="octen_search",
    toolset=TOOLSET,
    schema={
        "name": "octen_search",
        "description": "Search the web using Octen AI. Free-tier search with no credit card needed. Good for general web searches.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results (default 5)",
                    "default": 5,
                },
                "time_range": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "Optional time range filter",
                },
            },
            "required": ["query"],
        },
    },
    handler=lambda args, **kw: octen_search(
        query=args.get("query", ""),
        count=args.get("count", 5),
        time_range=args.get("time_range"),
    ),
    check_fn=lambda: bool(API_KEY),
    emoji="🔎",
)

registry.register(
    name="octen_extract",
    toolset=TOOLSET,
    schema={
        "name": "octen_extract",
        "description": "Extract readable content from one or more URLs using Octen. Returns the page content as markdown.",
        "parameters": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to extract content from",
                },
            },
            "required": ["urls"],
        },
    },
    handler=lambda args, **kw: octen_extract(
        urls=args.get("urls", []),
    ),
    check_fn=lambda: bool(API_KEY),
    emoji="📄",
)
