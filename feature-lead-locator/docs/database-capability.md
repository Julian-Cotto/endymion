# Database capability

## PostgreSQL

This feature includes PostgreSQL support using SQLAlchemy.

### Main files

- `backend/app/platform/database/config.py`
- `backend/app/platform/database/base.py`
- `backend/app/platform/database/session.py`

## Migrations

Alembic is configured for schema migrations.

### Commands

```bash
cd backend

# create migration
alembic revision --autogenerate -m "init"

# apply migrations
alembic upgrade head

# rollback
alembic downgrade -1
```

You can also use `scripts/run-migrations.sh` (or `.ps1`) from the repository root when those scripts are generated.


