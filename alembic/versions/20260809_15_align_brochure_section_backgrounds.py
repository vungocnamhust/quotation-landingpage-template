"""align brochure section backgrounds across active brand profiles

Revision ID: 20260809_15
Revises: 20260808_14
Create Date: 2026-08-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260809_15"
down_revision = "20260808_14"
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
        "vietnam_safar": {
            "canvas": "#f9f6f0",
            "paper": "#fffaf1",
            "storyContrast": "#17412e",
            "investmentSurface": "#17412e",
            "investmentText": "#ffffff",
        },
        "capella_travel": {
            "canvas": "#f9f6f0",
            "paper": "#fffaf1",
            "storyContrast": "#333333",
            "investmentSurface": "#a98338",
            "investmentText": "#1d1d1b",
        },
        "selvara": {
            "canvas": "#f9f6f0",
            "paper": "#fffaf1",
            "storyContrast": "#17412e",
            "investmentSurface": "#a98338",
            "investmentText": "#11130f",
        },
    })


def downgrade() -> None:
    _update_profiles({
        "vietnam_safar": {
            "storyContrast": None,
            "investmentSurface": None,
            "investmentText": None,
        },
        "capella_travel": {
            "canvas": "#f8f5ef",
            "paper": "#ffffff",
            "storyContrast": None,
            "investmentSurface": None,
            "investmentText": None,
        },
        "selvara": {
            "canvas": "#f7f5ef",
            "paper": "#ffffff",
            "storyContrast": None,
            "investmentSurface": None,
            "investmentText": None,
        },
    })
