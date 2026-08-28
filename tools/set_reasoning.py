"""
set_reasoning — model self-adjustable reasoning depth.

Lets the model raise/lower its own thinking effort mid-task (Louis's
"i need to think harder" tool). The model calls this when it judges the
current task needs deeper reasoning, then lowers it back when done.

Mechanics (verified against the running gateway architecture):
- Session-scoped override: the handler stores the level in this module's
  `_SESSION_OVERRIDES[session_key]`, and gateway/run.py
  `_resolve_session_reasoning_config()` consults it every turn (priority:
  manual /reasoning override > set_reasoning override > per-model > global).
  No config.yaml writes, no cross-session side effects.
- Live agent mutation: the running agent (registered via a tiny hook in
  agent/tool_executor.py) gets its `reasoning_config` updated so the
  CURRENT turn's continuation — the LLM call right after this tool
  returns — already uses the new level.
- Per-request reads go through `agent.reasoning_config` at build time
  (agent/chat_completion_helpers.py), so no agent re-init, no system
  prompt change, provider prefix cache unaffected.

Safety:
- Model self-adjustment is capped at "high"; xhigh/max stay manual
  (/reasoning ... --global).
- The tool is harmless on models without reasoning support — the level is
  simply ignored by those transports.
"""

import json
import threading

from tools.registry import registry

TOOLSET = "core"

# session_id -> running agent, registered by the tool_executor.py hook.
_AGENTS: dict[str, object] = {}
_AGENTS_LOCK = threading.Lock()

# session_key -> {"enabled": True, "effort": level} — consulted by the
# gateway's _resolve_session_reasoning_config() each turn.
_SESSION_OVERRIDES: dict[str, dict] = {}
_SESSION_LOCK = threading.Lock()

# Model self-adjustment cap. xhigh/max are owner-manual only.
VALID_LEVELS = ("low", "medium", "high")


def register_agent(agent: object) -> None:
    """Called from agent/tool_executor.py right before tool dispatch."""
    sid = getattr(agent, "session_id", "") or ""
    if not sid:
        return
    with _AGENTS_LOCK:
        _AGENTS[sid] = agent


def _live_agent(session_id: str):
    with _AGENTS_LOCK:
        return _AGENTS.get(session_id)


def set_session_override(session_key: str, level: str, baseline: str | None = None) -> None:
    """Store the session-scoped reasoning override (gateway reads this).

    ``baseline`` is the effective level before this call — the restore hook
    uses it to return the session to its default when the turn ends.
    """
    if not session_key:
        return
    with _SESSION_LOCK:
        _SESSION_OVERRIDES[session_key] = {
            "enabled": True,
            "effort": level,
            "baseline": baseline,
        }


def get_session_override(session_key: str):
    """Return the stored override for a session, or None (wire shape)."""
    if not session_key:
        return None
    with _SESSION_LOCK:
        entry = _SESSION_OVERRIDES.get(session_key)
        if not entry:
            return None
        return {"enabled": True, "effort": entry.get("effort", "medium")}


def clear_session_override(session_key: str) -> None:
    with _SESSION_LOCK:
        _SESSION_OVERRIDES.pop(session_key, None)


def restore_session_override(session_key: str) -> None:
    """Turn-scoped restore — called by the gateway when a turn ends.

    Pops the session override and resets the live agent's reasoning_config
    to the baseline captured when the override was set. If no baseline was
    captured, falls back to the global config resolution. Idempotent —
    cheap no-op when no override exists for the session.
    """
    if not session_key:
        return
    with _SESSION_LOCK:
        entry = _SESSION_OVERRIDES.pop(session_key, None)
    if entry is None:
        return
    agent = _live_agent(session_key)
    if agent is None:
        return
    baseline = entry.get("baseline")
    if baseline:
        try:
            setattr(agent, "reasoning_config", {"enabled": True, "effort": baseline})
            return
        except Exception:
            pass
    # No baseline — resolve the global effective config.
    try:
        from hermes_constants import resolve_reasoning_config
        from gateway.run import _load_gateway_runtime_config

        resolved = resolve_reasoning_config(
            _load_gateway_runtime_config(),
            str(getattr(agent, "model", "") or ""),
        )
        setattr(agent, "reasoning_config", resolved)
    except Exception:
        try:
            setattr(agent, "reasoning_config", None)
        except Exception:
            pass


def set_reasoning(level: str, reason: str = "", session_id: str = "") -> str:
    """Adjust the model's own reasoning effort.

    Args:
        level: Target effort. One of: low, medium, high (capped for
            self-adjustment; xhigh/max are manual only).
        reason: Short human-readable note on why the level changed. Shown
            to the user in the tool result.
        session_id: The dispatcher-provided session id (kwargs), used to
            find the live agent for immediate mid-turn effect.
    """
    level = str(level or "").strip().lower()
    if level not in VALID_LEVELS:
        return json.dumps(
            {
                "success": False,
                "error": f"Invalid level '{level}'. Valid levels: {', '.join(VALID_LEVELS)}",
            }
        )

    # Session-scoped override — consulted by the gateway every turn.
    if not session_id:
        try:
            from tools.approval import get_current_session_key

            session_id = get_current_session_key("")
        except Exception:
            pass
    set_session_override(session_id, level)

    # Live agent mutation — immediate effect on this turn's continuation.
    live_updated = False
    agent = _live_agent(session_id)
    if agent is not None:
        try:
            current = getattr(agent, "reasoning_config", None) or {}
            merged = dict(current) if isinstance(current, dict) else {}
            merged["enabled"] = True
            merged["effort"] = level
            setattr(agent, "reasoning_config", merged)
            live_updated = True
        except Exception:
            pass

    return json.dumps(
        {
            "success": True,
            "level": level,
            "reason": reason,
            "scope": "session" if session_id else "unscoped",
            "live_agent_updated": live_updated,
            "note": f"Reasoning effort for this session is now '{level}'. "
            "Lower it back when the hard part is done.",
        },
        ensure_ascii=False,
    )


registry.register(
    name="set_reasoning",
    toolset=TOOLSET,
    schema={
        "name": "set_reasoning",
        "description": (
            "Adjust your own reasoning/thinking effort mid-task. "
            "Use this when the current task needs deeper analysis than your "
            "current level allows (multi-step reasoning, complex math or code, "
            "ambiguous requirements), then use it again to lower back to 'low' "
            "or 'medium' once the hard part is done. "
            "Do NOT call for simple requests — default effort is fine there. "
            "Self-adjustment is capped at 'high'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Target reasoning effort.",
                },
                "reason": {
                    "type": "string",
                    "description": "Short note on why the level changed (shown to the user).",
                },
            },
            "required": ["level"],
        },
    },
    handler=lambda args, **kw: set_reasoning(
        level=args.get("level", ""),
        reason=args.get("reason", ""),
        session_id=kw.get("session_id", ""),
    ),
)
