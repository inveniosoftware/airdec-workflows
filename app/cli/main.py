import subprocess
import sys
from pathlib import Path

import typer
from sqlmodel import SQLModel

from app.database.models import Workflow  # noqa: F401
from app.database.session import get_engine

app = typer.Typer(help="AIRDEC CLI tools.")
services_app = typer.Typer(help="Manage infrastructure services (PostgreSQL + Temporal).")
app.add_typer(services_app, name="services")


@app.command()
def init_db():
    """Create all database tables from models."""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    typer.echo("Database tables created successfully.")


@services_app.command()
def start():
    """Start infrastructure services."""
    typer.echo("Starting services...")
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=Path(__file__).resolve().parents[2],
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    app()
