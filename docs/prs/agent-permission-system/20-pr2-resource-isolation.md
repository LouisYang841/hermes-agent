# PR2 - Resource Isolation

## Goal

Enforce policy-driven session and memory resolution behavior without unsafe silent fallback.

## Checklist

- [x] Add `invalid_agent_behavior` to policy config
- [x] Make web session DB resolution policy-driven
- [x] Add `/api/policy/config` for visibility
- [x] Switch web memory path resolution to `profile.memory_dir`
- [ ] Apply same behavior contract to all non-web entrypoints

## Compatibility Rule

- Keep defaults non-breaking.
- Strict deny modes must be opt-in via config where needed.

## Exit Criteria

- Invalid agent handling is deterministic and configurable per source.
- No hidden fallback unless explicitly configured.

