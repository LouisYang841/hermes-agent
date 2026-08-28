"""DSH Minimal Mode shim for Hermes.

Replicates the DeepSeek Harness "minimal" agent preset inside Hermes so
reasoning models trained under that scaffold (deepseek-v4-pro-0813) get the
CoT anchor they were RL-trained on:

* API-level system prompt = exactly the minimal preset's fixed persona
  ("You are a helpful software engineer assistant."), nothing else.
* API-level tools = exactly the two-tool composition: persistent bash +
  str_replace_editor (names match the model's training distribution).
* The full Hermes system prompt + complete tool schema catalog is carried
  in the message body (first user message) as an operating manual, so the
  model can still use every tool by name.

Design notes (verified 2026-08-28):

* Cache-safe: the outer system prompt and the 2-tool schema are byte-stable
  for the life of a conversation; the manual block sits in the first user
  message, replayed verbatim from history every turn (same bytes).
* The 2 declared tools are aliases: "bash" -> terminal handler,
  "str_replace_editor" -> patch handler.  Alias resolution happens at the
  single dispatch choke point (_invoke_tool in run_agent.py), so every
  downstream layer (approval, hooks, guardrails, arg coercion) sees the
  real tool name.
* valid_tool_names stays the FULL Hermes set, so the model can call any
  registered tool by name even though only 2 schemas are declared.
  (PoC: DeepSeek API passes through undeclared tool names — both
  deepseek-v4-pro and deepseek-v4-flash emitted a valid undeclared
  web_search tool_call under this exact framing.)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

DSH_MINIMAL_SYSTEM_PROMPT = "You are a helpful software engineer assistant."

DSH_MANUAL_HEADER = "=== HERMES OPERATING MANUAL ==="

# DSH minimal tool names -> Hermes tool names (dispatch aliases).
DSH_TOOL_ALIASES = {
    "bash": "terminal",
    "str_replace_editor": "patch",
}


def resolve_dsh_tool_call(agent: Any, name: str, args: dict) -> Tuple[str, dict]:
    """Translate a DSH-alias tool call to the real Hermes tool.

    No-op when the mode is off or the name isn't an alias.  Called from
    ``run_agent.AIAgent._invoke_tool`` — the single dispatch choke point —
    so every downstream layer sees the real tool name.
    """
    if not getattr(agent, "dsh_minimal_mode", False):
        return name, args
    real = DSH_TOOL_ALIASES.get(name)
    if real is None:
        return name, args
    if real == "patch" and isinstance(args, dict):
        args = dict(args)
        args.setdefault("mode", "replace")  # patch requires mode
        args.pop("view_range", None)        # DSH editor-only param
    return real, args


def _bash_schema() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Run commands in a bash shell\n"
                "* When invoking this tool, the contents of the \"command\" parameter does NOT need to be XML-escaped.\n"
                "* You don't have access to the internet via this tool.\n"
                "* You do have access to a mirror of common linux and python packages via apt and pip.\n"
                "* State is persistent across command calls and discussions with the user.\n"
                "* To inspect a particular line range of a file, e.g. lines 10-25, try 'sed -n 10,25p /path/to/the/file'.\n"
                "* Please avoid commands that may produce a very large amount of output.\n"
                "* Please run long lived commands in the background, e.g. 'sleep 10 &' or start a server in the background."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The bash command to run."},
                },
                "required": ["command"],
            },
        },
    }


def _editor_schema() -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "str_replace_editor",
            "description": (
                "Edit files on disk using exact string replacement (mirrors the DeepSeek Harness "
                "minimal-preset editor). Paths must be absolute. old_string must match exactly one "
                "occurrence in the file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to the file to edit."},
                    "old_string": {"type": "string", "description": "Exact text to replace (must appear exactly once)."},
                    "new_string": {"type": "string", "description": "Replacement text."},
                    "view_range": {"type": "array", "items": {"type": "integer"}, "description": "Optional [start, end] line range to view."},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    }


def minimal_tool_schemas() -> List[Dict[str, Any]]:
    return [_bash_schema(), _editor_schema()]


def apply_dsh_minimal_mode(agent: Any) -> bool:
    """Shrink the DECLARED tool schema to the DSH pair and stash the full
    definitions for the body manual.  Returns True when the mode is on and
    was applied; False otherwise (no-op).  Called from agent_init after the
    tools/valid_tool_names snapshot.
    """
    try:
        from hermes_cli.config import load_config as _lc
        _cfg = _lc()
        on = bool((_cfg.get("agent", {}) or {}).get("dsh_minimal_mode", False))
    except Exception:
        on = False
    agent.dsh_minimal_mode = bool(on)
    if not on:
        agent._dsh_full_tool_defs = []
        return False

    full = list(getattr(agent, "tools", None) or [])
    agent._dsh_full_tool_defs = full

    # The model may call ANY registered tool by name (undeclared) -> keep the
    # FULL valid set so validation + dispatch accept every tool.
    agent.valid_tool_names = {t["function"]["name"] for t in full} | set(DSH_TOOL_ALIASES)

    agent.tools = minimal_tool_schemas()
    return True


def compose_dsh_manual(agent: Any) -> str:
    """Full Hermes system prompt + complete tool schemas, framed as an
    operating manual.  Cached on the agent; byte-stable across turns."""
    cached = getattr(agent, "_dsh_manual_cache", None)
    if cached:
        return cached
    sp = getattr(agent, "_cached_system_prompt", None) or ""
    full = getattr(agent, "_dsh_full_tool_defs", None) or []
    schema_block = json.dumps(full, indent=2, ensure_ascii=False) if full else "(none)"
    manual = (
        f"{DSH_MANUAL_HEADER}\n\n"
        "The following document describes your operating environment: behavioral "
        "instructions and the complete catalog of tools available in this environment. "
        "Every tool in the catalog can be called by name even if its schema is not "
        "declared in the tool list; when you need a tool, emit a tool_call with the "
        "exact name and a JSON arguments object following its schema.\n\n"
        "## BEHAVIORAL INSTRUCTIONS\n"
        f"{sp}\n\n"
        "## COMPLETE TOOL SCHEMAS\n"
        f"{schema_block}\n\n"
        "## TOOL ALIASES\n"
        "- 'bash' is an alias for 'terminal' (run commands in a persistent shell).\n"
        "- 'str_replace_editor' is an alias for 'patch' (string-replace file edits; "
        "its 'view_range' parameter is ignored).\n"
    )
    agent._dsh_manual_cache = manual
    return manual
