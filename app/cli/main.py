import click

from app.database.session import get_engine
from app.database.models import Workflow  # noqa: F401
from sqlmodel import SQLModel


@click.group()
def cli():
    """AIRDEC CLI tools."""
    pass


@cli.command()
def init_db():
    """Create all database tables from models."""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    click.echo("Database tables created successfully.")


if __name__ == "__main__":
    cli()
