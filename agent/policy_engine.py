"""Central policy engine for role-based tool authorization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path

from agent.actions import ACTION_TOOL_INVOKE_PREFIX
from agent.policy_config import load_policy_config, DEFAULT_POLICY_CONFIG


@dataclass(frozen=True)
class PolicyDecision:
    allow: bool
    reason: str
    code: str


class PolicyEngine:
    """Evaluate whether a profile may perform an action."""

    def _load_policy(self) -> Dict[str, Any]:
        try:
            from hermes_cli.config import load_config, get_config_path

            cfg_path: Path = get_config_path()
            stat = cfg_path.stat()
            stamp = (stat.st_mtime_ns, stat.st_size)
        except Exception:
            stamp = None

        if getattr(self, "_policy_stamp", None) == stamp and getattr(self, "_policy_cache", None):
            return self._policy_cache

        policy = DEFAULT_POLICY_CONFIG
        try:
            policy = load_policy_config()
        except Exception:
            policy = DEFAULT_POLICY_CONFIG

        self._policy_cache = policy
        self._policy_stamp = stamp
        return policy

    def evaluate(self, profile: Optional[object], action: str) -> PolicyDecision:
        policy = self._load_policy()
        if not action.startswith(ACTION_TOOL_INVOKE_PREFIX):
            return PolicyDecision(True, "Action not governed by tool policy", "allow_not_tool")

        tool_name = action[len(ACTION_TOOL_INVOKE_PREFIX):]
        role = str(getattr(profile, "role", "") or "").lower()
        platform = str(getattr(profile, "platform", "") or "").lower()

        if policy.get("cli_superuser", True) and platform == "cli":
            return PolicyDecision(True, "CLI superuser mode", "allow_cli_superuser")

        if not role:
            if policy.get("fail_open_when_profile_missing", True):
                return PolicyDecision(True, "No active profile context", "allow_no_profile")
            return PolicyDecision(False, "Missing profile context", "deny_missing_profile")

        roles = policy.get("roles", {}) if isinstance(policy, dict) else {}
        role_cfg = roles.get(role, roles.get("guest", {})) if isinstance(roles, dict) else {}
        if not isinstance(role_cfg, dict):
            role_cfg = {}
        allow = role_cfg.get("allow", [])
        deny = role_cfg.get("deny", [])
        allow_set = set(allow) if isinstance(allow, list) else set()
        deny_set = set(deny) if isinstance(deny, list) else set()

        if tool_name in deny_set or "*" in deny_set:
            return PolicyDecision(False, f"{role} role cannot invoke {tool_name}", f"deny_role_{role}")

        if "*" in allow_set or tool_name in allow_set:
            return PolicyDecision(True, f"{role} role allows tool", f"allow_role_{role}")

        return PolicyDecision(False, f"{role} role cannot invoke {tool_name}", f"deny_role_{role}")
