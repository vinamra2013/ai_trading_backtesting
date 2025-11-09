# Initial migration for backtesting database schema (Epic 25)
# Revision ID: 001_initial
# Revises:
# Create Date: 2025-01-08

"""Initial migration for backtesting database schema"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create backtests table
    op.create_table(
        "backtests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("strategy_name", sa.String(length=255), nullable=False),
        sa.Column("symbols", sa.JSON(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column(
            "timeframe", sa.String(length=50), server_default="1d", nullable=True
        ),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="pending"
        ),
        sa.Column("mlflow_run_id", sa.String(length=255), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_backtests_id"), "backtests", ["id"], unique=False)
    op.create_index(
        op.f("ix_backtests_strategy_name"), "backtests", ["strategy_name"], unique=False
    )
    op.create_index(
        op.f("ix_backtests_mlflow_run_id"), "backtests", ["mlflow_run_id"], unique=False
    )

    # Create optimizations table
    op.create_table(
        "optimizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("strategy_name", sa.String(length=255), nullable=False),
        sa.Column("parameter_space", sa.JSON(), nullable=False),
        sa.Column(
            "objective_metric",
            sa.String(length=100),
            nullable=False,
            server_default="sharpe_ratio",
        ),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="pending"
        ),
        sa.Column("best_result_id", sa.Integer(), nullable=True),
        sa.Column("best_parameters", sa.JSON(), nullable=True),
        sa.Column("best_metric_value", sa.Float(), nullable=True),
        sa.Column("mlflow_experiment_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["best_result_id"],
            ["backtests.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_optimizations_id"), "optimizations", ["id"], unique=False)
    op.create_index(
        op.f("ix_optimizations_strategy_name"),
        "optimizations",
        ["strategy_name"],
        unique=False,
    )

    # Create analytics_cache table
    op.create_table(
        "analytics_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cache_key", sa.String(length=255), nullable=False),
        sa.Column("cache_type", sa.String(length=100), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("cache_metadata", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key"),
    )
    op.create_index(
        op.f("ix_analytics_cache_id"), "analytics_cache", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_analytics_cache_cache_key"),
        "analytics_cache",
        ["cache_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_analytics_cache_cache_type"),
        "analytics_cache",
        ["cache_type"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Drop tables in reverse order
    op.drop_table("analytics_cache")
    op.drop_table("optimizations")
    op.drop_table("backtests")
