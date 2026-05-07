"""
Agent Profile — per-identity agent sandbox.

Each identity (louis, 42, guest_xxx) gets its own AgentProfile with:
- Isolated session DB (state.db)
- Isolated memory store
- Isolated workspace
- Role-based toolset
- Per-agent system prompt
"""
import json
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class AgentProfile:
    """Everything one agent needs — fully isolated from other agents.

    A User (human) owns an Agent (AI persona). The user has permissions,
    preferences, and platforms; the agent has a persona, tools, and memory.
    """

    key: str                           # internal lookup: "louis", "42"
    user_name: str                     # human display name: "Louis", "42"
    agent_name: str                    # AI persona name: "Hermes", "小禾"
    role: str                          # "owner", "trusted", "guest"
    agent_dir: Path                    # ~/.hermes/agents/<key>/
    
    # Defaults (loaded from identities.yaml or auto-created)
    default_model: str = "deepseek-v4-pro"
    default_provider: str = "deepseek"
    
    # Runtime state
    _state: Dict[str, Any] = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def runtime_path(self) -> Path:
        return self.agent_dir / "runtime.json"

    @property
    def session_db_path(self) -> Path:
        return self.agent_dir / "state.db"

    @property
    def memory_dir(self) -> Path:
        """Per-agent memory directory."""
        from hermes_constants import get_hermes_home
        return Path(get_hermes_home()) / "memories" / self.key

    @property
    def workspace_dir(self) -> Path:
        """Per-agent workspace directory."""
        from hermes_constants import get_hermes_home
        return Path(get_hermes_home()) / "workspaces" / self.key

    @property
    def procedure_path(self) -> Path:
        """Per-agent procedure.md (optional override). Falls back to global."""
        proc = self.agent_dir / "procedure.md"
        return proc if proc.exists() else None

    @property
    def allowed_tools(self) -> List[str]:
        """Tools this agent is allowed to use based on role."""
        if self.role == "owner":
            return []  # empty = all tools
        elif self.role == "trusted":
            return [
                "clarify", "memory", "session_search", "send_message",
                "skill_view", "skills_list", "todo", "vision_analyze",
                "read_file", "write_file", "patch", "search_files",
                # No terminal, no execute_code, no delegate_task
            ]
        else:  # guest
            return [
                "clarify", "memory", "session_search",
                "skill_view", "skills_list", "todo",
                # Read-only files in workspace only
                "read_file",
            ]

    def load_runtime(self) -> Dict[str, Any]:
        """Load runtime state from disk."""
        with self._lock:
            if self.runtime_path.exists():
                try:
                    self._state = json.loads(self.runtime_path.read_text())
                except Exception:
                    self._state = self._fresh_runtime()
            else:
                self._state = self._fresh_runtime()
            return self._state

    def save_runtime(self, updates: Dict[str, Any]):
        """Save runtime state to disk atomically."""
        with self._lock:
            self._state.update(updates)
            tmp = self.runtime_path.with_suffix(".tmp")
            self.runtime_path.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(json.dumps(self._state, indent=2))
            tmp.rename(self.runtime_path)

    def _fresh_runtime(self) -> Dict[str, Any]:
        return {
            "agent_name": self.key,
            "role": self.role,
            "created_at": None,
            "last_active_session_id": None,
            "total_sessions": 0,
            "total_tokens": 0,
        }

    def ensure_dirs(self):
        """Create all per-agent directories."""
        self.agent_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.load_runtime()  # creates runtime.json if missing
