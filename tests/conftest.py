import asyncio
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "app"
TEST_DB_PATH = ROOT / ".pytest-data" / "lp_catalog_test.sqlite3"
TEST_DB_PATH.parent.mkdir(exist_ok=True)
COVERS_DIR = ROOT / ".pytest-data" / "covers"
COVERS_DIR.mkdir(exist_ok=True)

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["ALLOWED_ORIGINS"] = "http://testserver"
os.environ["AUTO_APPLY_MIGRATIONS"] = "true"
os.environ["COVERS_DIR"] = str(COVERS_DIR)

if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from db.session import AsyncSessionLocal, engine  # noqa: E402
from main import app  # noqa: E402
from models.album import Album  # noqa: E402
from models.artist import Artist  # noqa: E402
from models.copy import Copy, CopyLocationHistory, CopyPhoto, PhotoAnalysisSuggestion  # noqa: E402
from models.track import Track  # noqa: E402


async def reset_database():
    async with AsyncSessionLocal() as session:
        await session.execute(delete(CopyLocationHistory))
        await session.execute(delete(PhotoAnalysisSuggestion))
        await session.execute(delete(CopyPhoto))
        await session.execute(delete(Copy))
        await session.execute(delete(Track))
        await session.execute(delete(Album))
        await session.execute(delete(Artist))
        await session.commit()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(engine.dispose())
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(autouse=True)
def clean_database(client):
    asyncio.run(reset_database())
    yield
    asyncio.run(reset_database())
