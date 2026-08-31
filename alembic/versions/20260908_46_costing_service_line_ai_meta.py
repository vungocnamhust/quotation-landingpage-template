"""ai_meta_json on service_lines — AI Service Drafter provenance (15.7)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260908_46"
down_revision = "20260907_45"
branch_labels = None
depends_on = None

_JSON_VARIANT = sa.JSON().with_variant(JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.add_column("service_lines", sa.Column("ai_meta_json", _JSON_VARIANT, nullable=True))


def downgrade() -> None:
    op.drop_column("service_lines", "ai_meta_json")
