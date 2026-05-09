# Security Policy

## Supported Versions

| Version | Supported |
| --- | --- |
| `0.1.x` | Yes |

## Scope

Vega Pomodoro Log is a local CLI utility. It should not open network
connections, read browser storage, collect secrets, or run background services.

Security-relevant issues include:

- unexpected network activity
- unsafe file handling
- CSV or iCalendar output corruption
- command behavior that writes outside the requested log/export paths
- documentation that weakens the local-only boundary

## Reporting

Open a GitHub issue with:

- version or commit
- operating system
- command used
- expected behavior
- observed behavior
- minimal reproduction steps

Do not include private task logs, secrets, tokens, or target-specific security
research notes in public issues.
