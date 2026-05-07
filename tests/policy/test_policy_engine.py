from agent.actions import tool_invoke_action
from agent.policy_engine import PolicyEngine
from tools.agent_profile import AgentProfile


def _profile(role: str) -> AgentProfile:
    from pathlib import Path

    return AgentProfile(
        key=f"{role}_user",
        user_name=role,
        agent_name="Hermes",
        role=role,
        agent_dir=Path("/tmp") / f"{role}_user",
    )


def test_owner_allows_terminal():
    decision = PolicyEngine().evaluate(_profile("owner"), tool_invoke_action("terminal"))
    assert decision.allow is True


def test_trusted_denies_terminal():
    decision = PolicyEngine().evaluate(_profile("trusted"), tool_invoke_action("terminal"))
    assert decision.allow is False
    assert decision.code == "deny_role_trusted"


def test_trusted_allows_read_file():
    decision = PolicyEngine().evaluate(_profile("trusted"), tool_invoke_action("read_file"))
    assert decision.allow is True


def test_guest_denies_terminal():
    decision = PolicyEngine().evaluate(_profile("guest"), tool_invoke_action("terminal"))
    assert decision.allow is False
    assert decision.code == "deny_role_guest"


def test_guest_allows_read_file():
    decision = PolicyEngine().evaluate(_profile("guest"), tool_invoke_action("read_file"))
    assert decision.allow is True


def test_profile_missing_can_be_fail_closed(monkeypatch):
    engine = PolicyEngine()
    monkeypatch.setattr(
        engine,
        "_load_policy",
        lambda: {
            "cli_superuser": True,
            "fail_open_when_profile_missing": False,
            "roles": {"guest": {"allow": ["read_file"], "deny": []}},
        },
    )
    decision = engine.evaluate(None, tool_invoke_action("read_file"))
    assert decision.allow is False
    assert decision.code == "deny_missing_profile"


def test_config_override_can_deny_specific_tool(monkeypatch):
    engine = PolicyEngine()
    monkeypatch.setattr(
        engine,
        "_load_policy",
        lambda: {
            "cli_superuser": True,
            "fail_open_when_profile_missing": True,
            "roles": {"trusted": {"allow": ["*"], "deny": ["read_file"]}},
        },
    )
    decision = engine.evaluate(_profile("trusted"), tool_invoke_action("read_file"))
    assert decision.allow is False
    assert decision.code == "deny_role_trusted"
