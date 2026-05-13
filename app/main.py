import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from api.v1 import albums_router, artists_router, copies_router, health_router
from api.v1.copies import build_storage_overview
from core.config import get_settings
from db.init_db import init_database
from db.session import AsyncSessionLocal, get_db
from models.album import Album
from models.artist import Artist
from models.copy import Copy, CopyLocationHistory
from models.storage import StorageSlot, StorageUnit
from utils.storage import normalize_storage_token

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
ASSET_VERSION = "20260513-library-equal-cards-1"

COPY_STATUSES = ["triagem", "catalogado", "guardado", "emprestado", "reservado"]
MEDIA_CONDITIONS = ["M", "NM", "VG+", "VG", "G", "P"]
PHOTO_TYPES = [
    ("front", "Capa"),
    ("back", "Contracapa"),
    ("label_a", "Selo A"),
    ("label_b", "Selo B"),
    ("runout_a", "Runout A"),
    ("runout_b", "Runout B"),
    ("insert", "Encarte"),
    ("spine", "Lombada"),
    ("defect", "Defeito"),
    ("other", "Outro"),
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_database()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.allow_all_origins else settings.cors_origins,
        allow_credentials=not settings.allow_all_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/covers", StaticFiles(directory=settings.COVERS_DIR), name="covers")

templates = Jinja2Templates(directory=BASE_DIR / "templates")


def static_asset(_: Request, path: str) -> str:
    normalized = path.lstrip("/")
    return f"/static/{normalized}?v={ASSET_VERSION}"


templates.env.globals["static_asset"] = static_asset

api_prefix = settings.API_V1_PREFIX
app.include_router(health_router, prefix=f"{api_prefix}", tags=["health"])
app.include_router(artists_router, prefix=f"{api_prefix}/artists", tags=["artists"])
app.include_router(albums_router, prefix=f"{api_prefix}/albums", tags=["albums"])
app.include_router(copies_router, prefix=f"{api_prefix}/copies", tags=["copies"])


def copy_page_options():
    return (
        selectinload(Copy.album).selectinload(Album.artist),
        selectinload(Copy.album).selectinload(Album.tracks),
        selectinload(Copy.storage_unit),
        selectinload(Copy.storage_slot).selectinload(StorageSlot.storage_unit),
        selectinload(Copy.photos),
        selectinload(Copy.analysis_suggestions),
        selectinload(Copy.location_history)
        .selectinload(CopyLocationHistory.storage_slot)
        .selectinload(StorageSlot.storage_unit),
    )


async def fetch_copy_page(session, copy_id: int) -> Copy | None:
    result = await session.execute(
        select(Copy)
        .filter(Copy.id == copy_id)
        .options(*copy_page_options())
    )
    return result.scalar_one_or_none()


async def fetch_storage_units(session):
    result = await session.execute(
        select(StorageUnit)
        .order_by(StorageUnit.code)
        .options(selectinload(StorageUnit.slots))
    )
    return result.scalars().all()


async def fetch_storage_overview(session):
    result = await session.execute(
        select(StorageUnit)
        .order_by(StorageUnit.code)
        .options(
            selectinload(StorageUnit.slots).selectinload(StorageSlot.copies)
        )
    )
    units = result.scalars().all()
    return build_storage_overview(units)


@app.get("/")
async def home(request: Request, q: str = None, status: str = None):
    retries = 3
    delay = 0.5
    last_exc: Exception | None = None
    search_query = q.strip() if q else None
    normalized_location_query = normalize_storage_token(search_query) if search_query else None

    for attempt in range(retries):
        try:
            async with AsyncSessionLocal() as session:
                query = (
                    select(Copy)
                    .join(Copy.album)
                    .join(Album.artist)
                    .outerjoin(Copy.storage_slot)
                    .outerjoin(Copy.storage_unit)
                    .options(*copy_page_options())
                )

                if search_query:
                    like_term = f"%{search_query}%"
                    search_filters = [
                        Album.title.ilike(like_term),
                        Artist.name.ilike(like_term),
                        Album.catalog_number.ilike(like_term),
                        Album.barcode.ilike(like_term),
                        Copy.copy_code.ilike(like_term),
                        Copy.location_code.ilike(like_term),
                        StorageSlot.slot_code.ilike(like_term),
                        StorageUnit.code.ilike(like_term),
                    ]
                    if normalized_location_query:
                        search_filters.append(Copy.location_code == normalized_location_query)
                    query = query.filter(or_(*search_filters))

                if status:
                    query = query.filter(Copy.status == status)

                query = query.order_by(Copy.location_code, Artist.name, Album.title)
                result = await session.execute(query)
                copies = result.scalars().all()

            return templates.TemplateResponse(
                request,
                "index.html",
                {
                    "copies": copies,
                    "search_query": search_query,
                    "status_filter": status or "",
                    "statuses": COPY_STATUSES,
                },
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise last_exc


@app.get("/biblioteca")
async def physical_library(request: Request):
    async with AsyncSessionLocal() as session:
        storage_units = await fetch_storage_units(session)
        storage_overview = await fetch_storage_overview(session)
    return templates.TemplateResponse(
        request,
        "library.html",
        {
            "storage_units": storage_units,
            "storage_overview": storage_overview,
        },
    )


@app.get("/albums/new")
async def new_album(request: Request):
    async with AsyncSessionLocal() as session:
        storage_units = await fetch_storage_units(session)
    return templates.TemplateResponse(
        request,
        "new.html",
        {
            "storage_units": storage_units,
            "statuses": COPY_STATUSES,
            "conditions": MEDIA_CONDITIONS,
        },
    )


@app.get("/copies/id/{copy_id}")
async def copy_details(
    request: Request,
    copy_id: int,
    session=Depends(get_db),
):
    copy = await fetch_copy_page(session, copy_id)
    if not copy:
        return templates.TemplateResponse(request, "404.html", {}, status_code=404)

    return templates.TemplateResponse(request, "details.html", {"copy": copy})


@app.get("/copies/id/{copy_id}/edit")
async def edit_copy(
    request: Request,
    copy_id: int,
    session=Depends(get_db),
):
    copy = await fetch_copy_page(session, copy_id)
    if not copy:
        return templates.TemplateResponse(request, "404.html", {}, status_code=404)

    storage_units = await fetch_storage_units(session)
    return templates.TemplateResponse(
        request,
        "edit.html",
        {
            "copy": copy,
            "storage_units": storage_units,
            "statuses": COPY_STATUSES,
            "conditions": MEDIA_CONDITIONS,
            "photo_types": PHOTO_TYPES,
        },
    )


@app.get("/albums/id/{album_id}")
async def legacy_album_details(album_id: int, session=Depends(get_db)):
    result = await session.execute(select(Copy).filter(Copy.album_id == album_id).order_by(Copy.id))
    copy = result.scalars().first()
    if not copy:
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url=f"/copies/id/{copy.id}", status_code=303)


@app.get("/albums/id/{album_id}/edit")
async def legacy_album_edit(album_id: int, session=Depends(get_db)):
    result = await session.execute(select(Copy).filter(Copy.album_id == album_id).order_by(Copy.id))
    copy = result.scalars().first()
    if not copy:
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url=f"/copies/id/{copy.id}/edit", status_code=303)
