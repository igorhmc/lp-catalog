import asyncio
import fcntl
from pathlib import Path

from alembic import command
from alembic.config import Config

from core.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI_PATH = BASE_DIR / "alembic.ini"
MIGRATIONS_PATH = BASE_DIR / "migrations"
MIGRATIONS_LOCK_PATH = Path("/tmp/lp_catalog_migrations.lock")


def run_migrations() -> None:
    with MIGRATIONS_LOCK_PATH.open("w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        config = Config(str(ALEMBIC_INI_PATH))
        config.set_main_option("script_location", str(MIGRATIONS_PATH))
        config.set_main_option("sqlalchemy.url", get_settings().sync_db_uri)
        command.upgrade(config, "head")

async def init_database():
    settings = get_settings()
    if settings.AUTO_APPLY_MIGRATIONS:
        await asyncio.to_thread(run_migrations)
