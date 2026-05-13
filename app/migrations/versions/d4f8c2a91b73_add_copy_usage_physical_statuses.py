"""add copy usage and physical statuses

Revision ID: d4f8c2a91b73
Revises: b6a1d2e9f405
Create Date: 2026-05-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d4f8c2a91b73"
down_revision = "b6a1d2e9f405"
branch_labels = None
depends_on = None


copies = sa.table(
    "copies",
    sa.column("status", sa.String(length=32)),
    sa.column("usage_status", sa.String(length=32)),
    sa.column("physical_status", sa.String(length=32)),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("copies")}

    if "usage_status" not in columns:
        op.add_column("copies", sa.Column("usage_status", sa.String(length=32), nullable=True))
    if "physical_status" not in columns:
        op.add_column("copies", sa.Column("physical_status", sa.String(length=32), nullable=True))

    status_to_usage = sa.case(
        (copies.c.status == "emprestado", "emprestado"),
        (copies.c.status == "reservado", "reservado"),
        else_="disponivel",
    )
    status_to_physical = sa.case(
        (copies.c.status == "guardado", "no_lugar"),
        (copies.c.status == "catalogado", "no_lugar"),
        (copies.c.status == "emprestado", "fora_do_lugar"),
        (copies.c.status == "reservado", "a_guardar"),
        else_="triagem",
    )
    bind.execute(
        sa.update(copies).values(
            usage_status=status_to_usage,
            physical_status=status_to_physical,
        )
    )

    if bind.dialect.name != "sqlite":
        op.alter_column(
            "copies",
            "usage_status",
            existing_type=sa.String(length=32),
            nullable=False,
        )
        op.alter_column(
            "copies",
            "physical_status",
            existing_type=sa.String(length=32),
            nullable=False,
        )

    indexes = {index["name"] for index in inspector.get_indexes("copies")}
    if "ix_copies_usage_physical_status" not in indexes:
        op.create_index(
            "ix_copies_usage_physical_status",
            "copies",
            ["usage_status", "physical_status"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("copies")}
    if "ix_copies_usage_physical_status" in indexes:
        op.drop_index("ix_copies_usage_physical_status", table_name="copies")

    columns = {column["name"] for column in inspector.get_columns("copies")}
    if "physical_status" in columns:
        op.drop_column("copies", "physical_status")
    if "usage_status" in columns:
        op.drop_column("copies", "usage_status")
