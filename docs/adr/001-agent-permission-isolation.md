# ADR-001: Agent Permission Isolation Architecture

**Status:** Proposed  
**Date:** 2026-05-07  
**Author:** Louis Yang (@LouisYang841)  
**Review:** CodeRabbit AI, Hermes Agent (self-hosted companion)

---

## Context

Hermes Agent started as a single-user CLI tool. As it grew to support multi-platform messaging (Telegram, QQ, 飞书, 微信) and multi-user access (owner "Louis", trusted "42", guest users), the need for identity-based permission isolation became critical.

Three design iterations were explored before settling on the final architecture:

| Iteration | Approach | Problem |
|-----------|----------|---------|
| v1 (patches 001-002) | Scattered `if role == "owner"` checks in 4 files | Impossible to audit; adding a new permission required grepping the entire codebase |
| v2 (patches 005/013) | Centralized `AgentRegistry` + `AgentProfile` objects with per-agent session DBs, memory dirs, and workspaces | Data source unified, but permission *decisions* remained scattered across `run_agent.py`, `gateway/run.py`, and individual tool files |
| v3 (this PR) | Single-entry `PolicyEngine` with declarative RBAC, intercepting all tool calls at `handle_function_call()` | Clean architecture, but requires careful integration with existing gateway identity wiring |

A key lesson from v2's deployment on a live EC2 instance: **twelve gateway crashes were caused by a cross-function variable scope bug** (`_agent_profile` defined in `_handle_message_with_agent` but inaccessible in `_run_agent`). This reinforced the need for the policy context to flow through function parameters or thread-local storage, not rely on local variable scope.

Additionally, the upstream `hermes-agent` repository received 426 commits during our development period. Auto-merging via `git stash apply` silently dropped four of our patches (001, 002, 006, 010) without any merge conflict, because upstream modified adjacent code. Automated diff-based verification is now mandatory after each `hermes update`.

## Decision

We will adopt a **PolicyEngine-based single-entry enforcement** architecture:

1. All tool invocations pass through `handle_function_call()` in `model_tools.py`
2. A `PolicyEngine.evaluate(subject, action, resource, context)` call gates every tool invocation
3. RBAC is declaratively configured with `owner`/`trusted`/`guest` tiers
4. Per-agent resources (session DB, memory, workspace) are isolated at the `AgentProfile` level and resolved before the policy check

### Key Design Choices

**`fail_open_when_profile_missing`: No default (required operator choice)**

There is no safe universal default for this flag. `True` silently bypasses RBAC for unprovisioned agents. `False` can lock the agent out of its own permission system during auto self-development cycles—a bootstrap paradox observed multiple times during live testing on the EC2 instance.

Solution: use `None` as sentinel in `DEFAULT_POLICY_CONFIG`. A `resolve_fail_open()` helper raises `ConfigurationError` if the operator has not explicitly chosen. This forces conscious acknowledgment of the trade-off.

*(Discussed with CodeRabbit at PR #6, `agent/policy_config.py:10`)*

**Gateway wiring: identity flows through function parameters**

The v2 `_agent_profile` scope bug taught us that per-request identity context must be explicitly threaded through the call chain (`_handle_message_with_agent` → `_run_agent` → `handle_function_call` → `PolicyEngine.evaluate`). Thread-local storage (`tools/_agent_context.py`) provides a safety net but is not the primary transport.

## Consequences

**Positive:**
- Single audit point for all permission decisions
- New roles/tools require changes in one file, not four
- Declarative config makes security posture visible and reviewable
- The `ConfigurationError` pattern for `fail_open` makes misconfigurations fail fast

**Negative:**
- Added latency: one additional function call per tool invocation (negligible)
- Gateway restart required for policy changes (acceptable for security config)
- The `None`-sentinel pattern requires documentation and operator awareness

**Risks:**
- Upstream divergence: the PolicyEngine must be re-applied after each `hermes-agent` update
- The stash auto-merge hazard (see Context) means every update needs manual verification with `grep` of key symbols, not just `git diff --stat`

## References

- [CodeRabbit Review](docs/prs/agent-permission-system/coderabbit_review.md)
- [Architecture Journal](docs/custom-diffs/README.md#architecture-journal--key-ideas--lessons)
- [Test Plan](docs/prs/agent-permission-system/test-plan.md)
- [Rollback Plan](docs/prs/agent-permission-system/rollback-plan.md)
- PR #6: feat/agent-permission-system-batch
