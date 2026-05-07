# Code Review AI Prompt (Permission System PR)

Use the prompt below with your code-review AI:

---

You are reviewing a security-sensitive PR in Hermes Agent that introduces a configurable permission system.

## Review Goal

Prioritize:
1. privilege-escalation risks,
2. isolation break risks (session/memory/workspace cross-access),
3. compatibility regressions in gateway/web/api flows,
4. missing tests for high-risk paths.

Do not focus on style unless it impacts correctness or maintainability.

## Context

- This PR moves from scattered role checks to centralized policy enforcement.
- Main files include:
  - `agent/policy_config.py`
  - `agent/policy_engine.py`
  - `agent/policy_audit.py`
  - `model_tools.py` (tool-call entry enforcement)
  - `hermes_cli/web_server.py` (policy-driven agent DB resolution)
  - `hermes_cli/config.py` (`security.policy` defaults)
- Design notes:
  - `docs/prs/agent-permission-system/00-overview.md`
  - `docs/prs/agent-permission-system/compatibility-matrix.md`
  - `docs/prs/agent-permission-system/30-pr3-gateway-wiring.md`

## What to Check (Mandatory)

1. Can invalid or missing `agent` values lead to unintended shared DB access?
2. Are deny/allow decisions fully controlled by config and deterministic?
3. Is there any path that bypasses `model_tools.handle_function_call` policy checks?
4. Are fallback behaviors explicit and logged (not silent)?
5. Could CLI superuser behavior accidentally leak to remote entrypoints?
6. Are there race conditions or context leaks with thread-local profile usage?
7. Do defaults preserve backward compatibility safely?
8. Are break-glass/recovery paths safe but not overly permissive?

## Output Format Required

Return:
1. **Findings** ordered by severity (`Critical`, `High`, `Medium`, `Low`) with file + function references.
2. **Exploit/Failure Scenarios** for each Critical/High finding (concrete request flow).
3. **Required Fixes** (must-fix before merge).
4. **Suggested Improvements** (non-blocking).
5. **Test Gaps** with exact test cases to add.
6. **Merge Verdict**: `Approve`, `Approve with changes`, or `Block`.

Be specific and adversarial. Assume hostile inputs.

---

