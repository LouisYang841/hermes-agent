from agent.policy_config import load_policy_config


def test_load_policy_config_has_defaults():
    cfg = load_policy_config()
    assert isinstance(cfg, dict)
    assert "roles" in cfg
    assert "invalid_agent_behavior" in cfg
    assert "audit" in cfg

