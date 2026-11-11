from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.database import Base
from app.models import user, subject, course, course_schedule
from app.models import building, room, notice, notice_read
from app.models import timetable, timetable_course, custom_schedule, wizard_selection
from app.models import daily_menu, menu_item
from app.models import academic_calendar_event
from app.models import notification_setting, completed_course, graduation_standard
from app.models import user_notification
from app.models import app_release
from app.models import user_presence
from app.models import shuttle_map
from app.models.shuttle_map import (
    shuttle_map_routes,
    shuttle_map_schedules,
    shuttle_map_schedule_stops,
    shuttle_map_stops,
)
from app.models import messenger, room_messengers, room_participants
from app.models import friend_invite, password_reset_request_log, password_reset_token
from app.models import ai_chat_room, ai_message
from app.models import subway_line_station
from app.models import refresh_session
from app.models import biometric_Credential

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 배포 환경에서는 alembic.ini의 로컬 기본값보다 DATABASE_URL을 우선한다.
# URL에 퍼센트 인코딩이 포함되어도 ConfigParser가 다시 해석하지 않도록
# '%'를 이스케이프한다.
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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
