"""update k2 to two vertical slots

Revision ID: 9d3a7c4e2b18
Revises: f42c8b7d19a3
Create Date: 2026-05-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "9d3a7c4e2b18"
down_revision = "f42c8b7d19a3"
branch_labels = None
depends_on = None


storage_units = sa.table(
    "storage_units",
    sa.column("id", sa.Integer()),
    sa.column("code", sa.String(length=16)),
    sa.column("notes", sa.Text()),
)

storage_slots = sa.table(
    "storage_slots",
    sa.column("id", sa.Integer()),
    sa.column("storage_unit_id", sa.Integer()),
    sa.column("row_code", sa.String(length=8)),
    sa.column("col_code", sa.String(length=8)),
    sa.column("slot_code", sa.String(length=16)),
    sa.column("purpose", sa.String(length=128)),
    sa.column("capacity_estimate", sa.Integer()),
    sa.column("notes", sa.Text()),
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


def _move_slot(bind, unit_id: int, source_slot_id: int | None, target_slot_id: int | None, target_code: str) -> None:
    if source_slot_id is None or target_slot_id is None:
        return

    moved_album_ids = [
        row.album_id
        for row in bind.execute(sa.select(copies.c.album_id).where(copies.c.storage_slot_id == source_slot_id))
    ]
    bind.execute(
        sa.update(copies)
        .where(copies.c.storage_slot_id == source_slot_id)
        .values(
            storage_unit_id=unit_id,
            storage_slot_id=target_slot_id,
            slot_position=None,
            location_code=f"K2-{target_code}",
        )
    )
    if moved_album_ids:
        bind.execute(
            sa.update(albums)
            .where(albums.c.id.in_(moved_album_ids))
            .values(
                storage_unit="K2",
                storage_niche=target_code,
                storage_position=None,
                location_code=f"K2-{target_code}",
            )
        )
    bind.execute(
        sa.update(copy_location_history)
        .where(copy_location_history.c.storage_slot_id == source_slot_id)
        .values(
            storage_slot_id=target_slot_id,
            slot_position=None,
            location_code=f"K2-{target_code}",
        )
    )


def _normalize_target_slot(bind, unit_id: int, target_slot_id: int | None, target_code: str) -> None:
    if target_slot_id is None:
        return

    album_ids = [
        row.album_id
        for row in bind.execute(sa.select(copies.c.album_id).where(copies.c.storage_slot_id == target_slot_id))
    ]
    bind.execute(
        sa.update(copies)
        .where(copies.c.storage_slot_id == target_slot_id)
        .values(
            storage_unit_id=unit_id,
            slot_position=None,
            location_code=f"K2-{target_code}",
        )
    )
    if album_ids:
        bind.execute(
            sa.update(albums)
            .where(albums.c.id.in_(album_ids))
            .values(
                storage_unit="K2",
                storage_niche=target_code,
                storage_position=None,
                location_code=f"K2-{target_code}",
            )
        )


def upgrade() -> None:
    bind = op.get_bind()
    k2_id = bind.execute(
        sa.select(storage_units.c.id).where(storage_units.c.code == "K2")
    ).scalar_one_or_none()
    if k2_id is None:
        return

    a1_id = _slot_id(bind, k2_id, "A1")
    a2_id = _slot_id(bind, k2_id, "A2")
    b1_id = _slot_id(bind, k2_id, "B1")
    b2_id = _slot_id(bind, k2_id, "B2")

    _move_slot(bind, k2_id, a2_id, a1_id, "A1")
    _move_slot(bind, k2_id, b2_id, b1_id, "B1")

    bind.execute(
        sa.update(storage_units)
        .where(storage_units.c.id == k2_id)
        .values(notes="Triagem, pendencias e recem-chegados em dois nichos verticais")
    )

    updates = {
        "A1": ("A", "1", "Triagem / entrada", 65, "Nicho vertical de entrada e triagem"),
        "B1": ("B", "1", "Pendencias / recem-chegados", 70, "Nicho vertical para pendencias e discos recem-chegados"),
    }
    for slot_code, (row_code, col_code, purpose, capacity, notes) in updates.items():
        bind.execute(
            sa.update(storage_slots)
            .where(
                sa.and_(
                    storage_slots.c.storage_unit_id == k2_id,
                    storage_slots.c.slot_code == slot_code,
                )
            )
            .values(
                row_code=row_code,
                col_code=col_code,
                purpose=purpose,
                capacity_estimate=capacity,
                notes=notes,
            )
        )

    _normalize_target_slot(bind, k2_id, a1_id, "A1")
    _normalize_target_slot(bind, k2_id, b1_id, "B1")

    for slot_code in ("A2", "B2"):
        bind.execute(
            sa.delete(storage_slots).where(
                sa.and_(
                    storage_slots.c.storage_unit_id == k2_id,
                    storage_slots.c.slot_code == slot_code,
                )
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    k2_id = bind.execute(
        sa.select(storage_units.c.id).where(storage_units.c.code == "K2")
    ).scalar_one_or_none()
    if k2_id is None:
        return

    existing_slots = {
        row.slot_code
        for row in bind.execute(
            sa.select(storage_slots.c.slot_code).where(storage_slots.c.storage_unit_id == k2_id)
        )
    }

    legacy_slots = [
        ("A1", "A", "1", "triagem", 40, "Entrada e triagem"),
        ("A2", "A", "2", "support", 25, "Acessorios e material de apoio"),
        ("B1", "B", "1", "new-arrivals", 35, "Discos recem-chegados"),
        ("B2", "B", "2", "pending", 35, "Pendencias e itens sem endereco final"),
    ]
    for slot_code, row_code, col_code, purpose, capacity, notes in legacy_slots:
        values = {
            "storage_unit_id": k2_id,
            "row_code": row_code,
            "col_code": col_code,
            "slot_code": slot_code,
            "purpose": purpose,
            "capacity_estimate": capacity,
            "notes": notes,
        }
        if slot_code in existing_slots:
            bind.execute(
                sa.update(storage_slots)
                .where(
                    sa.and_(
                        storage_slots.c.storage_unit_id == k2_id,
                        storage_slots.c.slot_code == slot_code,
                    )
                )
                .values(**values)
            )
        else:
            bind.execute(sa.insert(storage_slots).values(**values))

    bind.execute(
        sa.update(storage_units)
        .where(storage_units.c.id == k2_id)
        .values(notes="Triagem, apoio e pendencias")
    )
