"""fix selvara brand render profile ink contrast

Revision ID: 20260820_26
Revises: 20260818_25
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_26"
down_revision = "20260818_25"
branch_labels = None
depends_on = None


BRANDS = sa.table(
    "brands",
    sa.column("id", sa.String),
    sa.column("render_profile", sa.JSON),
)


def _update_profiles(palette_updates: dict[str, dict[str, str | None]]) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(BRANDS.c.id, BRANDS.c.render_profile).where(
            BRANDS.c.id.in_(tuple(palette_updates))
        )
    ).mappings()

    for row in rows:
        profile = dict(row["render_profile"] or {})
        palette = dict(profile.get("palette") or {})
        for key, value in palette_updates[row["id"]].items():
            if value is None:
                palette.pop(key, None)
            else:
                palette[key] = value
        profile["palette"] = palette
        bind.execute(
            sa.update(BRANDS)
            .where(BRANDS.c.id == row["id"])
            .values(render_profile=profile)
        )


def upgrade() -> None:
    _update_profiles({
        "selvara": {
            "ink": "#11130f",
        },
    })


def downgrade() -> None:
    _update_profiles({
        "selvara": {
            "ink": "#283027",
        },
    })
