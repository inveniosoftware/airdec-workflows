## [Unreleased]

## [0.1.1] - 2026-06-17

### 🚀 Features

- *(db)* Add alembic; initial migration
- *(helm)* Add initial chart for orcha
  - Added the Helm chart for deploying Orcha (with support for tenants)
  - Added deployment documentation (available in charts/orcha/README.md)

### ⚙️ Miscellaneous Tasks

- Add optional tag to manual trigger for dockerpublish.yml
- Upgrade actions to use Node.js 24
## [0.0.1] - 2026-06-09
_First release._

### 🚀 Features

- Migrate cli to typer; add service start; README
- *(cli)* Add service and run commands
- *(auth)* Asymmetric JWT for auth
- User pydantic settings for env vars
- *(auth/tenants)* Add support for tenants
- *(auth/key-rotation)* Support key rotation/multiple keys per tenant
- Added extraction modules and option to extract page ranges
- Add BaseExtractor base class
- Return page numbers as list
- LLM title and abstract extraction
- LLM extraction also extracts authors now
- *(result)* Add result field to model; add save result activity
- *(suggestions)* Return suggestions from metadata extraction and persist
- *(suggestions)* Extend LLM extraction with DOI and publication date
- *(workflow)* Add support for different workflows; workflow registry

### 🐛 Bug Fixes

- Fix formatting in pymupdf.py
- Remove user_id
- Allow only cross origin GET requests
- Explicit token check for stream
- Update api method names
- Make get_engine fail-fast when engine is uninitialized
- Cli: explicit engine init
- Check token exists explicitly
- Activites: explicit raise if page selection not valid in extract pdf
- Use pydantic data converter

### 🚜 Refactor

- New folder structure and switch to fastapi sqlmodel
- Rename service to orcha
- Use context manager for DB sessions in activities, add get_db_session for FastAPI
- Move result schemas separately
- Use builder pattern for workflow requests; remove url from model
- Remove builder; separate param models
- Register workflows in registry; change worker queues

### 🧪 Testing

- Add tests for auth
- Add tests job
- Use get_db_session

### ⚙️ Miscellaneous Tasks

- Create cli, add init-db
- (temp) remove alembic
- Update README
- Add CI and linter
- Move to 3.14
- Create Dockerfile and add docker-compose
  - Whitelist .dockerignore
  - Add docker publish workflow
- Add ty typechecker
- *(licenses)* Update license headers to use SPDX

