import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.core.config import get_settings
from app.db import Base

# Это объект конфигурации Alembic; он дает доступ
# к значениям из используемого .ini-файла.
config = context.config

# Настраиваем Python-логирование из файла конфигурации.
# Эта строка инициализирует логгеры.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Укажите здесь MetaData моделей для поддержки autogenerate.
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# При необходимости здесь можно получать другие значения из конфигурации:
# my_important_option = config.get_main_option("my_important_option")
# ... и т. д.


def run_migrations_offline() -> None:
    """Запускает миграции в офлайн-режиме.

    Контекст настраивается только URL-адресом без Engine, хотя Engine здесь
    тоже допустим. Если не создавать Engine, для запуска не нужен DBAPI.

    Вызовы context.execute() в этом режиме выводят переданную строку в скрипт.

    """
    settings = get_settings()
    url = settings.postgres.url

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations(configuration: dict[str, str]) -> None:
    """Создает движок и подключает объект к контексту миграций.

    """

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запускает миграции в онлайн-режиме."""
    settings = get_settings()
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.postgres.url

    asyncio.run(run_async_migrations(configuration))


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
