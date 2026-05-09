# Vega Pomodoro Log

[![Release](https://img.shields.io/github/v/release/Vega-Starboard/vega-pomodoro-log?label=release)](https://github.com/Vega-Starboard/vega-pomodoro-log/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Standard Library](https://img.shields.io/badge/dependencies-Python%20standard%20library-62d394)](#design-boundary)
[![Local Only](https://img.shields.io/badge/privacy-local%20only-111827)](#privacy)
[![No Telemetry](https://img.shields.io/badge/telemetry-none-0f172a)](#privacy)
[![License: MIT](https://img.shields.io/badge/license-MIT-e1b15a)](LICENSE)

Minimalist Pomodoro timer for people who want a plain local work log instead of
an account, dashboard, sync service, or productivity feed.

Vega Pomodoro Log is a dependency-free Python CLI. It runs focus timers, appends
sessions to CSV, summarizes time windows, and exports sessions to an iCalendar
`.ics` file for calendar or spreadsheet workflows.

## Why

Small security research and development sessions are easy to lose. A 25-minute
HackerOne recon block, a bug reproduction window, a review pass, or a study
session should leave a clean trail without creating another cloud account.

This tool keeps that trail as boring, inspectable data:

- local CSV log
- UTC timestamps
- human-readable tasks, tags, and notes
- optional iCalendar export
- no network code
- no telemetry
- no database
- no background daemon

## Features

- Run a Pomodoro-style focus timer from the terminal.
- Log completed or partial sessions manually.
- Store all records in a simple CSV file.
- Filter session lists and stats by today, week, month, or date range.
- Export filtered sessions to iCalendar `.ics`.
- Override the log path with `--log-file` or `VEGA_POMODORO_LOG`.
- Use only the Python standard library.

## Install

Clone the repo and run from source:

```bash
git clone https://github.com/Vega-Starboard/vega-pomodoro-log.git
cd vega-pomodoro-log
PYTHONPATH=src python3 -m vega_pomodoro_log --help
```

For an editable local command:

```bash
python3 -m pip install --user -e .
vega-pomodoro-log --help
```

No package dependencies are installed by this project.

## Quick Start

Run a normal 25-minute focus block with a 5-minute break:

```bash
vega-pomodoro-log start --task "HackerOne recon block" --tag bug-bounty
```

Run a shorter block and skip the break:

```bash
vega-pomodoro-log start --focus 15 --skip-break --task "Review report draft" --tag writing
```

Log a session after the fact:

```bash
vega-pomodoro-log log --task "CSP notes" --minutes 25 --tag headers --notes "Reviewed policy gaps"
```

Show recent sessions:

```bash
vega-pomodoro-log list
```

Show this week's stats:

```bash
vega-pomodoro-log stats --window week
```

Export this month's sessions to an iCalendar file:

```bash
vega-pomodoro-log export-ics --window month --output pomodoro-month.ics
```

Print and initialize the active log path:

```bash
vega-pomodoro-log path
```

## Commands

### `start`

Runs a countdown timer and appends the result to CSV.

```bash
vega-pomodoro-log start \
  --focus 25 \
  --break 5 \
  --task "Endpoint review" \
  --tag bug-bounty \
  --notes "Scoped program only"
```

If interrupted with `Ctrl+C`, the elapsed focus session is still logged as
incomplete.

### `log`

Appends a manual session without running a timer.

```bash
vega-pomodoro-log log \
  --task "Write notes" \
  --minutes 30 \
  --kind review \
  --tag report
```

Accepted kinds:

- `focus`
- `break`
- `planning`
- `review`

### `list`

Displays recent rows in a terminal table.

```bash
vega-pomodoro-log list --window today
vega-pomodoro-log list --from-date 2026-05-01 --to-date 2026-05-09 --limit 50
```

### `stats`

Summarizes count, completed count, total minutes, focus minutes, and time by
tag.

```bash
vega-pomodoro-log stats --window week
```

### `export-ics`

Writes filtered sessions to an iCalendar file.

```bash
vega-pomodoro-log export-ics --from-date 2026-05-01 --output may-focus.ics
```

Pass `--force` to overwrite an existing file.

### `path`

Creates the CSV file if needed and prints its location.

```bash
vega-pomodoro-log path
```

## CSV Schema

Default path:

```text
~/.local/share/vega-pomodoro-log/sessions.csv
```

Override with either:

```bash
VEGA_POMODORO_LOG=/path/to/sessions.csv vega-pomodoro-log list
vega-pomodoro-log --log-file /path/to/sessions.csv list
```

Fields:

| Column | Meaning |
| --- | --- |
| `id` | Stable short SHA-256-derived session ID |
| `started_at_utc` | UTC ISO-8601 session start |
| `ended_at_utc` | UTC ISO-8601 session end |
| `duration_minutes` | Decimal duration |
| `kind` | `focus`, `break`, `planning`, or `review` |
| `task` | Human task label |
| `tag` | Optional grouping tag |
| `notes` | Optional notes |
| `completed` | `true` or `false` |
| `source` | `timer` or `manual` |

Example:

```csv
id,started_at_utc,ended_at_utc,duration_minutes,kind,task,tag,notes,completed,source
7e2d4a0aef8d57aa,2026-05-09T15:00:00Z,2026-05-09T15:25:00Z,25,focus,HackerOne recon block,bug-bounty,Scoped target review,true,manual
```

## iCalendar Export

`export-ics` emits a plain `.ics` file with one `VEVENT` per session. Times are
written in UTC with `DTSTART`, `DTEND`, and `DTSTAMP` values. The output is
intended for import into calendar tools that understand iCalendar files.

The exporter follows the core shape of RFC 5545 iCalendar data:

- `BEGIN:VCALENDAR` / `END:VCALENDAR`
- `VERSION:2.0`
- `VEVENT` entries
- folded long lines
- escaped text values
- UTC timestamps ending in `Z`

## Privacy

Local Only.

Vega Pomodoro Log does not send data anywhere. It does not include HTTP clients,
sockets, analytics, telemetry, crash reporting, remote sync, account creation,
or background services. No telemetry means no hidden collection path in normal
use.

The CSV and `.ics` files are yours. Treat them as work records; they may include
task names or notes you typed.

## Design Boundary

This is intentionally small:

- Python standard library only
- terminal interface only
- local files only
- no browser automation
- no external calendar API
- no cloud sync
- no secret storage

For security research workflows, use it as a time/accountability log for lawful,
authorized work. It is not a scanner, exploit tool, or target interaction tool.

## Verify

Run the included verifier:

```bash
python3 scripts/verify_pomodoro.py
```

The verifier checks:

- CLI syntax compiles
- no obvious network/process markers are present in the package
- manual CSV logging works
- list output includes logged work
- stats output totals focus time
- iCalendar export contains required markers
- documentation keeps the local-only boundary visible

## Documentation Notes

The implementation is shaped around official documentation for:

- Python `argparse` command-line parsing
- Python `csv` reading and writing
- Python `datetime` UTC handling
- RFC 5545 iCalendar file structure
- shields.io badge URLs used in this README

## Provider Notes

Vega used DeepSeek for a bounded bulk pass on README positioning, badge ideas,
edge cases, and validation ideas. Codex/GPT handled implementation, review,
verification, and publication packaging.

## Tags

`pomodoro-timer`, `cli`, `python`, `time-tracking`, `csv-logging`,
`ics-export`, `productivity`, `local-first`, `no-telemetry`, `hacker-tools`,
`bug-bounty`, `standard-library`

## Status

Version: `0.1.0`

Current status: usable from source, locally verified.
