from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from schemas.album import AlbumBase, TrackCreate, TrackOut
from schemas.artist import ArtistOut


class StorageUnitOut(BaseModel):
    id: int
    code: str
    name: str
    room: str | None = None
    notes: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StorageUnitWithSlotsOut(StorageUnitOut):
    slots: list["StorageSlotOut"] = Field(default_factory=list)


class StorageSlotOut(BaseModel):
    id: int
    storage_unit_id: int
    row_code: str | None = None
    col_code: str | None = None
    slot_code: str
    purpose: str | None = None
    capacity_estimate: int | None = None
    notes: str | None = None
    storage_unit: StorageUnitOut

    model_config = ConfigDict(from_attributes=True)


class StorageSlotOverviewOut(BaseModel):
    id: int
    slot_code: str
    row_code: str | None = None
    col_code: str | None = None
    purpose: str | None = None
    uses_positions: bool = True
    capacity_estimate: int | None = None
    occupied_count: int
    available_count: int | None = None
    fill_percentage: int | None = None
    next_position: str | None = None
    occupied_positions: list[str] = Field(default_factory=list)


class StorageUnitOverviewOut(BaseModel):
    id: int
    code: str
    name: str
    room: str | None = None
    notes: str | None = None
    slots: list[StorageSlotOverviewOut] = Field(default_factory=list)


class CopyPhotoOut(BaseModel):
    id: int
    photo_type: str
    file_path: str
    is_primary: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CopyLocationHistoryOut(BaseModel):
    id: int
    slot_position: str | None = None
    location_code: str | None = None
    note: str | None = None
    moved_at: datetime
    storage_slot: StorageSlotOut | None = None

    model_config = ConfigDict(from_attributes=True)


class ReleaseOut(AlbumBase):
    id: int
    artist: ArtistOut
    tracks: list[TrackOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CatalogItemBase(AlbumBase):
    cover_url: str | None = None
    status: str = "triagem"
    media_condition: str | None = None
    sleeve_condition: str | None = None
    has_insert: bool = False
    has_obi: bool = False
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    purchase_from: str | None = None
    copy_notes: str | None = None
    storage_slot_id: int | None = None
    slot_position: str | None = None


class CatalogItemCreate(CatalogItemBase):
    artist_name: str
    tracks: list[TrackCreate] = Field(default_factory=list)


class CatalogItemOut(BaseModel):
    id: int
    copy_code: str | None = None
    status: str
    media_condition: str | None = None
    sleeve_condition: str | None = None
    has_insert: bool
    has_obi: bool
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    purchase_from: str | None = None
    notes: str | None = None
    slot_position: str | None = None
    location_code: str | None = None
    created_at: datetime
    updated_at: datetime
    album: ReleaseOut
    storage_slot: StorageSlotOut | None = None
    storage_unit: StorageUnitOut | None = None
    photos: list[CopyPhotoOut] = Field(default_factory=list)
    location_history: list[CopyLocationHistoryOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


StorageUnitWithSlotsOut.model_rebuild()
