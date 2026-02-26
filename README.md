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

This starts:

| Service           | Port  | Description                     |
| ----------------- | ----- | ------------------------------- |
| PostgreSQL        | 5433  | Application database (`airdec`)|
| Temporal Server   | 7233  | Workflow orchestration          |
| Temporal UI       | 8080  | Web dashboard                   |

### 3. Create database tables

```bash
uv run airdec init-db
```

### 4. Start the FastAPI server

```bash
uv run fastapi dev app/main.py
```

### 5. Start the Temporal worker (separate terminal)

```bash
uv run python -m app.workers
```

## Useful Commands

```bash
# Stop all services
docker compose down

# Stop and remove volumes (reset databases)
docker compose down -v

# View service logs
docker compose logs -f

# Open Temporal UI
open http://localhost:8080
```
