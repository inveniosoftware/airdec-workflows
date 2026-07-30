# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Application-wide Temporal client, initialized at startup."""

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from .config import get_settings

_client: Client | None = None


async def init_temporal_client() -> Client:
    """Connect and store the global Temporal client."""
    global _client
    settings = get_settings()
    _client = await Client.connect(
        settings.temporal_host,
        data_converter=pydantic_data_converter,
    )
    return _client


def dispose_temporal_client() -> None:
    """Forget the global Temporal client."""
    global _client
    _client = None


def get_temporal_client() -> Client:
    """Return the global Temporal client, if initialized."""
    if _client is None:
        raise RuntimeError("Temporal client is not initialized!")
    return _client
