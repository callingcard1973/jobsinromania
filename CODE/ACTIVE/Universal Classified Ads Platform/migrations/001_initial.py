"""Initial migration

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('NOW()'))
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'ads',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('price', sa.Numeric(12, 2), nullable=True),
        sa.Column('location', sa.String(200), nullable=False),
        sa.Column('contact_info', sa.String(500), nullable=True),
        sa.Column('tags', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft', index=True),
        sa.Column('is_featured', sa.Boolean(), nullable=False, server_default=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_ads_category', 'ads', ['category'])

    op.create_table(
        'ad_media',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ad_id', sa.Integer(), sa.ForeignKey('ads.id'), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('thumbnail_path', sa.String(500), nullable=True),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'))
    )

    op.create_table(
        'external_posts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('ad_id', sa.Integer(), sa.ForeignKey('ads.id'), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('NOW()'))
    )


def downgrade():
    op.drop_table('external_posts')
    op.drop_table('ad_media')
    op.drop_index('ix_ads_category', 'ads')
    op.drop_table('ads')
    op.drop_index('ix_users_email', 'users')
    op.drop_table('users')