# Test Plan

## Unit Tests

- `tests/policy/test_policy_config.py`
- `tests/policy/test_policy_engine.py`
- policy-focused cases in `tests/test_model_tools.py`

## Integration Tests

- web server policy endpoints and agent DB behavior
- gateway wiring policy behavior (PR3)

## Environment Notes

- On Windows native Python, some web server tests can fail due to POSIX PTY imports (`fcntl`).
- Preferred full run environment for web/gateway tests: WSL or Linux.

## Execution Log

- 2026-05-08: policy unit subset passed locally (`9 passed`)
- 2026-05-08: web server policy tests partially blocked by platform-specific PTY import path on Windows

