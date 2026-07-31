# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Tests for the `orcha tenants` command group."""

import jwt
import pytest
import typer.rich_utils
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from typer.testing import CliRunner

from app.cli.main import app
from app.config import get_settings
from app.tenants import TenantRegistry

runner = CliRunner()


@pytest.fixture(autouse=True)
def plain_output(monkeypatch):
    """Keep error output unstyled.

    Typer forces a colour terminal under GITHUB_ACTIONS, and rich then splits
    flags like ``--force`` with escape codes, so assertions on them fail.
    """
    monkeypatch.setattr(typer.rich_utils, "FORCE_TERMINAL", False)


@pytest.fixture
def registry_path(tmp_path, monkeypatch):
    """Point the tenant registry at a temporary file."""
    path = tmp_path / "tenants.json"
    monkeypatch.setenv("TENANTS_CONFIG_PATH", str(path))
    get_settings.cache_clear()
    yield path
    get_settings.cache_clear()


@pytest.fixture
def public_key_file(tmp_path):
    """Write a freshly generated public key to disk."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path = tmp_path / "public_key.pem"
    path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return path


def test_add_registers_a_public_key(registry_path, public_key_file):
    """`tenants add` puts the key in the registry under the given tenant."""
    result = runner.invoke(
        app, ["tenants", "add", "zenodo", str(public_key_file), "--name", "Zenodo"]
    )

    assert result.exit_code == 0
    tenant = TenantRegistry.from_file(registry_path).get_tenant("zenodo")
    assert tenant is not None
    assert tenant.name == "Zenodo"
    assert tenant.public_keys == {"kid-1": public_key_file.read_text()}


def test_add_keeps_other_keys_and_tenants(registry_path, public_key_file):
    """A second `tenants add` leaves earlier registrations in place."""
    runner.invoke(app, ["tenants", "add", "zenodo", str(public_key_file)])
    runner.invoke(
        app, ["tenants", "add", "zenodo", str(public_key_file), "--kid", "kid-2"]
    )
    runner.invoke(app, ["tenants", "add", "cds", str(public_key_file)])

    registry = TenantRegistry.from_file(registry_path)
    assert sorted(registry.tenant_ids) == ["cds", "zenodo"]
    zenodo = registry.get_tenant("zenodo")
    assert zenodo is not None
    assert sorted(zenodo.public_keys) == ["kid-1", "kid-2"]


def test_add_refuses_to_replace_a_key_without_force(
    registry_path, public_key_file, tmp_path
):
    """Re-registering a key ID fails unless --force is given."""
    runner.invoke(app, ["tenants", "add", "zenodo", str(public_key_file)])
    replacement = tmp_path / "replacement.pem"
    replacement.write_text("-----BEGIN PUBLIC KEY-----\nreplaced\n")

    result = runner.invoke(app, ["tenants", "add", "zenodo", str(replacement)])
    assert result.exit_code != 0
    assert "--force" in result.output

    registry = TenantRegistry.from_file(registry_path)
    tenant = registry.get_tenant("zenodo")
    assert tenant is not None
    assert tenant.public_keys["kid-1"] == public_key_file.read_text()

    forced = runner.invoke(
        app, ["tenants", "add", "zenodo", str(replacement), "--force"]
    )
    assert forced.exit_code == 0
    tenant = TenantRegistry.from_file(registry_path).get_tenant("zenodo")
    assert tenant is not None
    assert tenant.public_keys["kid-1"] == replacement.read_text()


def test_list_reports_tenants_and_key_ids(registry_path, public_key_file):
    """`tenants list` prints each tenant with its registered key IDs."""
    empty = runner.invoke(app, ["tenants", "list"])
    assert empty.exit_code == 0
    assert "No tenants registered" in empty.output

    runner.invoke(
        app, ["tenants", "add", "zenodo", str(public_key_file), "--name", "Zenodo"]
    )
    result = runner.invoke(app, ["tenants", "list"])

    assert result.exit_code == 0
    assert "zenodo (Zenodo): kid-1" in result.output


def test_token_signs_claims_for_a_registered_key(registry_path, tmp_path):
    """`tenants token` mints a token the registered public key verifies."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_path = tmp_path / "private_key.pem"
    key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_key_path = tmp_path / "registered.pem"
    public_key_path.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    runner.invoke(app, ["tenants", "add", "zenodo", str(public_key_path)])

    result = runner.invoke(
        app,
        ["tenants", "token", "zenodo", str(key_path), "--workflow-id", "wf-123"],
    )

    assert result.exit_code == 0
    tenant = TenantRegistry.from_file(registry_path).get_tenant("zenodo")
    assert tenant is not None
    encoded = result.output.strip()
    assert jwt.get_unverified_header(encoded)["kid"] == "kid-1"
    claims = jwt.decode(
        encoded, tenant.public_keys["kid-1"], algorithms=["RS256"], issuer="zenodo"
    )
    assert claims["workflow_id"] == "wf-123"
