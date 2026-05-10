from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.deps import get_session
from core.config import get_settings
from models.album import Album
from models.artist import Artist
from models.copy import Copy, CopyLocationHistory, CopyPhoto
from models.storage import StorageSlot, StorageUnit
from models.track import Track
from schemas.album import AlbumSearch
from schemas.copy import (
    CatalogItemCreate,
    CatalogItemOut,
    CopyPhotoOut,
    StorageUnitOverviewOut,
    StorageUnitWithSlotsOut,
)
from services.discogs import DiscogsService
from utils.storage import build_copy_location_code, normalize_slot_position, slot_uses_positions

router = APIRouter()

PHOTO_TYPES = {
    "front",
    "back",
    "label_a",
    "label_b",
    "runout_a",
    "runout_b",
    "insert",
    "spine",
    "defect",
    "other",
}
POSITION_STEP = 10


def copy_load_options():
    return (
        selectinload(Copy.album).selectinload(Album.artist),
        selectinload(Copy.album).selectinload(Album.tracks),
        selectinload(Copy.storage_unit),
        selectinload(Copy.storage_slot).selectinload(StorageSlot.storage_unit),
        selectinload(Copy.photos),
        selectinload(Copy.location_history)
        .selectinload(CopyLocationHistory.storage_slot)
        .selectinload(StorageSlot.storage_unit),
    )


async def fetch_copy_or_404(db: AsyncSession, copy_id: int) -> Copy:
    result = await db.execute(
        select(Copy)
        .filter(Copy.id == copy_id)
        .options(*copy_load_options())
    )
    copy = result.scalar_one_or_none()
    if not copy:
        raise HTTPException(status_code=404, detail="Copy not found")
    return copy


async def resolve_artist(db: AsyncSession, artist_name: str) -> Artist:
    artist_query = await db.execute(select(Artist).filter(Artist.name == artist_name))
    artist = artist_query.scalar_one_or_none()
    if artist:
        return artist

    artist = Artist(name=artist_name)
    db.add(artist)
    await db.flush()
    return artist


async def resolve_storage_slot(db: AsyncSession, storage_slot_id: int | None) -> StorageSlot | None:
    if not storage_slot_id:
        return None

    result = await db.execute(
        select(StorageSlot)
        .filter(StorageSlot.id == storage_slot_id)
        .options(selectinload(StorageSlot.storage_unit))
    )
    slot = result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=400, detail="Storage slot not found")
    return slot


def apply_release_fields(album: Album, payload: CatalogItemCreate, artist_id: int) -> None:
    album.title = payload.title
    album.year = payload.year
    album.genre = payload.genre
    album.country = payload.country
    album.label_name = payload.label_name
    album.catalog_number = payload.catalog_number
    album.barcode = payload.barcode
    album.format = payload.format
    album.rpm = payload.rpm
    album.discs_count = payload.discs_count
    album.style = payload.style
    album.artist_id = artist_id
    album.discogs_id = payload.discogs_id
    album.cover_path = payload.cover_path
    album.notes = payload.notes


async def replace_tracks(db: AsyncSession, album_id: int, tracks: list) -> None:
    await db.execute(delete(Track).filter(Track.album_id == album_id))
    for track_data in tracks:
        if not track_data.position or not track_data.title:
            continue
        db.add(
            Track(
                album_id=album_id,
                disc_number=track_data.disc_number,
                side=track_data.side,
                position=track_data.position,
                title=track_data.title,
                duration=track_data.duration or "00:00",
            )
        )


def apply_copy_fields(copy: Copy, payload: CatalogItemCreate) -> None:
    copy.status = payload.status
    copy.media_condition = payload.media_condition
    copy.sleeve_condition = payload.sleeve_condition
    copy.has_insert = payload.has_insert
    copy.has_obi = payload.has_obi
    copy.purchase_date = payload.purchase_date
    copy.purchase_price = payload.purchase_price
    copy.purchase_from = payload.purchase_from
    copy.notes = payload.copy_notes


