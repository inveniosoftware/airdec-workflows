# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

import signal
import subprocess
import sys
from pathlib import Path

import typer
from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[2]

app = typer.Typer(help="Orcha CLI tools.")
services_app = typer.Typer(
    help="Manage infrastructure services (PostgreSQL + Temporal)."
)
run_app = typer.Typer(help="Run application processes.")
app.add_typer(services_app, name="services")
app.add_typer(run_app, name="run")


@app.command()
def migrate():
    """Apply all database migrations."""
    command.upgrade(Config(PROJECT_ROOT / "alembic.ini"), "head")
    typer.echo("Database migrations applied successfully.")


# ── services ──


@services_app.command()
def start():
    """Start infrastructure services."""
    typer.echo("Starting services...")
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=PROJECT_ROOT,
    )
    sys.exit(result.returncode)


@services_app.command()
def stop():
    """Stop infrastructure services."""
    typer.echo("Stopping services...")
    result = subprocess.run(
        ["docker", "compose", "down"],
        cwd=PROJECT_ROOT,
    )
    sys.exit(result.returncode)


# ── run ──


@run_app.command()
def server(
    dev: bool = typer.Option(
        False, "--dev", help="Run in development mode with hot reload."
    ),
):
    """Start the FastAPI server."""
    if dev:
        typer.echo("Starting FastAPI development server...")
        cmd = ["uv", "run", "fastapi", "dev", "app/main.py"]
    else:
        typer.echo("Starting FastAPI server...")
        cmd = ["uv", "run", "fastapi", "run", "app/main.py"]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    sys.exit(result.returncode)


@run_app.command()
def workers(task_queue: str | None = None):
    """Start the Temporal worker."""
    typer.echo("Starting Temporal worker...")
    command = ["uv", "run", "python", "-m", "app.workers"]
    if task_queue is not None:
        command.extend(["--task-queue", task_queue])
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
    )
    sys.exit(result.returncode)


@run_app.callback(invoke_without_command=True)
def run_all(ctx: typer.Context):
    """Start both the FastAPI server and Temporal worker."""
    if ctx.invoked_subcommand is not None:
        return

    typer.echo("Starting server and worker...")
    procs = [
        subprocess.Popen(
            ["uv", "run", "fastapi", "dev", "app/main.py"],
            cwd=PROJECT_ROOT,
        ),
        subprocess.Popen(
            ["uv", "run", "python", "-m", "app.workers"],
            cwd=PROJECT_ROOT,
        ),
    ]

    def _shutdown(sig, frame):
        for p in procs:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    for p in procs:
        p.wait()


if __name__ == "__main__":
    app()
