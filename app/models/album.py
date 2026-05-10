from sqlalchemy import String, Integer, ForeignKey, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from db.base_class import Base
from .track import Track

class Album(Base):
    __tablename__ = "albums"
    __table_args__ = (
        UniqueConstraint("discogs_id", name="uq_albums_discogs_id"),
        Index("ix_albums_year_title", "year", "title"),
        Index("ix_albums_storage_lookup", "storage_unit", "storage_niche", "storage_position"),
        Index("ix_albums_storage_niche", "storage_niche"),
        Index("ix_albums_artist_title_year", "artist_id", "title", "year"),
        Index("ix_albums_location_code", "location_code"),
        Index("ix_albums_catalog_number", "catalog_number"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    year: Mapped[int | None] = mapped_column(Integer)
    genre: Mapped[str | None] = mapped_column(String(64))
    country: Mapped[str | None] = mapped_column(String(64))
    label_name: Mapped[str | None] = mapped_column(String(255))
    catalog_number: Mapped[str | None] = mapped_column(String(128))
    barcode: Mapped[str | None] = mapped_column(String(128))
    format: Mapped[str | None] = mapped_column(String(32))
    rpm: Mapped[int | None] = mapped_column(Integer)
    discs_count: Mapped[int | None] = mapped_column(Integer)
    style: Mapped[str | None] = mapped_column(String(128))
    storage_unit: Mapped[str | None] = mapped_column(String(120))
    storage_niche: Mapped[str | None] = mapped_column(String(64))
    storage_position: Mapped[str | None] = mapped_column(String(64))
    location_code: Mapped[str | None] = mapped_column(String(255))
    cover_path: Mapped[str | None] = mapped_column(String(255))  # Caminho relativo para a capa em covers/
    discogs_id: Mapped[int | None] = mapped_column(Integer)  # ID do Discogs para referência
    notes: Mapped[str | None] = mapped_column(Text)  # Notas adicionais sobre o LP
    
    artist_id: Mapped[int] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), index=True)
    artist = relationship("Artist", back_populates="albums")
    tracks: Mapped[List[Track]] = relationship("Track", back_populates="album", cascade="all, delete-orphan")
    copies = relationship("Copy", back_populates="album", cascade="all, delete-orphan")
