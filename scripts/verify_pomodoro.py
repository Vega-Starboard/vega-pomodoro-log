#!/usr/bin/env python3
"""Static and behavioral checks for Vega Pomodoro Log."""

from __future__ import annotations

import csv
import os
import py_compile
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "vega_pomodoro_log" / "cli.py"


def fail(message: str) -> None:
    print(f"verify_pomodoro: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, "-m", "vega_pomodoro_log", *args],
        cwd=cwd,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        fail(f"command failed: {' '.join(args)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    return result


def assert_static() -> None:
    py_compile.compile(str(PACKAGE), doraise=True)
    text = PACKAGE.read_text(encoding="utf-8")
    forbidden = [
        "requests",
        "urllib",
        "http.client",
        "socket",
        "subprocess",
        "telnetlib",
        "ftplib",
    ]
    for marker in forbidden:
        if marker in text:
            fail(f"forbidden network/process marker found: {marker}")
    for marker in ["csv.DictWriter", "BEGIN:VCALENDAR", "BEGIN:VEVENT", "argparse.ArgumentParser", "datetime.now(UTC)"]:
        if marker not in text:
            fail(f"required marker missing: {marker}")


def assert_behavior() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        log_file = tmp / "sessions.csv"
        ics_file = tmp / "sessions.ics"
        run(
            "--log-file",
            str(log_file),
            "log",
            "--task",
            "HackerOne recon block",
            "--minutes",
            "25",
            "--tag",
            "bug-bounty",
            "--notes",
            "Scoped target review",
        )
        if not log_file.exists():
            fail("log file was not created")
        with log_file.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if len(rows) != 1:
            fail(f"expected 1 CSV row, got {len(rows)}")
        row = rows[0]
        if row["task"] != "HackerOne recon block" or row["tag"] != "bug-bounty":
            fail("CSV row content mismatch")
        if row["completed"] != "true" or row["duration_minutes"] != "25":
            fail("CSV completion or duration mismatch")

        listed = run("--log-file", str(log_file), "list")
        if "HackerOne recon block" not in listed.stdout:
            fail("list output missing task")

        stats = run("--log-file", str(log_file), "stats")
        if "focus_minutes: 25" not in stats.stdout:
            fail("stats output missing focus minutes")

        run("--log-file", str(log_file), "export-ics", "--output", str(ics_file))
        text = ics_file.read_text(encoding="utf-8")
        for marker in ["BEGIN:VCALENDAR", "VERSION:2.0", "BEGIN:VEVENT", "DTSTART:", "DTEND:", "SUMMARY:", "END:VCALENDAR"]:
            if marker not in text:
                fail(f"ICS missing marker: {marker}")


def assert_docs() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for marker in [
        "shields.io",
        "Local Only",
        "CSV",
        "iCalendar",
        "HackerOne",
        "No telemetry",
        "Python standard library",
    ]:
        if marker not in readme:
            fail(f"README missing marker: {marker}")


def main() -> int:
    assert_static()
    assert_behavior()
    assert_docs()
    print("pomodoro log verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
