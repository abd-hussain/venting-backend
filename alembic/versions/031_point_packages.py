"""Add point packages and purchases

Revision ID: 031_point_packages
Revises: 030_drop_achievements
Create Date: 2026-08-29 21:58:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "031_point_packages"
down_revision: Union[str, Sequence[str], None] = "030_drop_achievements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

point_purchase_status = postgresql.ENUM(
    "completed",
    "pending",
    "failed",
    name="point_purchase_status",
    create_type=False,
)


def upgrade() -> None:
    point_purchase_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "point_packages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("price_usd", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("bonus_percent", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        "ix_point_packages_active_sort",
        "point_packages",
        ["is_active", "sort_order"],
        unique=False,
    )
    op.create_table(
        "point_purchases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("ventor_id", sa.UUID(), nullable=False),
        sa.Column("package_id", sa.UUID(), nullable=False),
        sa.Column("package_code", sa.String(length=64), nullable=False),
        sa.Column("points_added", sa.Integer(), nullable=False),
        sa.Column("price_usd", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("payment_provider", sa.String(length=32), nullable=True),
        sa.Column("payment_reference", sa.String(length=128), nullable=True),
        sa.Column(
            "status",
            point_purchase_status,
            nullable=False,
        ),
        sa.Column(
            "purchased_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["package_id"], ["point_packages.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["ventor_id"], ["ventor_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payment_reference", name="uq_point_purchases_payment_reference"
        ),
    )
    op.create_index(
        "ix_point_purchases_ventor_purchased",
        "point_purchases",
        ["ventor_id", "purchased_at"],
        unique=False,
    )
    op.execute(
        sa.text(
            """
            INSERT INTO point_packages (id, code, points, price_usd, bonus_percent, sort_order, is_active)
            VALUES
                ('44444444-4444-4444-4444-444444444441', 'pkg_500', 500, 4.99, NULL, 1, true),
                ('44444444-4444-4444-4444-444444444442', 'pkg_1200', 1200, 9.99, 20, 2, true),
                ('44444444-4444-4444-4444-444444444443', 'pkg_2800', 2800, 19.99, 40, 3, true)
            ON CONFLICT (code) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_point_purchases_ventor_purchased", table_name="point_purchases")
    op.drop_table("point_purchases")
    op.drop_index("ix_point_packages_active_sort", table_name="point_packages")
    op.drop_table("point_packages")
    point_purchase_status.drop(op.get_bind(), checkfirst=True)
