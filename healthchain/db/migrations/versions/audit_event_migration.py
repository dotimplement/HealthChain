"""create_audit_events_fhir_jsonb

Revision ID: 750ae404a6bb
Revises:
Create Date: 2026-04-06 00:15:21.714022

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "750ae404a6bb"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("users", sa.Text(), nullable=False),
        sa.Column("accessed_info", sa.Text(), nullable=True),
        sa.Column("action", sa.String(length=1), nullable=False),
        sa.Column("resource", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_users_time", "audit_events", ["users", "time"])
    op.create_index("ix_audit_events_users", "audit_events", ["users"])
    op.create_index("ix_audit_events_accessed_info_time", "audit_events", ["accessed_info", "time"])
    op.create_index("ix_audit_events_accessed_info", "audit_events", ["accessed_info"])
    op.create_index("ix_audit_events_time", "audit_events", ["time"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_recorded", table_name="audit_events")
    op.drop_index("ix_audit_events_accessed_info", table_name="audit_events")
    op.drop_index("ix_audit_events_accessed_info_time", table_name="audit_events")
    op.drop_index("ix_audit_events_users", table_name="audit_events")
    op.drop_index("ix_audit_events_users_time", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_table("audit_events")
