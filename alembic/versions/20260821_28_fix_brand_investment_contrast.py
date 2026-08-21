"""fix brand investment surface contrast and WCAG AA palette tokens

Revision ID: 20260821_28
Revises: 20260821_27
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_28"
down_revision = "20260821_27"
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
            "accentAlt": "#8b642e",
            "investmentSurface": "#0d3f32",
            "investmentText": "#ffffff",
        },
        "capella_travel": {
            "accentAlt": "#7a591a",
            "contrast": "#5e4514",
            "focus": "#7a591a",
            "investmentSurface": "#333333",
            "investmentText": "#ffffff",
        },
        "selvara": {
            "accent": "#7a591a",
            "accentAlt": "#7a591a",
            "contrast": "#524018",
            "focus": "#7a591a",
            "investmentSurface": "#0d3f32",
            "investmentText": "#ffffff",
        },
    })


def downgrade() -> None:
    _update_profiles({
        "vietnam_safar": {
            "accentAlt": "#b7894b",
            "investmentSurface": "#17412e",
            "investmentText": "#ffffff",
        },
        "capella_travel": {
            "accentAlt": "#a98338",
            "contrast": "#a98338",
            "focus": "#a98338",
            "investmentSurface": "#a98338",
            "investmentText": "#1d1d1b",
        },
        "selvara": {
            "accent": "#a98338",
            "accentAlt": "#a98338",
            "contrast": "#a98338",
            "focus": "#a98338",
            "investmentSurface": "#a98338",
            "investmentText": "#11130f",
        },
    })
