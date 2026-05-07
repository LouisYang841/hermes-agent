# Review Feedback: Configurable Agent Permission System

> Generated from CodeRabbit review. Feed this file to your coding assistant to address all flagged issues.
> Priority: fix Critical/High first, then Medium, then Nitpicks.

---

## 🔴 Critical / High

### 1. `tests/hermes_cli/test_web_server.py` — Lines 281–330
**TestWebServerAgentDbPolicy accidentally swallows subsequent tests**

The new `TestWebServerAgentDbPolicy` class is placed before existing tests, causing subsequent tests (e.g., `test_reveal_env_var_custom_session_header_ignores_proxy_authorization` through `test_path_traversal_dotdot_blocked`) to be indented inside it and inherit `_setup_test_client`.

**Fix:** Move the entire `TestWebServerAgentDbPolicy` definition to *after* all existing `TestWebServerEndpoints` tests, or close/dedent the class block so those tests remain top-level.

---

### 2. `hermes_cli/web_server.py` — Lines 30–33
**`load_policy_config` imported before `sys.path` is patched**

If `PROJECT_ROOT` is computed and `sys.path.insert(0, str(PROJECT_ROOT))` runs after the import, `agent.policy_config` may not be discoverable.

**Fix:** Ensure this order:
```python
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.policy_config import load_policy_config  # AFTER sys.path patch
```

---

## 🟠 Medium

### 3. `agent/policy_audit.py` — Lines 23–29
**`log_all_fallbacks` config key is ignored in audit gating**

The current logic only checks `log_allows` and `log_denies`, ignoring the `log_all_fallbacks` flag defined in the config.

**Fix:** Update the conditional to be fallback-aware. Add a `fallback: bool = False` parameter to `audit_policy_decision` and apply:
```python
# When allow is True:
if not ((not fallback and audit_cfg.get("log_allows", False)) or
        (fallback and audit_cfg.get("log_all_fallbacks", True))):
    return

# When allow is False:
if not ((not fallback and audit_cfg.get("log_denies", True)) or
        (fallback and audit_cfg.get("log_all_fallbacks", True))):
    return
```
#### 💬 Design Discussion: `fail_open_when_profile_missing`

> **LouisYang841:** During auto self-dev of Hermes Agent, it happened multiple times that an agent locked itself outside of the permission system while modifying it. This can totally block Hermes in both CLI and gateway. We should make this a mandatory user-set config with no default.
>
> **CodeRabbit:** That's a critical real-world constraint. Any hardcoded default is a trap: `False` causes lockout, `True` silently bypasses RBAC. Forcing explicit acknowledgment is the right call.

**Agreed implementation — "required, no default":**

1. Sentinel: `"fail_open_when_profile_missing": None` in `DEFAULT_POLICY_CONFIG`
2. Validation via `resolve_fail_open()` that raises `ConfigurationError` when unset
3. Call from `PolicyEngine.evaluate()` so misconfigurations fail fast
4. Document trade-off in `config.yaml`:

```yaml
security:
  policy:
    # REQUIRED — no default. Choose deliberately:
    #   true  → unprovisioned agents are allowed (risk: RBAC bypass)
    #   false → unprovisioned agents are denied (risk: self-lockout during live edits)
    fail_open_when_profile_missing: true
```



---

### 4. `agent/policy_audit.py` — Lines 31–36
**Raw `profile.key` logged — potential PII exposure**

`_log.warning` emits `getattr(profile, "key", None)` directly, which can expose user-identifying keys in logs.

**Fix:** Hash the profile key before logging:
```python
import hashlib
raw_key = getattr(profile, "key", None)
profile_id = (
    hashlib.sha256(str(raw_key).encode()).hexdigest()[:16]
    if raw_key else "anonymous"
)
# Use profile_id in the log message instead of raw_key
```

---

### 5. `agent/policy_config.py` — Line 10
**`fail_open_when_profile_missing` defaults to `True` — unsafe default**

This is a global fail-open that weakens RBAC for all surfaces including `web` and `gateway`.

**Fix:** Change default to `False` (fail-closed) and rely on per-surface `invalid_agent_behavior` for explicit opt-in:
```python
"fail_open_when_profile_missing": False,  # Opt-in; override per-surface via invalid_agent_behavior
```
Add a comment explaining that `cli` can be set to `allow` via `invalid_agent_behavior.cli` for local dev, while `web` and `gateway` must explicitly deny.

