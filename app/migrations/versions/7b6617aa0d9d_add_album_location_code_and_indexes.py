"""add album location code and optimize indexes

Revision ID: 7b6617aa0d9d
Revises: 0f3ed6431052
Create Date: 2026-05-08 18:56:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "7b6617aa0d9d"
down_revision = "0f3ed6431052"
branch_labels = None
depends_on = None


albums_table = sa.table(
    "albums",
    sa.column("id", sa.Integer()),
    sa.column("storage_unit", sa.String(length=120)),
    sa.column("storage_niche", sa.String(length=64)),
    sa.column("storage_position", sa.String(length=64)),
    sa.column("location_code", sa.String(length=255)),
)


def _normalize_storage_token(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = "".join(char if char.isalnum() else "-" for char in value.strip().upper())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    cleaned = cleaned.strip("-")
    return cleaned or None


def _build_location_code(storage_unit: str | None, storage_niche: str | None, storage_position: str | None) -> str | None:
    parts = [
        _normalize_storage_token(storage_unit),
        _normalize_storage_token(storage_niche),
        _normalize_storage_token(storage_position),
    ]
    filtered_parts = [part for part in parts if part]
    if not filtered_parts:
        return None
    return "-".join(filtered_parts)


def _index_names(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_constraint_names(inspector, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name) if constraint.get("name")}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "albums" not in table_names:
        return

    album_columns = {column["name"] for column in inspector.get_columns("albums")}
    if "storage_unit" not in album_columns:
        op.add_column("albums", sa.Column("storage_unit", sa.String(length=120), nullable=True))
    if "storage_niche" not in album_columns:
        op.add_column("albums", sa.Column("storage_niche", sa.String(length=64), nullable=True))
    if "storage_position" not in album_columns:
        op.add_column("albums", sa.Column("storage_position", sa.String(length=64), nullable=True))
    if "location_code" not in album_columns:
        op.add_column("albums", sa.Column("location_code", sa.String(length=255), nullable=True))

    inspector = inspect(bind)
    album_indexes = _index_names(inspector, "albums")
    if "ix_albums_year_title" not in album_indexes:
        op.create_index("ix_albums_year_title", "albums", ["year", "title"], unique=False)
    if "ix_albums_storage_lookup" not in album_indexes:
        op.create_index("ix_albums_storage_lookup", "albums", ["storage_unit", "storage_niche", "storage_position"], unique=False)
    if "ix_albums_storage_niche" not in album_indexes:
        op.create_index("ix_albums_storage_niche", "albums", ["storage_niche"], unique=False)
    if "ix_albums_artist_title_year" not in album_indexes:
        op.create_index("ix_albums_artist_title_year", "albums", ["artist_id", "title", "year"], unique=False)
    if "ix_albums_location_code" not in album_indexes:
        op.create_index("ix_albums_location_code", "albums", ["location_code"], unique=False)

    album_unique_constraints = _unique_constraint_names(inspector, "albums")
    if "uq_albums_discogs_id" not in album_unique_constraints:
        op.create_unique_constraint("uq_albums_discogs_id", "albums", ["discogs_id"])
    if bind.dialect.name != "sqlite" and "discogs_id" in album_unique_constraints and "uq_albums_discogs_id" in album_unique_constraints:
        op.drop_constraint("discogs_id", "albums", type_="unique")

    rows = bind.execute(
        sa.select(
            albums_table.c.id,
            albums_table.c.storage_unit,
            albums_table.c.storage_niche,
            albums_table.c.storage_position,
        )
    ).mappings()
    for row in rows:
        location_code = _build_location_code(
            row["storage_unit"],
            row["storage_niche"],
            row["storage_position"],
        )
        bind.execute(
            sa.update(albums_table)
            .where(albums_table.c.id == row["id"])
            .values(location_code=location_code)
        )

    if "artists" in table_names:
        artist_indexes = _index_names(inspector, "artists")
        if "ix_artists_id" in artist_indexes:
            op.drop_index("ix_artists_id", table_name="artists")

    if "tracks" in table_names:
        track_indexes = _index_names(inspector, "tracks")
        if "ix_tracks_id" in track_indexes:
            op.drop_index("ix_tracks_id", table_name="tracks")

    inspector = inspect(bind)
    album_indexes = _index_names(inspector, "albums")
    if "ix_albums_id" in album_indexes:
        op.drop_index("ix_albums_id", table_name="albums")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "albums" in table_names:
        album_indexes = _index_names(inspector, "albums")
        if "ix_albums_location_code" in album_indexes:
            op.drop_index("ix_albums_location_code", table_name="albums")
        if "ix_albums_artist_title_year" in album_indexes:
            op.drop_index("ix_albums_artist_title_year", table_name="albums")
        if "ix_albums_storage_niche" in album_indexes:
            op.drop_index("ix_albums_storage_niche", table_name="albums")
        if "ix_albums_storage_lookup" in album_indexes:
            op.drop_index("ix_albums_storage_lookup", table_name="albums")
        if "ix_albums_year_title" in album_indexes:
            op.drop_index("ix_albums_year_title", table_name="albums")

        album_columns = {column["name"] for column in inspector.get_columns("albums")}
        if "location_code" in album_columns:
            op.drop_column("albums", "location_code")
        if "storage_position" in album_columns:
            op.drop_column("albums", "storage_position")
        if "storage_niche" in album_columns:
            op.drop_column("albums", "storage_niche")
        if "storage_unit" in album_columns:
            op.drop_column("albums", "storage_unit")

    if "artists" in table_names:
        artist_indexes = _index_names(inspector, "artists")
        if "ix_artists_id" not in artist_indexes:
            op.create_index("ix_artists_id", "artists", ["id"], unique=False)

    if "tracks" in table_names:
        track_indexes = _index_names(inspector, "tracks")
        if "ix_tracks_id" not in track_indexes:
            op.create_index("ix_tracks_id", "tracks", ["id"], unique=False)

    if "albums" in table_names:
        album_indexes = _index_names(inspector, "albums")
        if "ix_albums_id" not in album_indexes:
            op.create_index("ix_albums_id", "albums", ["id"], unique=False)
