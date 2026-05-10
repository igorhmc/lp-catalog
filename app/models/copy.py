from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import String, Integer, ForeignKey, Text, Date, DateTime, Boolean, Numeric, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base_class import Base


class Copy(Base):
    __tablename__ = "copies"
    __table_args__ = (
        UniqueConstraint("copy_code", name="uq_copies_copy_code"),
        Index("ix_copies_status_location", "status", "location_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("albums.id", ondelete="CASCADE"), index=True)
    copy_code: Mapped[str | None] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="triagem")
    media_condition: Mapped[str | None] = mapped_column(String(32))
    sleeve_condition: Mapped[str | None] = mapped_column(String(32))
    has_insert: Mapped[bool] = mapped_column(Boolean, default=False)
    has_obi: Mapped[bool] = mapped_column(Boolean, default=False)
    purchase_date: Mapped[date | None] = mapped_column(Date)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    purchase_from: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    storage_unit_id: Mapped[int | None] = mapped_column(ForeignKey("storage_units.id", ondelete="SET NULL"), index=True)
    storage_slot_id: Mapped[int | None] = mapped_column(ForeignKey("storage_slots.id", ondelete="SET NULL"), index=True)
    slot_position: Mapped[str | None] = mapped_column(String(16))
    location_code: Mapped[str | None] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    album = relationship("Album", back_populates="copies")
    storage_unit = relationship("StorageUnit", back_populates="copies")
    storage_slot = relationship("StorageSlot", back_populates="copies")
    photos = relationship("CopyPhoto", back_populates="copy", cascade="all, delete-orphan")
    location_history = relationship("CopyLocationHistory", back_populates="copy", cascade="all, delete-orphan")


class CopyPhoto(Base):
    __tablename__ = "copy_photos"
    __table_args__ = (
        Index("ix_copy_photos_copy_type", "copy_id", "photo_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    copy_id: Mapped[int] = mapped_column(ForeignKey("copies.id", ondelete="CASCADE"), index=True)
    photo_type: Mapped[str] = mapped_column(String(32))
    file_path: Mapped[str] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    copy = relationship("Copy", back_populates="photos")


class CopyLocationHistory(Base):
    __tablename__ = "copy_location_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    copy_id: Mapped[int] = mapped_column(ForeignKey("copies.id", ondelete="CASCADE"), index=True)
    storage_slot_id: Mapped[int | None] = mapped_column(ForeignKey("storage_slots.id", ondelete="SET NULL"), index=True)
    slot_position: Mapped[str | None] = mapped_column(String(16))
    location_code: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(255))
    moved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    copy = relationship("Copy", back_populates="location_history")
    storage_slot = relationship("StorageSlot", back_populates="location_history")
