# Privacy

Vega Pomodoro Log is local-only.

It does not include telemetry, analytics, crash reporting, remote sync, account
creation, HTTP clients, sockets, or background services.

Data written by the tool:

- CSV session log at `~/.local/share/vega-pomodoro-log/sessions.csv` by default
- optional `.ics` files when you run `export-ics`

The tool records text you provide in task labels, tags, and notes. Treat those
files as work records and avoid typing secrets into them.
