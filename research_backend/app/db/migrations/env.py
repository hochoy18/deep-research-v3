"""Alembic env 配置（async-aware）。

关键点：
- target_metadata = app.db.models.Base.metadata（M1 单一 source of truth）
- run_migrations_online 用 sync engine（alembic 官方约定）
- 通过 app.db._url_utils.to_sync_database_url() 兼容 async/sync URL
"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db._url_utils import to_sync_database_url
from app.db.models import Base


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 不连接 DB。"""
    context.configure(
        url=to_sync_database_url(config.get_main_option("sqlalchemy.url")),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：连真实 DB 跑迁移。"""
    cfg_section = config.get_section(config.config_ini_section) or {}
    cfg_section["sqlalchemy.url"] = to_sync_database_url(
        config.get_main_option("sqlalchemy.url")
    )
    connectable = engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
