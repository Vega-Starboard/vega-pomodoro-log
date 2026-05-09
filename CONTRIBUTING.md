# Contributing

Keep the project small, inspectable, and local-only.

Before opening a change:

```bash
python3 scripts/verify_pomodoro.py
```

Guidelines:

- use the Python standard library only
- keep CSV compatibility stable
- keep UTC timestamps explicit
- do not add telemetry, sync, accounts, or background services
- prefer clear CLI behavior over hidden automation
- document any schema or export behavior changes in `README.md`

Good first improvements:

- better terminal table formatting
- optional JSON export
- stricter iCalendar validation tests
- more examples for spreadsheet workflows
