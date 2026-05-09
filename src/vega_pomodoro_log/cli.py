"""Dependency-free Pomodoro timer with CSV logging and ICS export."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence


CSV_FIELDS = [
    "id",
    "started_at_utc",
    "ended_at_utc",
    "duration_minutes",
    "kind",
    "task",
    "tag",
    "notes",
    "completed",
    "source",
]
KINDS = {"focus", "break", "planning", "review"}
DEFAULT_LOG = Path.home() / ".local" / "share" / "vega-pomodoro-log" / "sessions.csv"


@dataclass(frozen=True)
class Session:
    id: str
    started_at_utc: datetime
    ended_at_utc: datetime
    duration_minutes: float
    kind: str
    task: str
    tag: str
    notes: str
    completed: bool
    source: str


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def parse_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).replace(microsecond=0)


def parse_local_date(value: str) -> date:
    return date.fromisoformat(value)


def session_id(started_at: datetime, ended_at: datetime, kind: str, task: str, tag: str) -> str:
    material = "|".join([
        started_at.isoformat(),
        ended_at.isoformat(),
        kind,
        task,
        tag,
    ])
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def default_start_for_manual_log(minutes: float) -> tuple[datetime, datetime]:
    ended_at = utc_now()
    started_at = ended_at - timedelta(minutes=minutes)
    return started_at, ended_at


def make_session(
    *,
    started_at: datetime,
    ended_at: datetime,
    kind: str,
    task: str,
    tag: str,
    notes: str,
    completed: bool,
    source: str,
) -> Session:
    duration = max(0.0, (ended_at - started_at).total_seconds() / 60)
    clean_kind = kind.strip().lower()
    if clean_kind not in KINDS:
        raise ValueError(f"kind must be one of: {', '.join(sorted(KINDS))}")
    return Session(
        id=session_id(started_at, ended_at, clean_kind, task.strip(), tag.strip()),
        started_at_utc=started_at,
        ended_at_utc=ended_at,
        duration_minutes=round(duration, 2),
        kind=clean_kind,
        task=task.strip(),
        tag=tag.strip(),
        notes=notes.strip(),
        completed=completed,
        source=source,
    )


def session_to_row(session: Session) -> dict[str, str]:
    return {
        "id": session.id,
        "started_at_utc": session.started_at_utc.isoformat().replace("+00:00", "Z"),
        "ended_at_utc": session.ended_at_utc.isoformat().replace("+00:00", "Z"),
        "duration_minutes": f"{session.duration_minutes:.2f}".rstrip("0").rstrip("."),
        "kind": session.kind,
        "task": session.task,
        "tag": session.tag,
        "notes": session.notes,
        "completed": "true" if session.completed else "false",
        "source": session.source,
    }


def row_to_session(row: dict[str, str]) -> Session:
    return Session(
        id=row.get("id", ""),
        started_at_utc=parse_utc(row["started_at_utc"]),
        ended_at_utc=parse_utc(row["ended_at_utc"]),
        duration_minutes=float(row["duration_minutes"]),
        kind=row.get("kind", "focus"),
        task=row.get("task", ""),
        tag=row.get("tag", ""),
        notes=row.get("notes", ""),
        completed=row.get("completed", "false").lower() == "true",
        source=row.get("source", "unknown"),
    )


def ensure_log(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()


def append_session(path: Path, session: Session) -> None:
    ensure_log(path)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writerow(session_to_row(session))


def read_sessions(path: Path) -> list[Session]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = set(CSV_FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"log file is missing columns: {', '.join(sorted(missing))}")
        return [row_to_session(row) for row in reader]


def display_table(sessions: Sequence[Session]) -> str:
    if not sessions:
        return "No sessions found."
    rows = ["started_at_utc        kind      min  tag          task"]
    rows.append("-" * 72)
    for session in sessions:
        started = session.started_at_utc.strftime("%Y-%m-%d %H:%M")
        minutes = f"{session.duration_minutes:g}".rjust(4)
        rows.append(
            f"{started} UTC  {session.kind:<8} {minutes}  "
            f"{session.tag[:12]:<12} {session.task[:36]}"
        )
    return "\n".join(rows)


def date_window(name: str) -> tuple[datetime, datetime]:
    now = utc_now()
    start_of_day = datetime(now.year, now.month, now.day, tzinfo=UTC)
    if name == "today":
        return start_of_day, start_of_day + timedelta(days=1)
    if name == "week":
        start = start_of_day - timedelta(days=start_of_day.weekday())
        return start, start + timedelta(days=7)
    if name == "month":
        start = datetime(now.year, now.month, 1, tzinfo=UTC)
        next_month = datetime(now.year + (now.month // 12), (now.month % 12) + 1, 1, tzinfo=UTC)
        return start, next_month
    raise ValueError(f"unknown window: {name}")


def filter_sessions(
    sessions: Iterable[Session],
    *,
    window: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[Session]:
    filtered = list(sessions)
    if window:
        start, end = date_window(window)
        filtered = [session for session in filtered if start <= session.started_at_utc < end]
    if from_date:
        start = datetime(from_date.year, from_date.month, from_date.day, tzinfo=UTC)
        filtered = [session for session in filtered if session.started_at_utc >= start]
    if to_date:
        end = datetime(to_date.year, to_date.month, to_date.day, tzinfo=UTC) + timedelta(days=1)
        filtered = [session for session in filtered if session.started_at_utc < end]
    return sorted(filtered, key=lambda item: item.started_at_utc)


def stats_text(sessions: Sequence[Session]) -> str:
    total = sum(session.duration_minutes for session in sessions)
    focus = sum(session.duration_minutes for session in sessions if session.kind == "focus")
    completed = sum(1 for session in sessions if session.completed)
    by_tag: dict[str, float] = {}
    for session in sessions:
        key = session.tag or "(untagged)"
        by_tag[key] = by_tag.get(key, 0.0) + session.duration_minutes
    lines = [
        f"sessions: {len(sessions)}",
        f"completed: {completed}",
        f"total_minutes: {total:g}",
        f"focus_minutes: {focus:g}",
    ]
    if by_tag:
        lines.append("by_tag:")
        for tag, minutes in sorted(by_tag.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"  {tag}: {minutes:g}")
    return "\n".join(lines)


def ics_datetime(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def fold_ics_line(line: str) -> list[str]:
    if len(line) <= 75:
        return [line]
    chunks = [line[:75]]
    rest = line[75:]
    while rest:
        chunks.append(f" {rest[:74]}")
        rest = rest[74:]
    return chunks


def render_ics(sessions: Sequence[Session]) -> str:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Vega-Starboard//Vega Pomodoro Log//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    generated = ics_datetime(utc_now())
    for session in sessions:
        summary_task = session.task or session.kind.title()
        summary = f"[{session.kind.title()}] {summary_task}"
        description = "; ".join(
            part for part in [
                f"Tag: {session.tag}" if session.tag else "",
                f"Notes: {session.notes}" if session.notes else "",
                f"Duration: {session.duration_minutes:g} minutes",
                f"Completed: {session.completed}",
            ] if part
        )
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{session.id}@vega-pomodoro-log",
            f"DTSTAMP:{generated}",
            f"DTSTART:{ics_datetime(session.started_at_utc)}",
            f"DTEND:{ics_datetime(session.ended_at_utc)}",
            f"SUMMARY:{ics_escape(summary)}",
            f"DESCRIPTION:{ics_escape(description)}",
        ])
        if session.tag:
            lines.append(f"CATEGORIES:{ics_escape(session.tag)}")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    folded: list[str] = []
    for line in lines:
        folded.extend(fold_ics_line(line))
    return "\r\n".join(folded) + "\r\n"


def run_countdown(total_seconds: int, label: str, *, tick: float = 1.0) -> None:
    end = time.monotonic() + total_seconds
    while True:
        remaining = max(0, int(round(end - time.monotonic())))
        minutes, seconds = divmod(remaining, 60)
        print(f"\r{label}: {minutes:02d}:{seconds:02d}", end="", flush=True)
        if remaining <= 0:
            print()
            return
        time.sleep(min(tick, remaining))


def command_log(args: argparse.Namespace) -> int:
    if args.minutes <= 0:
        raise SystemExit("--minutes must be greater than 0")
    started, ended = default_start_for_manual_log(args.minutes)
    if args.started_at:
        started = parse_utc(args.started_at)
        ended = started + timedelta(minutes=args.minutes)
    session = make_session(
        started_at=started,
        ended_at=ended,
        kind=args.kind,
        task=args.task,
        tag=args.tag,
        notes=args.notes,
        completed=not args.incomplete,
        source="manual",
    )
    append_session(args.log_file, session)
    print(f"logged {session.kind} session {session.id} ({session.duration_minutes:g} min)")
    return 0


def command_start(args: argparse.Namespace) -> int:
    if args.focus <= 0 or args.break_minutes < 0:
        raise SystemExit("durations must be non-negative, and focus must be greater than 0")
    start = utc_now()
    completed = True
    try:
        run_countdown(int(args.focus * 60), "focus", tick=args.tick)
    except KeyboardInterrupt:
        completed = False
        print("\ninterrupted; logging partial focus session")
    end = utc_now()
    session = make_session(
        started_at=start,
        ended_at=end,
        kind="focus",
        task=args.task,
        tag=args.tag,
        notes=args.notes,
        completed=completed,
        source="timer",
    )
    append_session(args.log_file, session)
    print(f"logged focus session {session.id} ({session.duration_minutes:g} min)")
    if completed and args.break_minutes and not args.skip_break:
        run_countdown(int(args.break_minutes * 60), "break", tick=args.tick)
        break_end = utc_now()
        break_session = make_session(
            started_at=end,
            ended_at=break_end,
            kind="break",
            task="Break",
            tag=args.tag,
            notes="",
            completed=True,
            source="timer",
        )
        append_session(args.log_file, break_session)
        print(f"logged break session {break_session.id} ({break_session.duration_minutes:g} min)")
    return 0


def command_list(args: argparse.Namespace) -> int:
    sessions = read_sessions(args.log_file)
    sessions = filter_sessions(sessions, window=args.window, from_date=args.from_date, to_date=args.to_date)
    if args.limit:
        sessions = sessions[-args.limit:]
    print(display_table(sessions))
    return 0


def command_stats(args: argparse.Namespace) -> int:
    sessions = read_sessions(args.log_file)
    sessions = filter_sessions(sessions, window=args.window, from_date=args.from_date, to_date=args.to_date)
    print(stats_text(sessions))
    return 0


def command_export_ics(args: argparse.Namespace) -> int:
    sessions = read_sessions(args.log_file)
    sessions = filter_sessions(sessions, window=args.window, from_date=args.from_date, to_date=args.to_date)
    text = render_ics(sessions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() and not args.force:
        raise SystemExit(f"{args.output} exists; pass --force to overwrite")
    args.output.write_text(text, encoding="utf-8", newline="")
    print(f"exported {len(sessions)} sessions to {args.output}")
    return 0


def command_path(args: argparse.Namespace) -> int:
    ensure_log(args.log_file)
    print(args.log_file)
    return 0


def add_date_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--window", choices=["today", "week", "month"], help="filter by UTC date window")
    parser.add_argument("--from-date", type=parse_local_date, help="include sessions on or after YYYY-MM-DD")
    parser.add_argument("--to-date", type=parse_local_date, help="include sessions on or before YYYY-MM-DD")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vega-pomodoro-log",
        description="Minimalist Pomodoro timer with local CSV logs and ICS export.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=Path(os.environ.get("VEGA_POMODORO_LOG", DEFAULT_LOG)),
        help=f"CSV log path (default: {DEFAULT_LOG})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="run a focus timer and log the session")
    start.add_argument("--focus", type=float, default=25, help="focus duration in minutes")
    start.add_argument("--break", dest="break_minutes", type=float, default=5, help="break duration in minutes")
    start.add_argument("--skip-break", action="store_true", help="do not start a break after focus")
    start.add_argument("--task", default="Focus", help="task label")
    start.add_argument("--tag", default="", help="tag such as bug-bounty, recon, writing, or study")
    start.add_argument("--notes", default="", help="optional session notes")
    start.add_argument("--tick", type=float, default=1.0, help=argparse.SUPPRESS)
    start.set_defaults(func=command_start)

    log = subparsers.add_parser("log", help="append a completed or partial session manually")
    log.add_argument("--task", required=True, help="task label")
    log.add_argument("--minutes", type=float, required=True, help="duration in minutes")
    log.add_argument("--kind", choices=sorted(KINDS), default="focus", help="session kind")
    log.add_argument("--tag", default="", help="tag such as bug-bounty, recon, writing, or study")
    log.add_argument("--notes", default="", help="optional session notes")
    log.add_argument("--started-at", help="UTC ISO timestamp; defaults to now minus duration")
    log.add_argument("--incomplete", action="store_true", help="mark the session incomplete")
    log.set_defaults(func=command_log)

    list_cmd = subparsers.add_parser("list", help="list logged sessions")
    add_date_filters(list_cmd)
    list_cmd.add_argument("--limit", type=int, default=20, help="show the latest N rows after filtering")
    list_cmd.set_defaults(func=command_list)

    stats = subparsers.add_parser("stats", help="summarize logged sessions")
    add_date_filters(stats)
    stats.set_defaults(func=command_stats)

    export = subparsers.add_parser("export-ics", help="export sessions to an iCalendar .ics file")
    add_date_filters(export)
    export.add_argument("--output", type=Path, required=True, help="target .ics file")
    export.add_argument("--force", action="store_true", help="overwrite an existing file")
    export.set_defaults(func=command_export_ics)

    path = subparsers.add_parser("path", help="print and initialize the current log path")
    path.set_defaults(func=command_path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
