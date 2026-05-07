"""Shared policy configuration loader."""

from __future__ import annotations

from typing import Any, Dict

DEFAULT_POLICY_CONFIG: Dict[str, Any] = {
    "mode": "configurable_rbac",
    "cli_superuser": True,
    "fail_open_when_profile_missing": True,
    "invalid_agent_behavior": {
        "cli": "fallback_owner",
        "gateway": "deny",
        "web": "fallback_shared",
        "api_server": "deny",
    },
    "break_glass": {
        "enabled": False,
        "allow_shared_fallback_for_owner": True,
    },
    "audit": {
        "log_denies": True,
        "log_all_fallbacks": True,
    },
    "roles": {
        "owner": {"allow": ["*"], "deny": []},
        "trusted": {"allow": ["*"], "deny": ["terminal", "execute_code", "delegate_task"]},
        "guest": {
            "allow": [
                "clarify",
                "memory",
                "session_search",
                "skill_view",
                "skills_list",
                "todo",
                "read_file",
                "search_files",
            ],
            "deny": [],
        },
    },
}


def _deep_merge(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in incoming.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_policy_config() -> Dict[str, Any]:
    policy = dict(DEFAULT_POLICY_CONFIG)
    try:
        from hermes_cli.config import load_config

        cfg = load_config() or {}
        sec = cfg.get("security") if isinstance(cfg, dict) else {}
        pol = sec.get("policy") if isinstance(sec, dict) else {}
        if isinstance(pol, dict):
            policy = _deep_merge(policy, pol)
    except Exception:
        pass
    return policy

