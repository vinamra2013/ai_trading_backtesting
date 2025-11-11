# Add discovery and ranking tables for Epic 26

"""add discovery ranking tables

Revision ID: 003_add_discovery_ranking_tables
Revises: 002_add_optimization_fields
Create Date: 2024-11-09 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_add_discovery_ranking_tables"
down_revision: Union[str, None] = "002_add_optimization_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create discovery_jobs table
    op.create_table(
        "discovery_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("scanner_name", sa.String(length=100), nullable=False),
        sa.Column("scanner_type", sa.String(length=100), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("progress", sa.Float(), nullable=True),
        sa.Column("symbols_discovered", sa.Integer(), nullable=True),
        sa.Column("symbols_filtered", sa.Integer(), nullable=True),
        sa.Column("result_data", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )

    # Create discovery_results table
    op.create_table(
        "discovery_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("exchange", sa.String(length=20), nullable=False),
        sa.Column("sector", sa.String(length=100), nullable=True),
        sa.Column("avg_volume", sa.Integer(), nullable=True),
        sa.Column("atr", sa.Float(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("pct_change", sa.Float(), nullable=True),
        sa.Column("market_cap", sa.Integer(), nullable=True),
        sa.Column("volume", sa.Integer(), nullable=True),
        sa.Column("scanner_type", sa.String(length=100), nullable=False),
        sa.Column(
            "discovery_timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["discovery_jobs.job_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create ranking_jobs table
    op.create_table(
        "ranking_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("input_type", sa.String(length=50), nullable=False),
        sa.Column("input_source", sa.String(length=500), nullable=True),
        sa.Column("criteria_weights", sa.JSON(), nullable=False),
        sa.Column("ranking_config", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("progress", sa.Float(), nullable=True),
        sa.Column("total_strategies", sa.Integer(), nullable=True),
        sa.Column("ranked_strategies", sa.Integer(), nullable=True),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )

    # Create ranking_results table
    op.create_table(
        "ranking_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("strategy_name", sa.String(length=255), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=True),
        sa.Column("sharpe_ratio", sa.Float(), nullable=True),
        sa.Column("max_drawdown", sa.Float(), nullable=True),
        sa.Column("win_rate", sa.Float(), nullable=True),
        sa.Column("total_trades", sa.Integer(), nullable=True),
        sa.Column("profit_factor", sa.Float(), nullable=True),
        sa.Column("sharpe_score", sa.Float(), nullable=True),
        sa.Column("consistency_score", sa.Float(), nullable=True),
        sa.Column("drawdown_score", sa.Float(), nullable=True),
        sa.Column("frequency_score", sa.Float(), nullable=True),
        sa.Column("efficiency_score", sa.Float(), nullable=True),
        sa.Column("composite_score", sa.Float(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["ranking_jobs.job_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for performance
    op.create_index(
        op.f("ix_discovery_jobs_job_id"), "discovery_jobs", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_discovery_jobs_scanner_name"),
        "discovery_jobs",
        ["scanner_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_jobs_status"), "discovery_jobs", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_discovery_results_job_id"),
        "discovery_results",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_discovery_results_symbol"),
        "discovery_results",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ranking_jobs_job_id"), "ranking_jobs", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_ranking_jobs_input_type"), "ranking_jobs", ["input_type"], unique=False
    )
    op.create_index(
        op.f("ix_ranking_jobs_status"), "ranking_jobs", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_ranking_results_job_id"), "ranking_results", ["job_id"], unique=False
    )
    op.create_index(
        op.f("ix_ranking_results_rank"), "ranking_results", ["rank"], unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_ranking_results_rank"), table_name="ranking_results")
    op.drop_index(op.f("ix_ranking_results_job_id"), table_name="ranking_results")
    op.drop_index(op.f("ix_ranking_jobs_status"), table_name="ranking_jobs")
    op.drop_index(op.f("ix_ranking_jobs_input_type"), table_name="ranking_jobs")
    op.drop_index(op.f("ix_ranking_jobs_job_id"), table_name="ranking_jobs")
    op.drop_index(op.f("ix_discovery_results_symbol"), table_name="discovery_results")
    op.drop_index(op.f("ix_discovery_results_job_id"), table_name="discovery_results")
    op.drop_index(op.f("ix_discovery_jobs_status"), table_name="discovery_jobs")
    op.drop_index(op.f("ix_discovery_jobs_scanner_name"), table_name="discovery_jobs")
    op.drop_index(op.f("ix_discovery_jobs_job_id"), table_name="discovery_jobs")

    # Drop tables
    op.drop_table("ranking_results")
    op.drop_table("ranking_jobs")
    op.drop_table("discovery_results")
    op.drop_table("discovery_jobs")