---

### 6. `agent/policy_config.py` — Lines 65–66
**Silent `except Exception: pass` swallows config load errors**

A malformed YAML or failed import silently falls back to defaults with no operator-visible signal.

**Fix:**
```python
except Exception as e:
    _log.warning(
        "Failed to load security.policy config; using defaults. Error: %s",
        e,
        exc_info=True,
    )
```

---

### 7. `agent/policy_engine.py` — Lines 63–66
**Unknown roles silently fall back to `guest` — masks typos/misconfigurations**

`roles.get(role, roles.get("guest", {}))` returns guest config for any unrecognized role name without any signal.

**Fix:** Add an explicit membership check:
```python
if role not in roles:
    _log.warning(
        "Unknown role %r not in policy config (available: %s); falling back to 'guest'.",
        role,
        list(roles.keys()),
    )
role_cfg = roles.get(role, roles.get("guest", {}))
```

---

### 8. `hermes_cli/config.py` — Line 1222
**`fail_open_when_profile_missing: True` in default config — same issue as `#5`**

This is the user-facing config default that needs to match the fix in `policy_config.py`.

**Fix:**
```yaml
fail_open_when_profile_missing: false
```
Update any tests that assert `True` for this value. Ensure `invalid_agent_behavior.cli` is set to `allow` to preserve CLI developer experience.

---

## 🟡 Nitpick / Low

### 9. `agent/policy_engine.py` — Line 7
**Unused import: `Path`**

```diff
 from dataclasses import dataclass
 from typing import Optional, Dict, Any
-from pathlib import Path

 from agent.actions import ACTION_TOOL_INVOKE_PREFIX
```

---

### 10. `agent/policy_engine.py` — Line 25
**Unused import: `load_config`**

```diff
-        from hermes_cli.config import load_config, get_config_path
+        from hermes_cli.config import get_config_path
```

---

### 11. `tests/test_model_tools.py` — Lines 119–125
**Hardcoded POSIX path `/tmp/guest_1` breaks on Windows**

```diff
-    def test_policy_block_returns_error_and_skips_dispatch(self, monkeypatch):
+    def test_policy_block_returns_error_and_skips_dispatch(self, monkeypatch, tmp_path):
         from pathlib import Path
         from tools.agent_profile import AgentProfile

         profile = AgentProfile(
             key="guest_1",
             user_name="guest_1",
             agent_name="Hermes",
             role="guest",
-            agent_dir=Path("/tmp/guest_1"),
+            agent_dir=tmp_path / "guest_1",
         )
```

---

## 📋 Summary Checklist

- [ ] **[CRITICAL]** Fix `TestWebServerAgentDbPolicy` class placement swallowing subsequent tests (`tests/hermes_cli/test_web_server.py` L281–330)
- [ ] **[HIGH]** Move `load_policy_config` import after `sys.path` patch (`hermes_cli/web_server.py` L30–33)
- [ ] **[MEDIUM]** Wire `log_all_fallbacks` into audit gating logic (`agent/policy_audit.py` L23–29)
- [ ] **[MEDIUM]** Hash `profile.key` before logging to avoid PII exposure (`agent/policy_audit.py` L31–36)
- [ ] **[MEDIUM]** Change `fail_open_when_profile_missing` default to `False` (`agent/policy_config.py` L10)
- [ ] **[MEDIUM]** Log on `except Exception` instead of silent pass (`agent/policy_config.py` L65–66)
- [ ] **[MEDIUM]** Log warning on unknown role fallback to guest (`agent/policy_engine.py` L63–66)
- [ ] **[MEDIUM]** Change `fail_open_when_profile_missing` to `false` in default config (`hermes_cli/config.py` L1222)
- [ ] **[NITPICK]** Remove unused `Path` import (`agent/policy_engine.py` L7)
- [ ] **[NITPICK]** Remove unused `load_config` import (`agent/policy_engine.py` L25)
- [ ] **[NITPICK]** Replace hardcoded `/tmp/guest_1` with `tmp_path` fixture (`tests/test_model_tools.py` L119–125)