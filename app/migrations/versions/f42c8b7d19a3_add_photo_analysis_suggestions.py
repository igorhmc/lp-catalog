"""add photo analysis suggestions

Revision ID: f42c8b7d19a3
Revises: c2d4f7e1aa91
Create Date: 2026-05-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "f42c8b7d19a3"
down_revision = "c2d4f7e1aa91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "photo_analysis_suggestions" not in table_names:
        op.create_table(
            "photo_analysis_suggestions",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("copy_id", sa.Integer(), nullable=False),
            sa.Column("field_name", sa.String(length=64), nullable=False),
            sa.Column("label", sa.String(length=120), nullable=False),
            sa.Column("current_value", sa.Text(), nullable=True),
            sa.Column("suggested_value", sa.Text(), nullable=False),
            sa.Column("confidence", sa.Integer(), nullable=True),
            sa.Column("rationale", sa.Text(), nullable=True),
            sa.Column("source_photo_ids", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["copy_id"], ["copies.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_photo_analysis_suggestions_copy_id", "photo_analysis_suggestions", ["copy_id"], unique=False)
        op.create_index("ix_photo_analysis_suggestions_status", "photo_analysis_suggestions", ["status"], unique=False)
        op.create_index(
            "ix_photo_analysis_suggestions_copy_status",
            "photo_analysis_suggestions",
            ["copy_id", "status"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if "photo_analysis_suggestions" in table_names:
        op.drop_index("ix_photo_analysis_suggestions_copy_status", table_name="photo_analysis_suggestions")
        op.drop_index("ix_photo_analysis_suggestions_status", table_name="photo_analysis_suggestions")
        op.drop_index("ix_photo_analysis_suggestions_copy_id", table_name="photo_analysis_suggestions")
        op.drop_table("photo_analysis_suggestions")
