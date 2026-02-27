# AIRDEC Workflows [Temporary]

Backend service for AIRDEC AI extraction, built with **FastAPI**, **Temporal**, and **PostgreSQL**.

## Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python ≥ 3.14

## Local Setup

### 1. Install dependencies

```bash
uv sync
```

### 2. Start infrastructure (PostgreSQL + Temporal)

```bash
uv run airdec services start
```

### 3. Create database tables

```bash
uv run airdec init-db
```

### 4. Start the application

```bash
# Start both server and worker
uv run airdec run

# Or start them individually
uv run airdec run server     # FastAPI dev server
uv run airdec run workers    # Temporal worker
```

## CLI Reference

| Command                      | Description                              |
| ---------------------------- | ---------------------------------------- |
| `airdec services start`     | Start PostgreSQL + Temporal via Docker   |
| `airdec services stop`      | Stop all Docker services                 |
| `airdec init-db`            | Create database tables from models       |
| `airdec run`                | Start both server and worker             |
| `airdec run server`         | Start FastAPI dev server only            |
| `airdec run workers`        | Start Temporal worker only               |

## Useful Commands

```bash
# Stop and remove volumes (reset databases)
docker compose down -v

# View Docker service logs
docker compose logs -f

# Open Temporal UI
open http://localhost:8080
```
