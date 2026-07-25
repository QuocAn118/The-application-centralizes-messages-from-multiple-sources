"""Cấu hình môi trường migration của Alembic."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import để Base.metadata biết tới các bảng. Không import thì autogenerate
# sẽ sinh ra migration rỗng.
from src.modules.identity.infrastructure.models.audit_log_model import AuditLogModel  # noqa: F401
from src.modules.identity.infrastructure.models.department_model import (  # noqa: F401
    DepartmentModel,
)
from src.modules.identity.infrastructure.models.refresh_token_model import (  # noqa: F401
    RefreshTokenModel,
)
from src.modules.identity.infrastructure.models.user_model import UserModel  # noqa: F401
from src.modules.inbox.infrastructure.models.attachment_model import (  # noqa: F401
    AttachmentModel,
)
from src.modules.inbox.infrastructure.models.channel_model import ChannelModel  # noqa: F401
from src.modules.inbox.infrastructure.models.conversation_model import (  # noqa: F401
    ConversationModel,
)
from src.modules.inbox.infrastructure.models.customer_model import (  # noqa: F401
    CustomerModel,
)
from src.modules.inbox.infrastructure.models.message_model import MessageModel  # noqa: F401
from src.shared.infrastructure.config import get_settings
from src.shared.infrastructure.database import Base
from src.shared.infrastructure.event_loop import cau_hinh_event_loop

# Alembic gọi asyncio.run() để chạy migration — cần đúng loại event loop mà
# psycopg chấp nhận, giống mọi entry point async khác.
cau_hinh_event_loop()

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
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


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