def sync_album_legacy_location(album: Album, copy: Copy, slot: StorageSlot | None) -> None:
    unit_code = slot.storage_unit.code if slot and slot.storage_unit else None
    slot_code = slot.slot_code if slot else None
    normalized_position = normalize_slot_position(copy.slot_position)
    album.storage_unit = unit_code
    album.storage_niche = slot_code
    album.storage_position = normalized_position
    album.location_code = copy.location_code


def set_copy_location(copy: Copy, slot: StorageSlot | None, slot_position: str | None) -> None:
    normalized_position = normalize_slot_position(slot_position)
    if slot and not slot_uses_positions(slot.purpose):
        normalized_position = None
    copy.storage_slot_id = slot.id if slot else None
    copy.storage_unit_id = slot.storage_unit_id if slot else None
    copy.slot_position = normalized_position
    copy.location_code = build_copy_location_code(
        slot.storage_unit.code if slot and slot.storage_unit else None,
        slot.slot_code if slot else None,
        normalized_position,
    )


def build_location_history(copy: Copy, note: str | None = None) -> CopyLocationHistory | None:
    if not copy.location_code and not copy.storage_slot_id:
        return None

    return CopyLocationHistory(
        copy_id=copy.id,
        storage_slot_id=copy.storage_slot_id,
        slot_position=copy.slot_position,
        location_code=copy.location_code,
        note=note,
    )


def compute_next_slot_position(used_positions: list[str], step: int = POSITION_STEP) -> str:
    numeric_positions = sorted(
        {
            int(position)
            for position in used_positions
            if position and position.isdigit()
        }
    )
    if not numeric_positions:
        return f"{step:03d}"

    candidate = step
    for value in numeric_positions:
        if value > candidate:
            break
        if value == candidate:
            candidate += step

    return f"{candidate:03d}"


def build_storage_overview(units: list[StorageUnit]) -> list[dict]:
    overview = []
    for unit in units:
        slot_items = []
        for slot in sorted(unit.slots, key=lambda item: ((item.row_code or ""), (item.col_code or ""), item.slot_code)):
            uses_positions = slot_uses_positions(slot.purpose)
            occupied_positions = sorted(
                [copy.slot_position for copy in slot.copies if copy.slot_position],
                key=lambda value: int(value) if value.isdigit() else value,
            ) if uses_positions else []
            occupied_count = len(slot.copies)
            capacity = slot.capacity_estimate
            available_count = max(capacity - occupied_count, 0) if capacity is not None else None
            fill_percentage = None
            if capacity:
                fill_percentage = round((occupied_count / capacity) * 100)

            slot_items.append(
                {
                    "id": slot.id,
                    "slot_code": slot.slot_code,
                    "row_code": slot.row_code,
                    "col_code": slot.col_code,
                    "purpose": slot.purpose,
                    "uses_positions": uses_positions,
                    "capacity_estimate": capacity,
                    "occupied_count": occupied_count,
                    "available_count": available_count,
                    "fill_percentage": fill_percentage,
                    "next_position": compute_next_slot_position(occupied_positions) if uses_positions else None,
                    "occupied_positions": occupied_positions,
                }
            )

        overview.append(
            {
                "id": unit.id,
                "code": unit.code,
                "name": unit.name,
                "room": unit.room,
                "notes": unit.notes,
                "slots": slot_items,
            }
        )
    return overview


@router.get("/", response_model=list[CatalogItemOut])
async def list_copies(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(Copy)
        .order_by(Copy.location_code, Copy.copy_code)
        .options(*copy_load_options())
    )
    return result.scalars().all()


@router.get("/count")
async def count_copies(db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(func.count(Copy.id)))
    return {"count": result.scalar_one() or 0}


