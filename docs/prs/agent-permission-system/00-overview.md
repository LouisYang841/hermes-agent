# Overview

## Objective

Build a configurable, compatible, and auditable agent+user permission system for Hermes.

## Non-Negotiable Invariants

1. Tool execution must be enforced at one unified entry point.
2. Resource boundaries must be explicit per agent profile.
3. CLI must remain a reliable recovery path to avoid self-lockout.
4. Gateway and built-in Hermes systems must remain backward compatible by default.
5. All strictness changes must be configurable via `config.yaml`.

## Configuration Root

- `security.policy`

## Core Building Blocks

- `agent/policy_config.py`
- `agent/policy_engine.py`
- `agent/policy_audit.py`
- `model_tools.handle_function_call(...)` entry enforcement
- per-entrypoint `invalid_agent_behavior` handling

## Design Evolution (Alternatives Considered)

1. Iteration 1: prompt-level user split.
   Result: reduced context bleed, but not security-enforceable and vulnerable to prompt injection.
2. Iteration 2: role checks scattered in individual tools (`owner/trusted/guest`).
   Result: better guardrails, but weak maintainability and easy-to-miss new code paths.
3. Iteration 3: gateway routing alignment.
   Result: identity/profile resolution moved earlier in request flow, enabling deterministic context.
4. Final direction: per-agent isolation (`AgentProfile + AgentRegistry + per-agent session/memory/workspace`) with policy-driven entry enforcement.
   Rationale: shared-nothing boundary is easier to reason about, audit, test, and aligns with Hermes profile model.

## Compatibility + Rollback

- Compatibility strategy: preserve default behavior unless explicitly tightened via `security.policy`.
- Rollback strategy: keep CLI recovery path (`cli_superuser`) and configurable fallback behavior for break-glass recovery.
