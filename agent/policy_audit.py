"""Policy decision audit logging."""

from __future__ import annotations

import logging
from typing import Any, Optional

from agent.policy_config import load_policy_config

_log = logging.getLogger("policy.audit")


def audit_policy_decision(
    *,
    allow: bool,
    action: str,
    tool_name: str,
    reason: str,
    code: str,
    profile: Optional[object],
) -> None:
    cfg = load_policy_config()
    audit_cfg = cfg.get("audit", {}) if isinstance(cfg, dict) else {}
    if not isinstance(audit_cfg, dict):
        audit_cfg = {}
    if allow and not audit_cfg.get("log_allows", False):
        return
    if not allow and not audit_cfg.get("log_denies", True):
        return

    _log.warning(
        "policy_decision allow=%s role=%s profile=%s action=%s tool=%s code=%s reason=%s",
        allow,
        getattr(profile, "role", None),
        getattr(profile, "key", None),
        action,
        tool_name,
        code,
        reason,
    )

