"""add triage boxes

Revision ID: e8b7a4c2d9f1
Revises: d4f8c2a91b73
Create Date: 2026-05-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e8b7a4c2d9f1"
down_revision = "d4f8c2a91b73"
branch_labels = None
depends_on = None


storage_units = sa.table(
    "storage_units",
    sa.column("id", sa.Integer()),
    sa.column("code", sa.String(length=16)),
    sa.column("name", sa.String(length=255)),
    sa.column("room", sa.String(length=128)),
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


TRIAGE_BOXES = [
    {
        "code": "BOX1",
        "name": "Box fechada",
        "room": "Sala",
        "notes": "Caixa fechavel para discos pendentes ou em triagem",
        "slot": {
            "slot_code": "A1",
            "row_code": "A",
            "col_code": "1",
            "purpose": "Triagem / pendencias",
            "capacity_estimate": 65,
            "notes": "Discos aguardando classificacao, limpeza ou endereco final",
        },
    },
    {
        "code": "BOX2",
        "name": "Caixa sobre o movel",
        "room": "Sala",
        "notes": "Caixa superior para discos pendentes ou em triagem",
        "slot": {
            "slot_code": "A1",
            "row_code": "A",
            "col_code": "1",
            "purpose": "Triagem / pendencias",
            "capacity_estimate": 65,
            "notes": "Discos aguardando classificacao, limpeza ou endereco final",
        },
    },
]


def _upsert_storage_unit(bind, unit: dict) -> int:
    unit_id = bind.execute(
        sa.select(storage_units.c.id).where(storage_units.c.code == unit["code"])
    ).scalar_one_or_none()
    values = {
        "code": unit["code"],
        "name": unit["name"],
        "room": unit["room"],
        "notes": unit["notes"],
    }
    if unit_id is None:
        bind.execute(sa.insert(storage_units).values(**values))
        return bind.execute(
            sa.select(storage_units.c.id).where(storage_units.c.code == unit["code"])
        ).scalar_one()

    bind.execute(
        sa.update(storage_units)
        .where(storage_units.c.id == unit_id)
        .values(**values)
    )
    return unit_id


def _upsert_storage_slot(bind, unit_id: int, slot: dict) -> None:
    slot_id = bind.execute(
        sa.select(storage_slots.c.id).where(
            sa.and_(
                storage_slots.c.storage_unit_id == unit_id,
                storage_slots.c.slot_code == slot["slot_code"],
            )
        )
    ).scalar_one_or_none()
    values = {
        "storage_unit_id": unit_id,
        "row_code": slot["row_code"],
        "col_code": slot["col_code"],
        "slot_code": slot["slot_code"],
        "purpose": slot["purpose"],
        "capacity_estimate": slot["capacity_estimate"],
        "notes": slot["notes"],
    }
    if slot_id is None:
        bind.execute(sa.insert(storage_slots).values(**values))
        return

    bind.execute(
        sa.update(storage_slots)
        .where(storage_slots.c.id == slot_id)
        .values(**values)
    )


def upgrade() -> None:
    bind = op.get_bind()
    for unit in TRIAGE_BOXES:
        unit_id = _upsert_storage_unit(bind, unit)
        _upsert_storage_slot(bind, unit_id, unit["slot"])


def downgrade() -> None:
    bind = op.get_bind()
    for code in ("BOX1", "BOX2"):
        unit_id = bind.execute(
            sa.select(storage_units.c.id).where(storage_units.c.code == code)
        ).scalar_one_or_none()
        if unit_id is None:
            continue

        bind.execute(
            sa.delete(storage_slots).where(storage_slots.c.storage_unit_id == unit_id)
        )
        bind.execute(sa.delete(storage_units).where(storage_units.c.id == unit_id))
