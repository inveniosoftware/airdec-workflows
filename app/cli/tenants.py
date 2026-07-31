# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Tenant registration and token minting."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
import typer

from app.config import get_settings

tenants_app = typer.Typer(help="Manage tenant keys.")


@tenants_app.command("list")
def list_tenants():
    """List the registered tenants and their key IDs."""
    registry_path = Path(get_settings().tenants_config_path)
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}

    if not registry:
        typer.echo(f"No tenants registered in {registry_path}.")
        return

    for tenant_id, entry in registry.items():
        kids = ", ".join(entry.get("public_keys", {}))
        typer.echo(f"{tenant_id} ({entry.get('name', tenant_id)}): {kids}")


@tenants_app.command()
def add(
    tenant: str,
    public_key: Path = typer.Argument(..., help="The tenant's public key file."),
    kid: str = "kid-1",
    name: str | None = None,
    force: bool = typer.Option(False, help="Replace an existing key."),
):
    """Register a public key a tenant sent you."""
    registry_path = Path(get_settings().tenants_config_path)
    registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}

    entry = registry.setdefault(tenant, {"name": name or tenant, "public_keys": {}})
    if name:
        entry["name"] = name
    if kid in entry["public_keys"] and not force:
        raise typer.BadParameter(
            f"key '{kid}' is already registered for tenant '{tenant}', "
            "pass --force to replace it"
        )

    entry["public_keys"][kid] = public_key.read_text()
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2) + "\n")

    typer.echo(f"Registered '{kid}' for tenant '{tenant}' in {registry_path}.")


@tenants_app.command()
def token(
    tenant: str,
    key: Path = typer.Argument(..., help="Private key to sign the token with."),
    kid: str = "kid-1",
    workflow_id: str | None = None,
    expires_in: int = typer.Option(3600, help="Token lifetime in seconds."),
):
    """Print a signed tenant token for calling the API."""
    claims: dict[str, Any] = {
        "iss": tenant,
        "exp": datetime.now(UTC) + timedelta(seconds=expires_in),
    }
    if workflow_id:
        claims["workflow_id"] = workflow_id

    typer.echo(
        jwt.encode(
            claims,
            key.read_text(),
            algorithm=get_settings().jwt_algorithm,
            headers={"kid": kid},
        )
    )
