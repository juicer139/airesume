"""create resume_analyses table

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-06

"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("file_ext", sa.String(length=10), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("job_description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="pending"
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_resume_analyses_user_id"), "resume_analyses", ["user_id"]
    )
    op.create_index(
        op.f("ix_resume_analyses_status"), "resume_analyses", ["status"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_resume_analyses_status"), table_name="resume_analyses")
    op.drop_index(op.f("ix_resume_analyses_user_id"), table_name="resume_analyses")
    op.drop_table("resume_analyses")
