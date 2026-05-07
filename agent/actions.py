"""Canonical action names for authorization checks."""

from __future__ import annotations


ACTION_TOOL_INVOKE_PREFIX = "tool.invoke."


def tool_invoke_action(tool_name: str) -> str:
    """Return the canonical action name for invoking a tool."""
    return f"{ACTION_TOOL_INVOKE_PREFIX}{tool_name}"

