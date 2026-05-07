# PR3 - Gateway Wiring Compatibility (Pending)

## Goal

Harden gateway policy wiring while preserving compatibility with built-in Hermes flows.

## Status

- Pending implementation.

## Required Work

- [ ] Centralize gateway profile resolution at message-entry hook
- [ ] Always set and clear `_agent_context` deterministically per turn
- [ ] Route invalid/empty agent behavior through `security.policy.invalid_agent_behavior.gateway`
- [ ] Keep CLI recovery path (`cli_superuser`) explicit and stable
- [ ] Add gateway audit logs for deny/fallback decisions

## Compatibility Focus Areas

- Session lifecycle (`new`, `resume`, `branch`, `restart`)
- Slash command routing
- Platform adapters (`telegram`, `discord`, `api_server`, `cli`)
- Existing session and memory persistence behavior

## Exit Criteria

- No regression in gateway command or session routing.
- Policy behavior is consistent with config and logs.

