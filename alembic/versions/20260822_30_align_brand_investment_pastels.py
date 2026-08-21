"""align brand investment pastel surface tokens and fix selvara identity

Revision ID: 20260822_30
Revises: 20260822_29
Create Date: 2026-08-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260822_30"
down_revision = "20260822_29"
branch_labels = None
depends_on = None


BRANDS = sa.table(
    "brands",
    sa.column("id", sa.String),
    sa.column("render_profile", sa.JSON),
)

PUBLICATION_RELEASES = sa.table(
    "publication_releases",
    sa.column("id", sa.String),
    sa.column("render_profile_snapshot", sa.JSON),
)


def _update_profiles(palette_updates: dict[str, dict[str, str | None]]) -> None:
    bind = op.get_bind()

    # 1. Update brands table
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

    # 2. Update publication_releases table snapshots
    release_rows = bind.execute(
        sa.select(PUBLICATION_RELEASES.c.id, PUBLICATION_RELEASES.c.render_profile_snapshot)
    ).mappings()

    for r_row in release_rows:
        r_profile = dict(r_row["render_profile_snapshot"] or {})
        brand_id = r_profile.get("id")
        if brand_id and brand_id in palette_updates:
            r_palette = dict(r_profile.get("palette") or {})
            for key, value in palette_updates[brand_id].items():
                if value is None:
                    r_palette.pop(key, None)
                else:
                    r_palette[key] = value
            r_profile["palette"] = r_palette
            bind.execute(
                sa.update(PUBLICATION_RELEASES)
                .where(PUBLICATION_RELEASES.c.id == r_row["id"])
                .values(render_profile_snapshot=r_profile)
            )


def upgrade() -> None:
    _update_profiles({
        "vietnam_safar": {
            "investmentSurface": "#edf5f1",
            "investmentText": "#11130f",
        },
        "capella_travel": {
            "investmentSurface": "#fbf7ee",
            "investmentText": "#171511",
        },
        "selvara": {
            "storyContrast": "#524018",
            "investmentSurface": "#f6f2ea",
            "investmentText": "#11130f",
        },
    })


def downgrade() -> None:
    _update_profiles({
        "vietnam_safar": {
            "investmentSurface": "#0d3f32",
            "investmentText": "#ffffff",
        },
        "capella_travel": {
            "investmentSurface": "#333333",
            "investmentText": "#ffffff",
        },
        "selvara": {
            "storyContrast": "#17412e",
            "investmentSurface": "#0d3f32",
            "investmentText": "#ffffff",
        },
    })
