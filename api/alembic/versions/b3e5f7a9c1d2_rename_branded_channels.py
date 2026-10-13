"""rename seeded channels that imitated real media brands (fix plan P0-7)

Renames in place so existing delivery data keeps its channel ids. Rows that were already renamed,
or never existed (fresh seeds use the new names), are simply not matched.

Revision ID: b3e5f7a9c1d2
Revises: a1c4d2e9b7f3
Create Date: 2026-10-13
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b3e5f7a9c1d2"
down_revision: str | None = "a1c4d2e9b7f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RENAMES = {
    "StreamMax Originals": "Quillmere Originals",
    "Magic Kingdom+": "Fernhollow Family+",
    "HubStream": "Brightwick Stream",
    "Peak TV": "Tallowridge TV",
    "Summit Plus": "Ondara Plus",
    "Summit Streaming Network": "Corvane Streaming Network",
    "Discovery Bros Network": "Wildcourt Lifestyle Network",
    "SportsCenter Live": "Fieldhouse Sports Live",
    "Spectrum Cable Apps": "Lanternway Cable Apps",
    "Pluto Free TV": "Pebbleshore Free TV",
}


def _rename(pairs) -> None:
    stmt = sa.text("UPDATE channels SET name = :new WHERE name = :old")
    for old, new in pairs:
        op.get_bind().execute(stmt, {"old": old, "new": new})


def upgrade() -> None:
    _rename(RENAMES.items())


def downgrade() -> None:
    _rename((new, old) for old, new in RENAMES.items())
