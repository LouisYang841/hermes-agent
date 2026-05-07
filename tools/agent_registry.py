"""
Agent Registry — singleton that maps identities to AgentProfile instances.

Reads identities.yaml at startup. Auto-creates profiles for guest users.
The gateway uses this to route every message to the right agent sandbox.
"""
import threading
from pathlib import Path
from typing import Optional, Dict

from tools.identity_resolver import resolve_identity, _load_identities as load_identities
from tools.agent_profile import AgentProfile


class AgentRegistry:
    """Thread-safe registry of all agent profiles."""

    def __init__(self):
        self._lock = threading.Lock()
        self._profiles: Dict[str, AgentProfile] = {}
        self._identity_map: Dict[tuple, str] = {}  # (platform, user_id) -> agent_name
        self._agent_home: Path = None
        self._loaded = False

    @property
    def agent_home(self) -> Path:
        if self._agent_home is None:
            from hermes_constants import get_hermes_home
            self._agent_home = Path(get_hermes_home()) / "agents"
        return self._agent_home

    def _build_profile(self, key: str, identity: dict) -> AgentProfile:
        """Create AgentProfile from an identity entry."""
        role = identity.get("role", "guest")
        profile = AgentProfile(
            key=key,
            user_name=identity.get("name", key),
            agent_name=identity.get("agent", "Hermes"),
            role=role,
            agent_dir=self.agent_home / key,
            default_model=identity.get("default_model", "deepseek-v4-pro"),
            default_provider=identity.get("default_provider", "deepseek"),
        )
        profile.ensure_dirs()
        return profile

    def load(self):
        """Load all identities from identities.yaml and build profiles."""
        with self._lock:
            if self._loaded:
                return

            identities = load_identities()
            for name, ident in identities.items():
                profile = self._build_profile(name, ident)
                self._profiles[name] = profile

                # Map platform IDs to agent name
                for platform, uid in ident.get("platforms", {}).items():
                    self._identity_map[(platform, str(uid))] = name

                # CLI default
                if ident.get("cli_default"):
                    self._identity_map[("cli", "__default__")] = name

            self._loaded = True

    def get_or_create(self, platform: str, user_id: Optional[str]) -> AgentProfile:
        """
        Resolve an identity to an agent profile. Auto-creates for guest users.

        Returns (profile, is_new) — is_new=True when a guest profile was just created.
        """
        if not self._loaded:
            self.load()

        # Try exact match
        if user_id:
            key = (platform, str(user_id))
            if key in self._identity_map:
                name = self._identity_map[key]
                if name in self._profiles:
                    return self._profiles[name]

            # Try resolve_identity for dynamic guests
            resolved = resolve_identity(platform, user_id)
            name = resolved.get("name", f"guest_{user_id}")
            role = resolved.get("role", "guest")

            if name in self._profiles:
                return self._profiles[name]

            # Auto-create guest profile
            is_new = True
        else:
            # CLI / API — use cli_default
            for (p, uid), agent_name in self._identity_map.items():
                if p == "cli" and uid == "__default__":
                    return self._profiles.get(agent_name)
            # Fallback
            name = "louis"
            is_new = False

        with self._lock:
            # Double-check after acquiring lock
            if name in self._profiles:
                return self._profiles[name]

            # Auto-create
            profile = AgentProfile(
                key=name,
                user_name=resolved.get("name", name),
                agent_name=resolved.get("agent", "Hermes"),
                role=role if user_id else "owner",
                agent_dir=self.agent_home / name,
                default_model=resolved.get("default_model", "gpt-5.5-Sys") if user_id else "deepseek-v4-pro",
                default_provider=resolved.get("default_provider", "custom:jwyihao") if user_id else "deepseek",
            )
            profile.ensure_dirs()
            self._profiles[name] = profile
            if user_id:
                self._identity_map[(platform, str(user_id))] = name

            return profile

    def get(self, name: str) -> Optional[AgentProfile]:
        """Get an existing profile by name."""
        if not self._loaded:
            self.load()
        return self._profiles.get(name)

    def list_profiles(self) -> Dict[str, AgentProfile]:
        """Return all loaded profiles."""
        if not self._loaded:
            self.load()
        return dict(self._profiles)

    def reload(self):
        """Force reload from identities.yaml."""
        with self._lock:
            self._profiles.clear()
            self._identity_map.clear()
            self._loaded = False
            self.load()


# Singleton
_registry: Optional[AgentRegistry] = None
_registry_lock = threading.Lock()


def get_agent_registry() -> AgentRegistry:
    """Get or create the global AgentRegistry singleton."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = AgentRegistry()
                _registry.load()
    return _registry
