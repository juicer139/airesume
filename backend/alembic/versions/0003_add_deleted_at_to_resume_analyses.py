"""add deleted_at to resume_analyses

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-10

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 可空列，已有数据不受影响（NULL = 未删除），无需数据回填
    op.add_column(
        "resume_analyses",
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        op.f("ix_resume_analyses_deleted_at"), "resume_analyses", ["deleted_at"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_resume_analyses_deleted_at"), table_name="resume_analyses")
    op.drop_column("resume_analyses", "deleted_at")