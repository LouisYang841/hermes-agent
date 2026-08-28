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

    ``str_replace_editor`` is a multi-command tool (view / create /
    str_replace / insert); each command routes to the matching Hermes tool:
    view -> read_file, create -> write_file, str_replace -> patch,
    insert -> terminal+python (Hermes patch has no insert mode).
    """
    if not getattr(agent, "dsh_minimal_mode", False):
        return name, args
    real = DSH_TOOL_ALIASES.get(name)
    if real is None:
        return name, args
    if name == "bash":
        return "terminal", args
    if name == "str_replace_editor":
        return _resolve_editor_call(args)
    return name, args


def _resolve_editor_call(args: dict) -> Tuple[str, dict]:
    import shlex

    args = dict(args or {})
    cmd = (args.get("command") or "").strip()
    path = args.get("path") or ""

    if cmd == "view":
        vr = args.get("view_range") or None
        if isinstance(vr, list) and len(vr) == 2:
            start, end = int(vr[0]), int(vr[1])
            if end == -1:
                return "read_file", {"path": path, "offset": start, "limit": 2000}
            return "read_file", {"path": path, "offset": start, "limit": max(1, end - start + 1)}
        return "read_file", {"path": path}

    if cmd == "create":
        return "write_file", {"path": path, "content": args.get("file_text") or ""}

    if cmd == "str_replace":
        return "patch", {
            "mode": "replace",
            "path": path,
            "old_string": args.get("old_str") or "",
            "new_string": args.get("new_str") or "",
        }

    if cmd == "insert":
        line = int(args.get("insert_line") or 0)
        text = args.get("new_str") or ""
        script = (
            "import sys;"
            f"p={shlex.quote(path)};"
            f"n={line};"
            f"t={shlex.quote(text)};"
            "ls=open(p).read().splitlines(keepends=True);"
            "ls.insert(n, t if t.endswith(chr(10)) else t+chr(10));"
            "open(p,'w').writelines(ls)"
        )
        return "terminal", {"command": f"python3 -c {shlex.quote(script)}"}

    # Unknown/missing command: degrade to a read so the model can recover.
    return "read_file", {"path": path}


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


# Exact DEFAULT_DESCRIPTION from DeepSeek Harness
# packages/fs/tool-str-replace-editor/src/index.ts (verified 2026-08-28).
DSH_EDITOR_DESCRIPTION = """Custom editing tool for viewing, creating and editing files
* State is persistent across command calls and discussions with the user
* If `path` is a file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
* The `create` command cannot be used if the specified `path` already exists as a file
* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
* A null placeholder for a parameter unused by the selected command is treated as omitted. Required parameters still need values; omit `str_replace.new_str` rather than setting it to null when deleting a match

Notes for using the `str_replace` command:
* The `old_str` parameter should match EXACTLY one or more consecutive lines from the original file. Be mindful of whitespaces!
* If the `old_str` parameter is not unique in the file, the replacement will not be performed. Make sure to include enough context in `old_str` to make it unique
* The `new_str` parameter should contain the edited lines that should replace the `old_str`"""


def _editor_schema() -> Dict[str, Any]:
    """Exact DeepSeek Harness str_replace_editor schema (multi-command:
    view / create / str_replace / insert).  Verified against
    packages/fs/tool-str-replace-editor/src/index.ts registerStrReplaceEditor."""
    return {
        "type": "function",
        "function": {
            "name": "str_replace_editor",
            "description": DSH_EDITOR_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "enum": ["view", "create", "str_replace", "insert"],
                        "description": "The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`.",
                    },
                    "path": {
                        "type": "string",
                        "description": "Absolute path to file or directory, e.g. `/repo/file.py` or `/repo`.",
                    },
                    "file_text": {
                        "oneOf": [{"type": "string"}, {"type": "null"}],
                        "description": "Required string parameter of `create` command, with the content of the file to be created. A null placeholder is treated as omitted by commands that do not use this parameter.",
                    },
                    "insert_line": {
                        "oneOf": [{"type": "integer"}, {"type": "null"}],
                        "description": "Required integer parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`. A null placeholder is treated as omitted by commands that do not use this parameter.",
                    },
                    "new_str": {
                        "oneOf": [{"type": "string"}, {"type": "null"}],
                        "description": "Optional string parameter of `str_replace` command containing the new string (if omitted, no string will be added). Required string parameter of `insert` command containing the string to insert. A null placeholder is accepted only by commands that do not use this parameter.",
                    },
                    "old_str": {
                        "oneOf": [{"type": "string"}, {"type": "null"}],
                        "description": "Required string parameter of `str_replace` command containing the string in `path` to replace. A null placeholder is treated as omitted by commands that do not use this parameter.",
                    },
                    "view_range": {
                        "oneOf": [{"type": "array", "items": {"type": "integer"}}, {"type": "null"}],
                        "description": "Optional parameter of `view` command when `path` points to a file. If omitted or null, the full file is shown. If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to start. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.",
                    },
                },
                "required": ["command", "path"],
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
