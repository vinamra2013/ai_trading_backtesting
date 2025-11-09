# Add max_trials and optimization_method fields to optimizations table

"""add optimization fields

Revision ID: 002_add_optimization_fields
Revises: 001_initial
Create Date: 2024-11-09 15:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_add_optimization_fields"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add max_trials column
    op.add_column("optimizations", sa.Column("max_trials", sa.Integer(), nullable=True))

    # Add optimization_method column
    op.add_column(
        "optimizations",
        sa.Column(
            "optimization_method", sa.String(length=50), nullable=True, default="grid"
        ),
    )


def downgrade() -> None:
    # Remove the columns in reverse order
    op.drop_column("optimizations", "optimization_method")
    op.drop_column("optimizations", "max_trials")
