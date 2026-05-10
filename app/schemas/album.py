from typing import List
from pydantic import BaseModel, ConfigDict, Field

class TrackBase(BaseModel):
    disc_number: int | None = None
    side: str | None = None
    position: str
    title: str
    duration: str

class Track(TrackBase):
    pass

class TrackCreate(TrackBase):
    pass

class TrackOut(TrackBase):
    id: int
    album_id: int

    model_config = ConfigDict(from_attributes=True)

class AlbumBase(BaseModel):
    title: str
    year: int | None = None
    genre: str | None = None
    country: str | None = None
    label_name: str | None = None
    catalog_number: str | None = None
    barcode: str | None = None
    format: str | None = None
    rpm: int | None = None
    discs_count: int | None = None
    style: str | None = None
    storage_unit: str | None = None
    storage_niche: str | None = None
    storage_position: str | None = None
    artist_id: int | None = None  # Opcional para permitir criar via nome do artista
    artist_name: str | None = None  # Nome do artista para criação manual
    discogs_id: int | None = None
    cover_path: str | None = None
    notes: str | None = None

class AlbumCreate(AlbumBase):
    tracks: List[TrackCreate] = Field(default_factory=list)

class AlbumOut(AlbumBase):
    id: int
    location_code: str | None = None
    tracks: List[TrackOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

# Schema para resultados da busca no Discogs
class AlbumSearch(BaseModel):
    title: str = ""  # Valor padrão vazio
    artist: str = ""  # Valor padrão vazio
    year: int | None = None
    genre: str | None = None
    country: str | None = None
    label_name: str | None = None
    catalog_number: str | None = None
    format: str | None = None
    style: str | None = None
    storage_unit: str | None = None
    storage_niche: str | None = None
    storage_position: str | None = None
    discogs_id: int = 0  # Valor padrão
    cover_url: str | None = None
    notes: str | None = None
    tracks: List[TrackBase] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

    @classmethod
    def create_safe(cls, **data):
        """Cria uma instância de AlbumSearch com validação segura"""
        safe_data = {
            "title": str(data.get("title", "")),
            "artist": str(data.get("artist", "")),
            "year": int(data["year"]) if data.get("year") else None,
            "genre": str(data.get("genre", "")),
            "country": str(data.get("country", "")) if data.get("country") else None,
            "label_name": str(data.get("label_name", "")) if data.get("label_name") else None,
            "catalog_number": str(data.get("catalog_number", "")) if data.get("catalog_number") else None,
            "format": str(data.get("format", "")) if data.get("format") else None,
            "style": str(data.get("style", "")) if data.get("style") else None,
            "storage_unit": str(data.get("storage_unit", "")) if data.get("storage_unit") else None,
            "storage_niche": str(data.get("storage_niche", "")) if data.get("storage_niche") else None,
            "storage_position": str(data.get("storage_position", "")) if data.get("storage_position") else None,
            "discogs_id": int(data.get("discogs_id", 0)),
            "cover_url": str(data.get("cover_url", "")) if data.get("cover_url") else None,
            "notes": str(data.get("notes", "")) if data.get("notes") else None,
            "tracks": data.get("tracks", [])
        }
        return cls(**safe_data)
