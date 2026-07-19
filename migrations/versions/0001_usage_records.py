"""Create metadata-only usage records.

Revision ID: 0001
Revises:
Create Date: 2026-07-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_records",
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("client_type", sa.String(length=32), nullable=False),
        sa.Column("requested_model", sa.String(length=255), nullable=False),
        sa.Column("selected_model", sa.String(length=255), nullable=True),
        sa.Column("selected_provider", sa.String(length=100), nullable=True),
        sa.Column("route", sa.String(length=100), nullable=False),
        sa.Column("fallback_attempts", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("time_to_first_token_ms", sa.Float(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("error_category", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("request_id"),
    )


def downgrade() -> None:
    op.drop_table("usage_records")