@router.get("/meta/storage", response_model=list[StorageUnitWithSlotsOut])
async def list_storage_units(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(StorageUnit)
        .order_by(StorageUnit.code)
        .options(selectinload(StorageUnit.slots))
    )
    return result.scalars().all()


@router.get("/meta/storage/overview", response_model=list[StorageUnitOverviewOut])
async def get_storage_overview(db: AsyncSession = Depends(get_session)):
    result = await db.execute(
        select(StorageUnit)
        .order_by(StorageUnit.code)
        .options(
            selectinload(StorageUnit.slots).selectinload(StorageSlot.copies)
        )
    )
    units = result.scalars().all()
    return build_storage_overview(units)


@router.get("/meta/storage/{slot_id}/next-position")
async def get_next_slot_position(
    slot_id: int,
    exclude_copy_id: int | None = None,
    db: AsyncSession = Depends(get_session),
):
    slot = await resolve_storage_slot(db, slot_id)
    query = select(Copy.slot_position).filter(Copy.storage_slot_id == slot.id)
    if exclude_copy_id:
        query = query.filter(Copy.id != exclude_copy_id)

    result = await db.execute(query)
    used_positions = [position for position in result.scalars().all() if position]
    uses_positions = slot_uses_positions(slot.purpose)
    next_position = compute_next_slot_position(used_positions)
    return {
        "slot_id": slot.id,
        "slot_code": slot.slot_code,
        "storage_unit_code": slot.storage_unit.code if slot.storage_unit else None,
        "uses_positions": uses_positions,
        "next_position": next_position if uses_positions else None,
        "used_positions": sorted(used_positions) if uses_positions else [],
    }


@router.get("/meta/storage/{slot_id}/contents")
async def get_slot_contents(
    slot_id: int,
    db: AsyncSession = Depends(get_session),
):
    slot = await resolve_storage_slot(db, slot_id)
    result = await db.execute(
        select(Copy)
        .join(Copy.album)
        .join(Album.artist)
        .filter(Copy.storage_slot_id == slot.id)
        .options(
            selectinload(Copy.album).selectinload(Album.artist),
        )
        .order_by(Copy.slot_position, Artist.name, Album.title, Copy.copy_code)
    )
    copies = result.scalars().all()
    uses_positions = slot_uses_positions(slot.purpose)
    used_positions = [copy.slot_position for copy in copies if copy.slot_position] if uses_positions else []

    return {
        "slot_id": slot.id,
        "slot_code": slot.slot_code,
        "storage_unit_code": slot.storage_unit.code if slot.storage_unit else None,
        "purpose": slot.purpose,
        "uses_positions": uses_positions,
        "capacity_estimate": slot.capacity_estimate,
        "occupied_count": len(copies),
        "next_position": compute_next_slot_position(used_positions) if uses_positions else None,
        "copies": [
            {
                "id": copy.id,
                "copy_code": copy.copy_code,
                "slot_position": copy.slot_position,
                "location_code": copy.location_code,
                "status": copy.status,
                "title": copy.album.title,
                "artist_name": copy.album.artist.name if copy.album and copy.album.artist else None,
                "year": copy.album.year if copy.album else None,
            }
            for copy in copies
        ],
    }


