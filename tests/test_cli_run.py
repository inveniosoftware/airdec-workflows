# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Tests for the `orcha run` command group."""

import os
import pty
import subprocess

import pytest
from typer.testing import CliRunner

from app.cli.main import (
    _db_files,
    _delete_db_files,
    _stream_output,
    _terminate_all,
    _wait_for_exit,
    _wait_for_temporal,
    app,
)

runner = CliRunner()


def test_run_requires_temporal_cli():
    """`orcha run` fails fast with an install hint when temporal is missing."""
    original_path = os.environ["PATH"]
    os.environ["PATH"] = ""
    try:
        result = runner.invoke(app, ["run"])
    finally:
        os.environ["PATH"] = original_path

    assert result.exit_code == 1
    assert "temporal" in result.output.lower()
    assert "install" in result.output.lower()


def test_db_files_lists_sqlite_siblings(tmp_path):
    """`_db_files` enumerates the db file and its wal/shm/journal siblings."""
    db_path = tmp_path / "orcha.db"
    files = _db_files(db_path)
    assert files == [
        db_path,
        tmp_path / "orcha.db-wal",
        tmp_path / "orcha.db-shm",
        tmp_path / "orcha.db-journal",
    ]


def test_delete_db_files_removes_existing_siblings(tmp_path):
    """`_delete_db_files` removes whichever sibling files actually exist."""
    db_path = tmp_path / "orcha.db"
    for suffix in ("", "-wal", "-journal"):
        db_path.with_name(f"orcha.db{suffix}").write_text("x")

    _delete_db_files(db_path)

    assert not any(tmp_path.glob("orcha.db*"))


def test_delete_db_files_is_noop_when_missing(tmp_path):
    """`_delete_db_files` doesn't error when the files never existed."""
    _delete_db_files(tmp_path / "missing.db")


def test_wait_for_temporal_times_out_on_closed_port():
    """Waiting on a port nothing listens on raises within the given timeout."""
    proc = subprocess.Popen(["sleep", "5"])
    try:
        with pytest.raises(TimeoutError):
            _wait_for_temporal(proc, "127.0.0.1:1", timeout=1.0)
    finally:
        proc.terminate()
        proc.wait()


def test_wait_for_temporal_raises_when_process_exits_early():
    """An early process exit is reported instead of waiting out the timeout."""
    proc = subprocess.Popen(["true"])
    proc.wait()
    with pytest.raises(RuntimeError, match="exited with code 0"):
        _wait_for_temporal(proc, "127.0.0.1:1", timeout=5.0)


def test_wait_for_exit_reports_first_process_that_exits():
    """`_wait_for_exit` returns as soon as one process exits."""
    procs = {
        "short": subprocess.Popen(["sh", "-c", "exit 3"]),
        "long": subprocess.Popen(["sleep", "5"]),
    }
    try:
        name, code = _wait_for_exit(procs, poll_interval=0.05)
        assert (name, code) == ("short", 3)
        assert procs["long"].poll() is None
    finally:
        procs["long"].terminate()
        procs["long"].wait()


def test_terminate_all_stops_every_running_process():
    """`_terminate_all` terminates running processes, leaving exited ones alone."""
    procs = {
        "exited": subprocess.Popen(["true"]),
        "running": subprocess.Popen(["sleep", "5"]),
    }
    procs["exited"].wait()

    _terminate_all(procs)

    assert procs["exited"].returncode == 0
    assert procs["running"].poll() is not None


def test_stream_output_prefixes_each_line(capsys):
    """Output arriving over a pty is relayed line by line behind the marker."""
    read_fd, write_fd = pty.openpty()
    proc = subprocess.Popen(["printf", "one\\ntwo\\n"], stdout=write_fd)
    os.close(write_fd)

    _stream_output(os.fdopen(read_fd, "rb", buffering=0), "api")
    proc.wait()

    assert capsys.readouterr().out == "[api] one\n[api] two\n"


def test_stream_output_relays_colour_codes(capsys):
    """Escape codes survive, which is the point of giving the child a pty."""
    read_fd, write_fd = pty.openpty()
    proc = subprocess.Popen(["printf", "\\033[31mred\\033[0m\\n"], stdout=write_fd)
    os.close(write_fd)

    _stream_output(os.fdopen(read_fd, "rb", buffering=0), "worker")
    proc.wait()

    assert capsys.readouterr().out == "[worker] \033[31mred\033[0m\n"
