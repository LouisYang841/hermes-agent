# PR1 - Policy Core

## Goal

Introduce a centralized policy engine and enforce it at tool-call entry.

## Checklist

- [x] Add canonical action mapping (`agent/actions.py`)
- [x] Add centralized policy engine (`agent/policy_engine.py`)
- [x] Make policy config-driven (`security.policy`)
- [x] Enforce policy in `model_tools.handle_function_call`
- [x] Add basic policy unit tests
- [ ] Add full matrix tests for all high-risk tools

## Risks

- Existing tests may assume old implicit behavior for unknown tools.

## Exit Criteria

- Policy deny decisions block actual dispatch.
- Role-based allow/deny can be changed only through config.

