# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

FROM python:3.14-slim-bookworm

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:0.9.11 /uv /bin/uv

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --locked --no-cache

# Create a non-root user and fix permissions for OpenShift.
# OpenShift assigns a random UID at runtime, but the GID is always 0 (root).
RUN chgrp -R 0 /app && chmod -R g=u /app
USER 1001

# Run the application.
CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--port", "8000"]