@router.post("/meta/storage/{slot_id}/normalize")
async def normalize_slot_positions(
    slot_id: int,
    db: AsyncSession = Depends(get_session),
):
    slot = await resolve_storage_slot(db, slot_id)
    if not slot_uses_positions(slot.purpose):
        result = await db.execute(select(func.count(Copy.id)).filter(Copy.storage_slot_id == slot.id))
        return {
            "slot_id": slot.id,
            "slot_code": slot.slot_code,
            "storage_unit_code": slot.storage_unit.code if slot.storage_unit else None,
            "normalized_count": 0,
            "copies_in_slot": result.scalar_one() or 0,
            "updated": [],
            "message": "Este nicho nao usa posicoes internas.",
        }
    result = await db.execute(
        select(Copy)
        .join(Copy.album)
        .join(Album.artist)
        .filter(Copy.storage_slot_id == slot.id)
        .options(selectinload(Copy.album))
        .order_by(Artist.name, Album.title, Album.year, Copy.copy_code)
    )
    copies = result.scalars().all()

    updated = []
    for index, copy in enumerate(copies, start=1):
        new_position = f"{index * POSITION_STEP:03d}"
        new_location_code = build_copy_location_code(
            slot.storage_unit.code if slot.storage_unit else None,
            slot.slot_code,
            new_position,
        )
        if copy.slot_position == new_position and copy.location_code == new_location_code:
            continue

        copy.slot_position = new_position
        copy.location_code = new_location_code
        sync_album_legacy_location(copy.album, copy, slot)
        history_item = build_location_history(copy, note="Normalizacao de posicoes")
        if history_item:
            db.add(history_item)
        updated.append(
            {
                "copy_id": copy.id,
                "copy_code": copy.copy_code,
                "new_position": new_position,
                "new_location_code": new_location_code,
            }
        )

    await db.commit()
    return {
        "slot_id": slot.id,
        "slot_code": slot.slot_code,
        "storage_unit_code": slot.storage_unit.code if slot.storage_unit else None,
        "normalized_count": len(updated),
        "copies_in_slot": len(copies),
        "updated": updated,
    }


@router.get("/id/{copy_id}", response_model=CatalogItemOut)
async def get_copy(copy_id: int, db: AsyncSession = Depends(get_session)):
    return await fetch_copy_or_404(db, copy_id)


@router.post("/", response_model=CatalogItemOut, status_code=201)
async def create_copy(payload: CatalogItemCreate, db: AsyncSession = Depends(get_session)):
    artist = await resolve_artist(db, payload.artist_name.strip())
    slot = await resolve_storage_slot(db, payload.storage_slot_id)
    cover_path = payload.cover_path
    if not cover_path and payload.cover_url:
        cover_path = await DiscogsService().download_cover(
            AlbumSearch.create_safe(
                title=payload.title,
                artist=payload.artist_name,
                discogs_id=payload.discogs_id or 0,
                cover_url=payload.cover_url,
            )
        )

    album = Album()
    payload.cover_path = cover_path
    apply_release_fields(album, payload, artist.id)
    db.add(album)
    await db.flush()
    await replace_tracks(db, album.id, payload.tracks)

    copy = Copy(album_id=album.id)
    apply_copy_fields(copy, payload)
    set_copy_location(copy, slot, payload.slot_position)
    db.add(copy)
    await db.flush()
    copy.copy_code = f"LP-{copy.id:06d}"
    history_item = build_location_history(copy, note="Cadastro inicial")
    if history_item:
        db.add(history_item)
    sync_album_legacy_location(album, copy, slot)

    await db.commit()
    return await fetch_copy_or_404(db, copy.id)


@router.put("/id/{copy_id}", response_model=CatalogItemOut)
async def update_copy(copy_id: int, payload: CatalogItemCreate, db: AsyncSession = Depends(get_session)):
    copy = await fetch_copy_or_404(db, copy_id)
    artist = await resolve_artist(db, payload.artist_name.strip())
    slot = await resolve_storage_slot(db, payload.storage_slot_id)
    cover_path = payload.cover_path or copy.album.cover_path
    if not cover_path and payload.cover_url:
        cover_path = await DiscogsService().download_cover(
            AlbumSearch.create_safe(
                title=payload.title,
                artist=payload.artist_name,
                discogs_id=payload.discogs_id or 0,
                cover_url=payload.cover_url,
            )
        )
    payload.cover_path = cover_path

    previous_location = copy.location_code
    previous_slot_id = copy.storage_slot_id
    previous_slot_position = copy.slot_position

    apply_release_fields(copy.album, payload, artist.id)
    await replace_tracks(db, copy.album.id, payload.tracks)
    apply_copy_fields(copy, payload)
    set_copy_location(copy, slot, payload.slot_position)
    sync_album_legacy_location(copy.album, copy, slot)

    if (
        previous_location != copy.location_code
        or previous_slot_id != copy.storage_slot_id
        or previous_slot_position != copy.slot_position
    ):
        history_item = build_location_history(copy, note="Atualizacao de localizacao")
        if history_item:
            db.add(history_item)

    await db.commit()
    return await fetch_copy_or_404(db, copy.id)


