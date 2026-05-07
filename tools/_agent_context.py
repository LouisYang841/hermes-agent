"""
Thread-local agent context.

Set at the beginning of each message handling, read by tools.
Replaces the current_identity.json file-based approach with thread-safe context.
"""
import threading
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from tools.agent_profile import AgentProfile

_agent_profile: threading.local = threading.local()


def set_current_profile(profile: "AgentProfile") -> None:
    """Set the agent profile for the current thread/turn."""
    _agent_profile.value = profile


def get_current_profile() -> Optional["AgentProfile"]:
    """Get the agent profile for the current thread/turn."""
    return getattr(_agent_profile, "value", None)


def clear_current_profile() -> None:
    """Clear the profile (called at end of turn)."""
    try:
        del _agent_profile.value
    except AttributeError:
        pass
