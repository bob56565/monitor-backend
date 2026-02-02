# The generic single-database configuration.

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# this is the Alembic Config object, which provides
# the values of the alembic.ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set up Python path
sys.path.insert(0, os.path.dirname(__file__) + '/..')

# add your model's MetaData object here
# for 'autogenerate' support
from app.db.base import Base
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    configuration = config.get_section(config.config_ini_section)
    # Use SQLite by default like the app
    configuration["sqlalchemy.url"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///./monitor.db"
    )

    context.configure(
        url=configuration["sqlalchemy.url"],
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    # Use SQLite by default like the app
    configuration["sqlalchemy.url"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///./monitor.db"
    )

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
