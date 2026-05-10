"""add copy catalog model

Revision ID: a1c4e9b7f3d2
Revises: 7b6617aa0d9d
Create Date: 2026-05-08 20:05:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "a1c4e9b7f3d2"
down_revision = "7b6617aa0d9d"
branch_labels = None
depends_on = None


albums_table = sa.table(
    "albums",
    sa.column("id", sa.Integer()),
    sa.column("location_code", sa.String(length=255)),
    sa.column("storage_unit", sa.String(length=120)),
    sa.column("storage_niche", sa.String(length=64)),
)

copies_table = sa.table(
    "copies",
    sa.column("id", sa.Integer()),
    sa.column("album_id", sa.Integer()),
    sa.column("copy_code", sa.String(length=32)),
    sa.column("status", sa.String(length=32)),
    sa.column("notes", sa.Text()),
    sa.column("storage_unit_id", sa.Integer()),
    sa.column("storage_slot_id", sa.Integer()),
    sa.column("slot_position", sa.String(length=16)),
    sa.column("location_code", sa.String(length=64)),
)

storage_units_table = sa.table(
    "storage_units",
    sa.column("id", sa.Integer()),
    sa.column("code", sa.String(length=16)),
    sa.column("name", sa.String(length=255)),
    sa.column("room", sa.String(length=128)),
    sa.column("notes", sa.Text()),
)

storage_slots_table = sa.table(
    "storage_slots",
    sa.column("id", sa.Integer()),
    sa.column("storage_unit_id", sa.Integer()),
    sa.column("row_code", sa.String(length=8)),
    sa.column("col_code", sa.String(length=8)),
    sa.column("slot_code", sa.String(length=16)),
    sa.column("purpose", sa.String(length=32)),
    sa.column("capacity_estimate", sa.Integer()),
    sa.column("notes", sa.Text()),
)


def _table_names(inspector) -> set[str]:
    return set(inspector.get_table_names())


def _column_names(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _unique_constraint_names(inspector, table_name: str) -> set[str]:
    return {constraint["name"] for constraint in inspector.get_unique_constraints(table_name) if constraint.get("name")}


def _seed_storage_layout(bind) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
    unit_defs = [
        {"code": "K1", "name": "Kallax principal", "room": "Sala", "notes": "Arquivo principal da colecao"},
        {"code": "K2", "name": "Kallax escrivaninha", "room": "Sala", "notes": "Triagem, apoio e pendencias"},
    ]
    slot_defs = [
        ("K1", "A", "1", "A1", "Forró 1", 60, "Bloco principal de Forró"),
        ("K1", "A", "2", "A2", "Forró 2", 60, "Bloco principal de Forró"),
        ("K1", "A", "3", "A3", "MPB / Brasil não-forró", 60, "Musica brasileira fora do bloco de Forró"),
        ("K1", "A", "4", "A4", "Internacional", 60, "Catalogo internacional"),
        ("K1", "B", "1", "B1", "Forró 3", 60, "Bloco principal de Forró"),
        ("K1", "B", "2", "B2", "Forró 4", 60, "Bloco principal de Forró"),
        ("K1", "B", "3", "B3", "Triagem", 50, "Triagem e reorganizacao"),
        ("K1", "B", "4", "B4", "Crescimento / extras / compilações", 50, "Folga para crescimento, extras e coletaneas"),
        ("K2", "A", "1", "A1", "triagem", 40, "Entrada e triagem"),
        ("K2", "A", "2", "A2", "support", 25, "Acessorios e material de apoio"),
        ("K2", "B", "1", "B1", "new-arrivals", 35, "Discos recem-chegados"),
        ("K2", "B", "2", "B2", "pending", 35, "Pendencias e itens sem endereco final"),
    ]

    unit_ids: dict[str, int] = {}
    for unit in unit_defs:
        existing = bind.execute(
            sa.select(storage_units_table.c.id).where(storage_units_table.c.code == unit["code"])
        ).scalar_one_or_none()
        if existing is None:
            bind.execute(sa.insert(storage_units_table).values(**unit))
            existing = bind.execute(
                sa.select(storage_units_table.c.id).where(storage_units_table.c.code == unit["code"])
            ).scalar_one()
            unit_ids[unit["code"]] = existing
        else:
            unit_ids[unit["code"]] = existing

    slot_ids: dict[tuple[str, str], int] = {}
    for unit_code, row_code, col_code, slot_code, purpose, capacity, notes in slot_defs:
        existing = bind.execute(
            sa.select(storage_slots_table.c.id).where(
                sa.and_(
                    storage_slots_table.c.storage_unit_id == unit_ids[unit_code],
                    storage_slots_table.c.slot_code == slot_code,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            bind.execute(
                sa.insert(storage_slots_table).values(
                    storage_unit_id=unit_ids[unit_code],
                    row_code=row_code,
                    col_code=col_code,
                    slot_code=slot_code,
                    purpose=purpose,
                    capacity_estimate=capacity,
                    notes=notes,
                )
            )
            existing = bind.execute(
                sa.select(storage_slots_table.c.id).where(
                    sa.and_(
                        storage_slots_table.c.storage_unit_id == unit_ids[unit_code],
                        storage_slots_table.c.slot_code == slot_code,
                    )
                )
            ).scalar_one()
            slot_ids[(unit_code, slot_code)] = existing
        else:
            slot_ids[(unit_code, slot_code)] = existing

    return unit_ids, slot_ids


def _copy_code(copy_id: int) -> str:
    return f"LP-{copy_id:06d}"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = _table_names(inspector)

    if "albums" in table_names:
        album_columns = _column_names(inspector, "albums")
        new_columns = [
            ("country", sa.String(length=64)),
            ("label_name", sa.String(length=255)),
            ("catalog_number", sa.String(length=128)),
            ("barcode", sa.String(length=128)),
            ("format", sa.String(length=32)),
            ("rpm", sa.Integer()),
            ("discs_count", sa.Integer()),
            ("style", sa.String(length=128)),
        ]
        for name, column_type in new_columns:
            if name not in album_columns:
                op.add_column("albums", sa.Column(name, column_type, nullable=True))

        album_indexes = _index_names(inspector, "albums")
        if "ix_albums_catalog_number" not in album_indexes:
            op.create_index("ix_albums_catalog_number", "albums", ["catalog_number"], unique=False)

    if "tracks" in table_names:
        track_columns = _column_names(inspector, "tracks")
        if "disc_number" not in track_columns:
            op.add_column("tracks", sa.Column("disc_number", sa.Integer(), nullable=True))
        if "side" not in track_columns:
            op.add_column("tracks", sa.Column("side", sa.String(length=8), nullable=True))

    if "storage_units" not in table_names:
        op.create_table(
            "storage_units",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("code", sa.String(length=16), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("room", sa.String(length=128), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.UniqueConstraint("code", name="uq_storage_units_code"),
        )
        op.create_index("ix_storage_units_code", "storage_units", ["code"], unique=False)

    inspector = inspect(bind)
    table_names = _table_names(inspector)
    if "storage_slots" not in table_names:
        op.create_table(
            "storage_slots",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("storage_unit_id", sa.Integer(), sa.ForeignKey("storage_units.id", ondelete="CASCADE"), nullable=False),
            sa.Column("row_code", sa.String(length=8), nullable=True),
            sa.Column("col_code", sa.String(length=8), nullable=True),
            sa.Column("slot_code", sa.String(length=16), nullable=False),
            sa.Column("purpose", sa.String(length=128), nullable=True),
            sa.Column("capacity_estimate", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.UniqueConstraint("storage_unit_id", "slot_code", name="uq_storage_slots_unit_slot"),
        )
        op.create_index("ix_storage_slots_storage_unit_id", "storage_slots", ["storage_unit_id"], unique=False)
        op.create_index("ix_storage_slots_slot_code", "storage_slots", ["slot_code"], unique=False)

    inspector = inspect(bind)
    table_names = _table_names(inspector)
    if "copies" not in table_names:
        op.create_table(
            "copies",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("album_id", sa.Integer(), sa.ForeignKey("albums.id", ondelete="CASCADE"), nullable=False),
            sa.Column("copy_code", sa.String(length=32), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="triagem"),
            sa.Column("media_condition", sa.String(length=32), nullable=True),
            sa.Column("sleeve_condition", sa.String(length=32), nullable=True),
            sa.Column("has_insert", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("has_obi", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("purchase_date", sa.Date(), nullable=True),
            sa.Column("purchase_price", sa.Numeric(10, 2), nullable=True),
            sa.Column("purchase_from", sa.String(length=255), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("storage_unit_id", sa.Integer(), sa.ForeignKey("storage_units.id", ondelete="SET NULL"), nullable=True),
            sa.Column("storage_slot_id", sa.Integer(), sa.ForeignKey("storage_slots.id", ondelete="SET NULL"), nullable=True),
            sa.Column("slot_position", sa.String(length=16), nullable=True),
            sa.Column("location_code", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("copy_code", name="uq_copies_copy_code"),
        )
        op.create_index("ix_copies_album_id", "copies", ["album_id"], unique=False)
        op.create_index("ix_copies_copy_code", "copies", ["copy_code"], unique=False)
        op.create_index("ix_copies_status", "copies", ["status"], unique=False)
        op.create_index("ix_copies_storage_unit_id", "copies", ["storage_unit_id"], unique=False)
        op.create_index("ix_copies_storage_slot_id", "copies", ["storage_slot_id"], unique=False)
        op.create_index("ix_copies_location_code", "copies", ["location_code"], unique=False)
        op.create_index("ix_copies_status_location", "copies", ["status", "location_code"], unique=False)

    inspector = inspect(bind)
    table_names = _table_names(inspector)
    if "copy_photos" not in table_names:
        op.create_table(
            "copy_photos",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("copy_id", sa.Integer(), sa.ForeignKey("copies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("photo_type", sa.String(length=32), nullable=False),
            sa.Column("file_path", sa.String(length=255), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_copy_photos_copy_id", "copy_photos", ["copy_id"], unique=False)
        op.create_index("ix_copy_photos_copy_type", "copy_photos", ["copy_id", "photo_type"], unique=False)

    inspector = inspect(bind)
    table_names = _table_names(inspector)
    if "copy_location_history" not in table_names:
        op.create_table(
            "copy_location_history",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("copy_id", sa.Integer(), sa.ForeignKey("copies.id", ondelete="CASCADE"), nullable=False),
            sa.Column("storage_slot_id", sa.Integer(), sa.ForeignKey("storage_slots.id", ondelete="SET NULL"), nullable=True),
            sa.Column("slot_position", sa.String(length=16), nullable=True),
            sa.Column("location_code", sa.String(length=64), nullable=True),
            sa.Column("note", sa.String(length=255), nullable=True),
            sa.Column("moved_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_copy_location_history_copy_id", "copy_location_history", ["copy_id"], unique=False)
        op.create_index("ix_copy_location_history_storage_slot_id", "copy_location_history", ["storage_slot_id"], unique=False)

    unit_ids, slot_ids = _seed_storage_layout(bind)

    inspector = inspect(bind)
    if "albums" in table_names:
        existing_copy_album_ids = (
            {row[0] for row in bind.execute(sa.select(copies_table.c.album_id))}
            if "copies" in _table_names(inspector)
            else set()
        )

        albums = bind.execute(
            sa.select(
                albums_table.c.id,
                albums_table.c.location_code,
                albums_table.c.storage_unit,
                albums_table.c.storage_niche,
            )
        ).mappings()
        for album in albums:
            if album["id"] in existing_copy_album_ids:
                continue

            slot_id = None
            unit_id = None
            unit_code = (album["storage_unit"] or "").strip().upper() if album["storage_unit"] else None
            niche_code = (album["storage_niche"] or "").strip().upper() if album["storage_niche"] else None
            if unit_code in unit_ids:
                unit_id = unit_ids[unit_code]
                slot_id = slot_ids.get((unit_code, niche_code or ""))

            bind.execute(
                sa.insert(copies_table).values(
                    album_id=album["id"],
                    status="guardado",
                    notes="Copia migrada do modelo anterior",
                    storage_unit_id=unit_id,
                    storage_slot_id=slot_id,
                    location_code=album["location_code"],
                )
            )
            copy_id = bind.execute(
                sa.select(sa.func.max(copies_table.c.id)).where(copies_table.c.album_id == album["id"])
            ).scalar_one()
            bind.execute(
                sa.update(copies_table)
                .where(copies_table.c.id == copy_id)
                .values(copy_code=_copy_code(copy_id))
            )
            bind.execute(
                sa.insert(sa.table(
                    "copy_location_history",
                    sa.column("copy_id", sa.Integer()),
                    sa.column("storage_slot_id", sa.Integer()),
                    sa.column("location_code", sa.String(length=64)),
                    sa.column("note", sa.String(length=255)),
                )).values(
                    copy_id=copy_id,
                    storage_slot_id=slot_id,
                    location_code=album["location_code"],
                    note="Migracao inicial",
                )
            )

        copies_without_code = bind.execute(
            sa.select(copies_table.c.id).where(copies_table.c.copy_code.is_(None))
        )
        for row in copies_without_code:
            bind.execute(
                sa.update(copies_table)
                .where(copies_table.c.id == row[0])
                .values(copy_code=_copy_code(row[0]))
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = _table_names(inspector)

    if "copy_location_history" in table_names:
        history_indexes = _index_names(inspector, "copy_location_history")
        if "ix_copy_location_history_storage_slot_id" in history_indexes:
            op.drop_index("ix_copy_location_history_storage_slot_id", table_name="copy_location_history")
        if "ix_copy_location_history_copy_id" in history_indexes:
            op.drop_index("ix_copy_location_history_copy_id", table_name="copy_location_history")
        op.drop_table("copy_location_history")

    inspector = inspect(bind)
    table_names = _table_names(inspector)
    if "copy_photos" in table_names:
        photo_indexes = _index_names(inspector, "copy_photos")
        if "ix_copy_photos_copy_type" in photo_indexes:
            op.drop_index("ix_copy_photos_copy_type", table_name="copy_photos")
        if "ix_copy_photos_copy_id" in photo_indexes:
            op.drop_index("ix_copy_photos_copy_id", table_name="copy_photos")
        op.drop_table("copy_photos")

    inspector = inspect(bind)
    table_names = _table_names(inspector)
    if "copies" in table_names:
        copy_indexes = _index_names(inspector, "copies")
        for index_name in [
            "ix_copies_status_location",
            "ix_copies_location_code",
            "ix_copies_storage_slot_id",
            "ix_copies_storage_unit_id",
            "ix_copies_status",
            "ix_copies_copy_code",
            "ix_copies_album_id",
        ]:
            if index_name in copy_indexes:
                op.drop_index(index_name, table_name="copies")
        op.drop_table("copies")

    inspector = inspect(bind)
    table_names = _table_names(inspector)
    if "storage_slots" in table_names:
        slot_indexes = _index_names(inspector, "storage_slots")
        if "ix_storage_slots_slot_code" in slot_indexes:
            op.drop_index("ix_storage_slots_slot_code", table_name="storage_slots")
        if "ix_storage_slots_storage_unit_id" in slot_indexes:
            op.drop_index("ix_storage_slots_storage_unit_id", table_name="storage_slots")
        op.drop_table("storage_slots")

    inspector = inspect(bind)
    table_names = _table_names(inspector)
    if "storage_units" in table_names:
        unit_indexes = _index_names(inspector, "storage_units")
        if "ix_storage_units_code" in unit_indexes:
            op.drop_index("ix_storage_units_code", table_name="storage_units")
        op.drop_table("storage_units")

    if "tracks" in table_names:
        track_columns = _column_names(inspector, "tracks")
        if "side" in track_columns:
            op.drop_column("tracks", "side")
        if "disc_number" in track_columns:
            op.drop_column("tracks", "disc_number")

    if "albums" in table_names:
        album_indexes = _index_names(inspector, "albums")
        if "ix_albums_catalog_number" in album_indexes:
            op.drop_index("ix_albums_catalog_number", table_name="albums")
        album_columns = _column_names(inspector, "albums")
        for column_name in ["style", "discs_count", "rpm", "format", "barcode", "catalog_number", "label_name", "country"]:
            if column_name in album_columns:
                op.drop_column("albums", column_name)
