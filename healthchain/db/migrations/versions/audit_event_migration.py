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
        sa.Column("recorded", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agent_who", sa.Text(), nullable=False),
        sa.Column("entity_what", sa.Text(), nullable=True),
        sa.Column("action", sa.String(length=1), nullable=False),
        sa.Column("resource", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_agent_recorded", "audit_events", ["agent_who", "recorded"])
    op.create_index("ix_audit_events_agent_who", "audit_events", ["agent_who"])
    op.create_index("ix_audit_events_entity_recorded", "audit_events", ["entity_what", "recorded"])
    op.create_index("ix_audit_events_entity_what", "audit_events", ["entity_what"])
    op.create_index("ix_audit_events_recorded", "audit_events", ["recorded"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_recorded", table_name="audit_events")
    op.drop_index("ix_audit_events_entity_what", table_name="audit_events")
    op.drop_index("ix_audit_events_entity_recorded", table_name="audit_events")
    op.drop_index("ix_audit_events_agent_who", table_name="audit_events")
    op.drop_index("ix_audit_events_agent_recorded", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_table("audit_events")
