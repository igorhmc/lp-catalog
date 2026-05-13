"""normalize k2 slot positions

Revision ID: b6a1d2e9f405
Revises: 9d3a7c4e2b18
Create Date: 2026-05-11 00:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b6a1d2e9f405"
down_revision = "9d3a7c4e2b18"
branch_labels = None
depends_on = None


storage_units = sa.table(
    "storage_units",
    sa.column("id", sa.Integer()),
    sa.column("code", sa.String(length=16)),
)

storage_slots = sa.table(
    "storage_slots",
    sa.column("id", sa.Integer()),
    sa.column("storage_unit_id", sa.Integer()),
    sa.column("slot_code", sa.String(length=16)),
)

copies = sa.table(
    "copies",
    sa.column("album_id", sa.Integer()),
    sa.column("storage_unit_id", sa.Integer()),
    sa.column("storage_slot_id", sa.Integer()),
    sa.column("slot_position", sa.String(length=16)),
    sa.column("location_code", sa.String(length=64)),
)

albums = sa.table(
    "albums",
    sa.column("id", sa.Integer()),
    sa.column("storage_unit", sa.String(length=120)),
    sa.column("storage_niche", sa.String(length=64)),
    sa.column("storage_position", sa.String(length=64)),
    sa.column("location_code", sa.String(length=255)),
)

copy_location_history = sa.table(
    "copy_location_history",
    sa.column("storage_slot_id", sa.Integer()),
    sa.column("slot_position", sa.String(length=16)),
    sa.column("location_code", sa.String(length=64)),
)


def _slot_id(bind, unit_id: int, slot_code: str) -> int | None:
    return bind.execute(
        sa.select(storage_slots.c.id).where(
            sa.and_(
                storage_slots.c.storage_unit_id == unit_id,
                storage_slots.c.slot_code == slot_code,
            )
        )
    ).scalar_one_or_none()


def _normalize_slot(bind, unit_id: int, slot_id: int | None, slot_code: str) -> None:
    if slot_id is None:
        return

    album_ids = [
        row.album_id
        for row in bind.execute(sa.select(copies.c.album_id).where(copies.c.storage_slot_id == slot_id))
    ]
    bind.execute(
        sa.update(copies)
        .where(copies.c.storage_slot_id == slot_id)
        .values(
            storage_unit_id=unit_id,
            slot_position=None,
            location_code=f"K2-{slot_code}",
        )
    )
    if album_ids:
        bind.execute(
            sa.update(albums)
            .where(albums.c.id.in_(album_ids))
            .values(
                storage_unit="K2",
                storage_niche=slot_code,
                storage_position=None,
                location_code=f"K2-{slot_code}",
            )
        )
    bind.execute(
        sa.update(copy_location_history)
        .where(copy_location_history.c.storage_slot_id == slot_id)
        .values(
            slot_position=None,
            location_code=f"K2-{slot_code}",
        )
    )


def upgrade() -> None:
    bind = op.get_bind()
    k2_id = bind.execute(
        sa.select(storage_units.c.id).where(storage_units.c.code == "K2")
    ).scalar_one_or_none()
    if k2_id is None:
        return

    _normalize_slot(bind, k2_id, _slot_id(bind, k2_id, "A1"), "A1")
    _normalize_slot(bind, k2_id, _slot_id(bind, k2_id, "B1"), "B1")


def downgrade() -> None:
    pass
