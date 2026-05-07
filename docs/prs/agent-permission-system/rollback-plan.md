# Rollback Plan

## Fast Rollback

1. Revert policy-entry enforcement commit in `model_tools.py`.
2. Revert web policy DB resolution changes in `hermes_cli/web_server.py`.
3. Keep `security.policy` config keys harmless by default.

## Break-Glass Recovery

- Keep CLI access path available at all times.
- Ensure `security.policy.cli_superuser` can be set to `true`.
- If needed, switch `invalid_agent_behavior.*` to fallback mode for temporary recovery.

## Post-Rollback Validation

1. Can owner use CLI tools end-to-end.
2. Sessions list/search/detail endpoints return expected data.
3. Gateway command and message routing unchanged from baseline.

