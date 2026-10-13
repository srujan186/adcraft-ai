"""delivery loop: sim_clock + attribution indexes

Revision ID: a1c4d2e9b7f3
Revises: f189da0eaf7b
Create Date: 2026-10-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c4d2e9b7f3"
down_revision: str | None = "f189da0eaf7b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sim_clock",
        sa.Column("name", sa.String(length=40), primary_key=True),
        sa.Column("last_tick_at", sa.DateTime(timezone=True), nullable=False),
    )
    # set-based attribution: "this household's latest impression from this advertiser"
    op.create_index("ix_impressions_hh_adv_ts", "impressions", ["household_id", "advertiser_id", "ts"])
    # set-based attribution: "has this event been credited yet"
    op.create_index("ix_conversions_event_id", "conversions", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_conversions_event_id", table_name="conversions")
    op.drop_index("ix_impressions_hh_adv_ts", table_name="impressions")
    op.drop_table("sim_clock")
