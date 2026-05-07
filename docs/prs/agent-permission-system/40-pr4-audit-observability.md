# PR4 - Audit and Observability

## Goal

Make permission decisions explainable and operable in production.

## Checklist

- [x] Add policy audit module (`agent/policy_audit.py`)
- [x] Emit audit logs for entry-level policy decisions
- [ ] Add gateway-side policy audit events
- [ ] Add optional allow-decision logging controls
- [ ] Add operator docs for interpreting deny/fallback events

## Config Hooks

- `security.policy.audit.log_denies`
- `security.policy.audit.log_all_fallbacks`
- `security.policy.audit.log_allows` (optional future)

## Exit Criteria

- Deny decisions are visible and actionable.
- Operators can diagnose policy issues without code-level tracing.

