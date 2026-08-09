"""normalize brand chrome radii and Capella's non-green story surface

Revision ID: 20260809_16
Revises: 20260809_15
Create Date: 2026-08-09
"""

from alembic import op
import sqlalchemy as sa


revision = "20260809_16"
down_revision = "20260809_15"
branch_labels = None
depends_on = None


BRANDS = sa.table(
    "brands",
    sa.column("id", sa.String),
    sa.column("render_profile", sa.JSON),
)

LEGACY_RADII = {
    "card": "1.25rem",
    "button": "999px",
    "frame": "1.75rem",
    "pill": "999px",
}

CHROME_RADII = {
    "card": "0.5rem",
    "button": "0.375rem",
    "frame": "0.625rem",
    "pill": "999px",
}


def _update_profiles(
    *,
    capella_story_contrast: str,
    source_radii: dict[str, str],
    radii: dict[str, str],
) -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.select(BRANDS.c.id, BRANDS.c.render_profile)).mappings()
    for row in rows:
        profile = dict(row["render_profile"] or {})
        replace_radii = profile.get("radii") == source_radii
        if replace_radii:
            profile["radii"] = dict(radii)
        if row["id"] == "capella_travel":
            palette = dict(profile.get("palette") or {})
            palette["storyContrast"] = capella_story_contrast
            profile["palette"] = palette
        if replace_radii or row["id"] == "capella_travel":
            bind.execute(sa.update(BRANDS).where(BRANDS.c.id == row["id"]).values(render_profile=profile))


def upgrade() -> None:
    _update_profiles(
        capella_story_contrast="#333333",
        source_radii=LEGACY_RADII,
        radii=CHROME_RADII,
    )


def downgrade() -> None:
    _update_profiles(
        capella_story_contrast="#17412e",
        source_radii=CHROME_RADII,
        radii=LEGACY_RADII,
    )