@router.delete("/id/{copy_id}", status_code=204)
async def delete_copy(copy_id: int, db: AsyncSession = Depends(get_session)):
    copy = await fetch_copy_or_404(db, copy_id)
    await db.delete(copy)
    await db.commit()
    return None


@router.post("/id/{copy_id}/photos", response_model=list[CopyPhotoOut], status_code=201)
async def upload_copy_photos(
    copy_id: int,
    photo_type: str = Form(...),
    is_primary: bool = Form(default=False),
    photos: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_session),
):
    if photo_type not in PHOTO_TYPES:
        raise HTTPException(status_code=400, detail="Invalid photo type")

    copy = await fetch_copy_or_404(db, copy_id)
    settings = get_settings()
    base_dir = Path(settings.COVERS_DIR) / "copies" / (copy.copy_code or f"copy-{copy.id}")
    base_dir.mkdir(parents=True, exist_ok=True)

    if is_primary:
        for existing in copy.photos:
            existing.is_primary = False

    created_photos: list[CopyPhoto] = []
    for upload in photos:
        suffix = Path(upload.filename or "upload.jpg").suffix or ".jpg"
        filename = f"{photo_type}-{uuid4().hex}{suffix.lower()}"
        file_path = base_dir / filename
        relative_path = str(Path("covers") / "copies" / (copy.copy_code or f"copy-{copy.id}") / filename)

        async with aiofiles.open(file_path, "wb") as output:
            while chunk := await upload.read(1024 * 1024):
                await output.write(chunk)
        await upload.close()

        photo = CopyPhoto(
            copy_id=copy.id,
            photo_type=photo_type,
            file_path=relative_path,
            is_primary=is_primary and len(created_photos) == 0,
        )
        db.add(photo)
        created_photos.append(photo)

    await db.commit()
    return created_photos


@router.delete("/id/{copy_id}/photos/{photo_id}", status_code=204)
async def delete_copy_photo(copy_id: int, photo_id: int, db: AsyncSession = Depends(get_session)):
    copy = await fetch_copy_or_404(db, copy_id)
    photo = next((item for item in copy.photos if item.id == photo_id), None)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    file_path = Path(photo.file_path)
    settings = get_settings()
    absolute_path = Path(settings.COVERS_DIR).parent / file_path if not str(file_path).startswith("/") else file_path
    await db.delete(photo)
    await db.commit()
    if absolute_path.exists():
        absolute_path.unlink()
    return None


@router.get("/search", response_model=list[CatalogItemOut])
async def search_copies(q: str, db: AsyncSession = Depends(get_session)):
    like_term = f"%{q.strip()}%"
    result = await db.execute(
        select(Copy)
        .join(Copy.album)
        .join(Album.artist)
        .outerjoin(Copy.storage_slot)
        .outerjoin(Copy.storage_unit)
        .filter(
            or_(
                Album.title.ilike(like_term),
                Artist.name.ilike(like_term),
                Album.catalog_number.ilike(like_term),
                Album.barcode.ilike(like_term),
                Copy.copy_code.ilike(like_term),
                Copy.location_code.ilike(like_term),
                StorageSlot.slot_code.ilike(like_term),
                StorageUnit.code.ilike(like_term),
            )
        )
        .options(*copy_load_options())
        .order_by(Copy.location_code, Copy.copy_code)
    )
    return result.scalars().all()
