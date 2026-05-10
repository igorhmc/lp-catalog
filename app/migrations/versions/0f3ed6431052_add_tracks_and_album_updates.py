"""empty message

Revision ID: 0f3ed6431052
Revises: 
Create Date: 2025-09-15 00:05:30.148513

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '0f3ed6431052'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if 'artists' not in table_names:
        op.create_table(
            'artists',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('country', sa.String(length=64), nullable=True),
        )
        op.create_index(op.f('ix_artists_id'), 'artists', ['id'], unique=False)
        op.create_index(op.f('ix_artists_name'), 'artists', ['name'], unique=True)

    if 'albums' not in table_names:
        op.create_table(
            'albums',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('year', sa.Integer(), nullable=True),
            sa.Column('genre', sa.String(length=64), nullable=True),
            sa.Column('storage_unit', sa.String(length=120), nullable=True),
            sa.Column('storage_niche', sa.String(length=64), nullable=True),
            sa.Column('storage_position', sa.String(length=64), nullable=True),
            sa.Column('cover_path', sa.String(length=255), nullable=True),
            sa.Column('discogs_id', sa.Integer(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('artist_id', sa.Integer(), sa.ForeignKey('artists.id', ondelete='CASCADE'), nullable=False),
            sa.UniqueConstraint('discogs_id', name='uq_albums_discogs_id'),
        )
        op.create_index(op.f('ix_albums_id'), 'albums', ['id'], unique=False)
        op.create_index(op.f('ix_albums_title'), 'albums', ['title'], unique=False)
        op.create_index(op.f('ix_albums_artist_id'), 'albums', ['artist_id'], unique=False)
    else:
        album_columns = {column['name'] for column in inspector.get_columns('albums')}
        if 'storage_unit' not in album_columns:
            op.add_column('albums', sa.Column('storage_unit', sa.String(length=120), nullable=True))
        if 'storage_niche' not in album_columns:
            op.add_column('albums', sa.Column('storage_niche', sa.String(length=64), nullable=True))
        if 'storage_position' not in album_columns:
            op.add_column('albums', sa.Column('storage_position', sa.String(length=64), nullable=True))
        if 'cover_path' not in album_columns:
            op.add_column('albums', sa.Column('cover_path', sa.String(length=255), nullable=True))
        if 'discogs_id' not in album_columns:
            op.add_column('albums', sa.Column('discogs_id', sa.Integer(), nullable=True))
        if 'notes' not in album_columns:
            op.add_column('albums', sa.Column('notes', sa.Text(), nullable=True))

        unique_constraints = {constraint['name'] for constraint in inspector.get_unique_constraints('albums')}
        if 'uq_albums_discogs_id' not in unique_constraints and bind.dialect.name != 'sqlite':
            op.create_unique_constraint('uq_albums_discogs_id', 'albums', ['discogs_id'])

    if 'tracks' not in table_names:
        op.create_table(
            'tracks',
            sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
            sa.Column('position', sa.String(length=8), nullable=False),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('duration', sa.String(length=16), nullable=False),
            sa.Column('album_id', sa.Integer(), sa.ForeignKey('albums.id', ondelete='CASCADE'), nullable=False),
        )
        op.create_index(op.f('ix_tracks_id'), 'tracks', ['id'], unique=False)
        op.create_index(op.f('ix_tracks_album_id'), 'tracks', ['album_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())

    if 'tracks' in table_names:
        op.drop_index(op.f('ix_tracks_album_id'), table_name='tracks')
        op.drop_index(op.f('ix_tracks_id'), table_name='tracks')
        op.drop_table('tracks')

    if 'albums' in table_names:
        unique_constraints = {constraint['name'] for constraint in inspector.get_unique_constraints('albums')}
        if 'uq_albums_discogs_id' in unique_constraints:
            op.drop_constraint('uq_albums_discogs_id', 'albums', type_='unique')
        album_columns = {column['name'] for column in inspector.get_columns('albums')}
        if 'notes' in album_columns:
            op.drop_column('albums', 'notes')
        if 'discogs_id' in album_columns:
            op.drop_column('albums', 'discogs_id')
        if 'cover_path' in album_columns:
            op.drop_column('albums', 'cover_path')
        if 'storage_position' in album_columns:
            op.drop_column('albums', 'storage_position')
        if 'storage_niche' in album_columns:
            op.drop_column('albums', 'storage_niche')
        if 'storage_unit' in album_columns:
            op.drop_column('albums', 'storage_unit')
        album_indexes = {index['name'] for index in inspector.get_indexes('albums')}
        if op.f('ix_albums_artist_id') in album_indexes:
            op.drop_index(op.f('ix_albums_artist_id'), table_name='albums')
        if op.f('ix_albums_title') in album_indexes:
            op.drop_index(op.f('ix_albums_title'), table_name='albums')
        if op.f('ix_albums_id') in album_indexes:
            op.drop_index(op.f('ix_albums_id'), table_name='albums')
        op.drop_table('albums')

    if 'artists' in table_names:
        artist_indexes = {index['name'] for index in inspector.get_indexes('artists')}
        if op.f('ix_artists_name') in artist_indexes:
            op.drop_index(op.f('ix_artists_name'), table_name='artists')
        if op.f('ix_artists_id') in artist_indexes:
            op.drop_index(op.f('ix_artists_id'), table_name='artists')
        op.drop_table('artists')
