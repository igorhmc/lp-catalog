"""update k1 slot purposes

Revision ID: c2d4f7e1aa91
Revises: a1c4e9b7f3d2
Create Date: 2026-05-08 19:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "c2d4f7e1aa91"
down_revision = "a1c4e9b7f3d2"
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
    sa.column("purpose", sa.String(length=32)),
    sa.column("notes", sa.Text()),
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column(
            "storage_slots",
            "purpose",
            existing_type=sa.String(length=32),
            type_=sa.String(length=128),
            existing_nullable=True,
        )
    k1_id = bind.execute(
        sa.select(storage_units.c.id).where(storage_units.c.code == "K1")
    ).scalar_one_or_none()
    if k1_id is None:
        return

    updates = {
        "A1": ("Forró 1", "Bloco principal de Forró"),
        "A2": ("Forró 2", "Bloco principal de Forró"),
        "A3": ("MPB / Brasil não-forró", "Musica brasileira fora do bloco de Forró"),
        "A4": ("Internacional", "Catalogo internacional"),
        "B1": ("Forró 3", "Bloco principal de Forró"),
        "B2": ("Forró 4", "Bloco principal de Forró"),
        "B3": ("Triagem", "Triagem e reorganizacao"),
        "B4": ("Crescimento / extras / compilações", "Folga para crescimento, extras e coletaneas"),
    }

    for slot_code, (purpose, notes) in updates.items():
        bind.execute(
            sa.update(storage_slots)
            .where(
                sa.and_(
                    storage_slots.c.storage_unit_id == k1_id,
                    storage_slots.c.slot_code == slot_code,
                )
            )
            .values(purpose=purpose, notes=notes)
        )


def downgrade() -> None:
    bind = op.get_bind()
    k1_id = bind.execute(
        sa.select(storage_units.c.id).where(storage_units.c.code == "K1")
    ).scalar_one_or_none()
    if k1_id is None:
        return

    updates = {
        "A1": ("collection", "Colecao principal"),
        "A2": ("collection", "Colecao principal"),
        "A3": ("collection", "Colecao principal"),
        "A4": ("collection", "Colecao principal"),
        "B1": ("collection", "Colecao principal"),
        "B2": ("collection", "Colecao principal"),
        "B3": ("triagem", "Triagem e reorganizacao"),
        "B4": ("growth", "Reserva para crescimento"),
    }

    for slot_code, (purpose, notes) in updates.items():
        bind.execute(
            sa.update(storage_slots)
            .where(
                sa.and_(
                    storage_slots.c.storage_unit_id == k1_id,
                    storage_slots.c.slot_code == slot_code,
                )
            )
            .values(purpose=purpose, notes=notes)
        )

    if bind.dialect.name != "sqlite":
        op.alter_column(
            "storage_slots",
            "purpose",
            existing_type=sa.String(length=128),
            type_=sa.String(length=32),
            existing_nullable=True,
        )
