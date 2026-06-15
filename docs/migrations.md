# Database Migrations

Alembic is the only mechanism for creating or changing the deployed database
schema. The application and workers do not create tables at startup.

Alembic reads the PostgreSQL connection settings from `app.config.Settings`, so
the same `PGUSER`, `PGPASSWORD`, `PGHOST`, `PGPORT`, and `PGDATABASE` values are
used by both the application and migrations.

Run all commands below from the repository root, where `alembic.ini` is located.

## Initial Deployment

Apply every committed migration before starting the application:

```bash
uv run alembic upgrade head
```

For local setup, the equivalent convenience command is:

```bash
uv run orcha init-db
```

It runs the same Alembic upgrade to `head`; it does not call
`SQLModel.metadata.create_all()`.

The first migration creates the complete initial schema.

## Adding a Migration

1. Make sure the local database is running and up to date:

   ```bash
   uv run orcha services start
   uv run alembic upgrade head
   ```

2. Change the SQLModel table models in `app/database/models.py`.

3. Generate a revision with a short, specific description:

   ```bash
   uv run alembic revision --autogenerate -m "add workflow timestamps"
   ```

4. Review the generated file in `migrations/versions/`. Autogeneration is a
   starting point, not approval of the migration. In particular, check:
   - Renames. Alembic usually sees a rename as one dropped column and one added
     column. Replace those operations with `op.alter_column(...)` so data is
     preserved.
   - New non-null columns. Existing rows may require a server default, a data
     backfill, and then removal of the temporary default.
   - Enum changes. PostgreSQL enum values often need explicit SQL or custom
     operations.
   - Data transformations. Alembic compares schemas, not application meaning,
     so write these operations manually.
   - Constraints, indexes, and server defaults. Confirm they express the
     intended database behavior.

5. Apply the new revision:

   ```bash
   uv run alembic upgrade head
   ```

6. Confirm that the migrated database matches the models:

   ```bash
   uv run alembic check
   ```

7. Run the project checks and commit the model change and generated migration
   together.

## Useful Commands

```bash
# Show the revision currently applied to the database
uv run alembic current

# Show migration history
uv run alembic history

# Show the SQL without applying it
uv run alembic upgrade head --sql

# Revert one revision in a development database
uv run alembic downgrade -1
```

Prefer forward fixes for deployed environments. Downgrades are mainly useful
for testing migration reversibility in disposable development databases.
