# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Utils for activities."""

from urllib.parse import urlparse

from app.config import get_settings


def http_verify(url: str) -> bool:
    """Whether to verify TLS when talking to an Invenio instance."""
    settings = get_settings()

    parsed_url = urlparse(url)
    hostname = (parsed_url.hostname or "").lower()

    if hostname in ("localhost", "127.0.0.1", "::1") or hostname.endswith(".localhost"):
        return False

    allowlist = {
        host.strip().lower()
        for host in (settings.http_allowlist or "").split(",")
        if host.strip()
    }

    if hostname not in allowlist:
        raise ValueError(f"'{hostname}' is not an allowed domain")

    return True
