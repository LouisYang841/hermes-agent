# Compatibility Matrix

## Core Paths

| Area | Backward Compatible by Default | Notes |
|---|---|---|
| CLI tool execution | Yes | `cli_superuser` keeps recovery path |
| Web sessions API | Yes | behavior controlled by `invalid_agent_behavior.web` |
| Gateway session flow | Pending | PR3 scope |
| Plugin hook flow | Yes | enforcement occurs before dispatch, hooks remain |
| Existing role configs | Yes | defaults include role policy baseline |

## Regression Watchlist

1. Session routing for resumed threads.
2. Legacy command behavior that depends on shared DB fallback.
3. Platform-specific adapters with implicit profile assumptions.
4. Non-POSIX test environments importing web server PTY code paths.

