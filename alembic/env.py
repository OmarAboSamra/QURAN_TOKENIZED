"""
Alembic environment configuration.

Reads the database URL from backend.config so that Alembic always targets the
same database as the running application.  All ORM models are imported so that
Base.metadata contains the full schema for autogenerate support.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ── Alembic Config object ────────────────────────────────────────
config = context.config

# Python logging from the .ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import application models & metadata ─────────────────────────
# These imports register every table with Base.metadata so autogenerate
# can detect schema changes.
from backend.db import Base  # noqa: E402
from backend.models.token_model import Token  # noqa: E402, F401
from backend.models.root_model import Root  # noqa: E402, F401
from backend.models.verse_model import Verse  # noqa: E402, F401

target_metadata = Base.metadata

# ── Override sqlalchemy.url from app config ──────────────────────
# This keeps the single source of truth in backend.config / .env rather
# than duplicating the URL in alembic.ini.
from backend.config import get_settings  # noqa: E402

_settings = get_settings()
_db_url = _settings.database_url

# Alembic requires a *synchronous* URL.  Convert aiosqlite / asyncpg to sync.
_db_url = _db_url.replace("sqlite+aiosqlite", "sqlite")
_db_url = _db_url.replace("postgresql+asyncpg", "postgresql")

config.set_main_option("sqlalchemy.url", _db_url)


# ── Offline (SQL-script) mode ────────────────────────────────────
def run_migrations_offline() -> None:
    """Generate SQL script without connecting to the database."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # required for SQLite ALTER TABLE support
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online (live connection) mode ────────────────────────────────
def run_migrations_online() -> None:
    """Run migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # required for SQLite ALTER TABLE support
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
