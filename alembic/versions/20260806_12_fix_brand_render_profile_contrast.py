"""repair seeded V2 brand profiles to satisfy the runtime color contract

Revision ID: 20260806_12
Revises: 20260806_11
"""
from alembic import op


revision = "20260806_12"
down_revision = "20260806_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 20260806_09 is immutable.  Its gold focus colors do not meet the React
    # display contract against their light canvases, so correct mutable brand
    # configuration in a forward-only migration.  No quotation/release data is
    # touched.
    op.execute(
        """
        UPDATE brands
        SET render_profile = jsonb_set(render_profile::jsonb, '{palette,focus}', '"#8a6500"'::jsonb)::json
        WHERE id IN ('capella_travel', 'vietnam_safar')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE brands
        SET render_profile = jsonb_set(
            render_profile::jsonb,
            '{palette,focus}',
            CASE id
                WHEN 'capella_travel' THEN '"#cba135"'::jsonb
                WHEN 'vietnam_safar' THEN '"#b7894b"'::jsonb
            END
        )::json
        WHERE id IN ('capella_travel', 'vietnam_safar')
        """
    )
