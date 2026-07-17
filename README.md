# Orcha

Orcha AI extraction.

## Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python ≥ 3.14

## Local Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Run the complete local stack

SQLite is the local-development default, so no Docker services are required.
`orcha run` applies migrations against a local `orcha.db` file, starts a
Temporal dev server backed by `temporal.db`, then the API and a worker:

```bash
uv run orcha run
```

This requires the [`temporal` CLI](https://docs.temporal.io/cli#install) to
be installed. Stopping it (Ctrl-C) preserves both database files; pass
`--reset` to delete them first and start from a clean state:

```bash
uv run orcha run --reset
```

### Running against PostgreSQL

To use PostgreSQL instead (e.g. to match production), start the Dockerized
services, point the app at them, and run the API and worker as separate
processes:

```bash
uv run orcha services start
export DB_DIALECT=postgresql   # DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME
                                # default to the docker-compose values
uv run orcha migrate
uv run orcha run server --dev  # FastAPI dev server
uv run orcha run workers       # Temporal worker for the default queue

# Run a worker for a specific queue
uv run orcha run workers --task-queue low-priority
```

## Authentication

The API uses **multi-tenant RS256 (asymmetric) JWT authentication**. Each tenant has its own RSA key pair(s). The tenant signs tokens with their private key; the server verifies them using the tenant's registered public key.

Tenants are identified by the `iss` (issuer) claim in the JWT. To support zero-downtime key rotation, the server allows multiple public keys per tenant. In token headers, tenants must include a Key ID (`kid`) that matches one of their defined keys in the configuration.

### Tenant Configuration

Create a `tenants.json` file at the project root:

```json
{
  "tenant-a": {
    "name": "Tenant A",
    "public_keys": {
      "kid-1": "-----BEGIN PUBLIC KEY-----\nMIIBI...\n-----END PUBLIC KEY-----"
    }
  },
  "tenant-b": {
    "name": "Tenant B",
    "public_keys": {
      "kid-1": "-----BEGIN PUBLIC KEY-----\nMIIBI...\n-----END PUBLIC KEY-----"
    }
  }
}
```

Each key in the JSON must match the `iss` claim the tenant will use in their JWTs.

> ⚠️ **Never commit `tenants.json` or `.pem` files** — they are already in `.gitignore`.

### Generating RSA Keys (Tenant-Side)

Each tenant generates their own key pair and sends you **only the public key**:

```bash
# Generate a 2048-bit RSA private key (tenant keeps this secret)
openssl genpkey -algorithm RSA -out private_key.pem -pkeyopt rsa_keygen_bits:2048

# Extract the public key (send this to the server operator)
openssl rsa -pubout -in private_key.pem -out public_key.pem
```

### Configuration

| Variable              | Description                              | Required    |
| --------------------- | ---------------------------------------- | ----------- |
| `JWT_ALGORITHM`       | Signing algorithm (default: RS256)       | No          |
| `AUTH_DISABLED`       | Set to `true` to skip auth               | Development |
| `TENANTS_CONFIG_PATH` | Path to tenants JSON (default: tenants.json) | Production  |

**Local development** — bypass authentication entirely:

```bash
export AUTH_DISABLED=true
```

### Creating a Test Token (Tenant-Side)

Tokens **must** include the `iss` claim matching the tenant ID. Optionally include `workflow_id` to scope access.

```python
import jwt
from datetime import datetime, timedelta, timezone

private_key = open("private_key.pem").read()

token = jwt.encode(
    {
        "iss": "tenant-a",                                    # Required: must match tenants.json key
        "workflow_id": "YOUR_WORKFLOW_ID",                    # Optional: scope to a specific workflow
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    },
    private_key,
    algorithm="RS256",
    headers={"kid": "kid-1"}                                  # Required: must match kid in tenants.json public_keys
)
print(token)
```

Use the token:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/workflows/<YOUR_WORKFLOW_ID>
```

### LLM Configuration

The service supports multiple LLM backends. Configure a single setting, `LLM`,
in the form `<provider>/<model>`.

#### LiteLLM (default/recommended)

```bash
export LLM="litellm/groq/qwen/qwen3-32b"
```

Optional configuration:

```bash
export LITELLM_API_BASE="<litellm-endpoint>"
export LITELLM_API_KEY="<api-key>"
```

#### Ollama (local/dev)

```bash
export LLM="ollama/llama3.1"
export OLLAMA_BASE_URL="http://localhost:11434/v1"
```


## CLI Reference

| Command                            | Description                               |
|------------------------------------|-------------------------------------------|
| `orcha services start`             | Start PostgreSQL + Temporal via Docker    |
| `orcha services stop`              | Stop all Docker services                  |
| `orcha migrate`                    | Apply all database migrations             |
| `orcha run`                        | Migrate, then start Temporal, API, and worker (SQLite) |
| `orcha run --reset`                | Same, after deleting `orcha.db` and `temporal.db` |
| `orcha run server`                 | Start the FastAPI server only             |
| `orcha run server --dev`           | Start the FastAPI server with hot reload  |
| `orcha run workers`                | Start Temporal worker for default queue   |
| `orcha run workers --task-queue Q` | Start Temporal worker for a specific queue |

## Database Migrations

The deployed schema is managed with Alembic. Apply committed migrations with:

```bash
uv run alembic upgrade head
```

For local setup, `uv run orcha migrate` is a convenience wrapper around the
same Alembic upgrade.

See [Database Migrations](docs/migrations.md) for the full process of generating
and reviewing migrations when SQLModel models change.

## Useful Commands

```bash
# Stop and remove volumes (reset databases)
docker compose down -v

# View Docker service logs
docker compose logs -f

# Open Temporal UI
open http://localhost:8080
```

## Releasing

Release for Orcha are done manually. Pushing a `v*` tag triggers the image build, so commit the version bump and changelog before you tag.

### 1. Bump the version

Bump `pyproject.toml` and re-lock in one step:

```bash
uv version --bump patch   # or: minor, major
```

Then set the same `X.Y.Z` in `charts/orcha/Chart.yaml`, in both `version` and `appVersion`.

### 2. Update the changelog

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/). Every `feat:`/`fix:`/`refactor:` commit should already have a bullet under `## [Unreleased]`. At release time, promote that section:

- Rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` and open a fresh empty `## [Unreleased]` above it.
- In the link footer, repoint `[unreleased]` to `vX.Y.Z...HEAD` and add `[X.Y.Z]: .../compare/<prev>...vX.Y.Z`.

### 3. Commit, tag, and push

```bash
git commit -am "release: vX.Y.Z"
git tag vX.Y.Z
git push origin main vX.Y.Z
```

The tag push kicks off the Docker workflow below, which builds and publishes the image.

## Docker Image Release

Docker images are automatically built and published to `registry.cern.ch/orcha/orcha` by the [Docker workflow](.github/workflows/dockerpublish.yml).

### Triggers

| Event | Image tag |
|---|---|
| Push a `v*` tag (e.g. `v1.2.3`) | `1.2.3` |
| Manual via GitHub UI (`workflow_dispatch`) | depends on branch/tag |

### Required secrets

The workflow uses two repository secrets that must be configured in `Settings → Secrets and variables → Actions`:

| Secret | Description                     |
|---|---------------------------------|
| `REGISTRY_USER` | registry robot account username |
| `REGISTRY_PASSWORD` | registry robot account password |
