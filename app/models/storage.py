from sqlalchemy import String, Integer, ForeignKey, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base_class import Base


class StorageUnit(Base):
    __tablename__ = "storage_units"
    __table_args__ = (
        UniqueConstraint("code", name="uq_storage_units_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(16), index=True)
    name: Mapped[str] = mapped_column(String(255))
    room: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)

    slots = relationship("StorageSlot", back_populates="storage_unit", cascade="all, delete-orphan")
    copies = relationship("Copy", back_populates="storage_unit")


class StorageSlot(Base):
    __tablename__ = "storage_slots"
    __table_args__ = (
        UniqueConstraint("storage_unit_id", "slot_code", name="uq_storage_slots_unit_slot"),
        Index("ix_storage_slots_slot_code", "slot_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id", ondelete="CASCADE"), index=True)
    row_code: Mapped[str | None] = mapped_column(String(8))
    col_code: Mapped[str | None] = mapped_column(String(8))
    slot_code: Mapped[str] = mapped_column(String(16))
    purpose: Mapped[str | None] = mapped_column(String(128))
    capacity_estimate: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    storage_unit = relationship("StorageUnit", back_populates="slots")
    copies = relationship("Copy", back_populates="storage_slot")
    location_history = relationship("CopyLocationHistory", back_populates="storage_slot")
