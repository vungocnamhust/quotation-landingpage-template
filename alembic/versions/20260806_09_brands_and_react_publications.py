"""brands as V2 source of truth and React publication releases

Revision ID: 20260806_09
Revises: 20260806_08
"""
from alembic import op
import sqlalchemy as sa


revision = "20260806_09"
down_revision = "20260806_08"
branch_labels = None
depends_on = None


def _profile(*, name: str, logo: str, palette: dict[str, str], seller: dict[str, str]) -> dict:
    return {
        "displayName": name,
        "logoUrl": logo,
        "palette": palette,
        "radii": {"card": "0.5rem", "button": "0.375rem", "frame": "0.625rem", "pill": "999px"},
        "seller": seller,
        "themeId": "brochure",
        "layoutVersion": 1,
    }


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False, unique=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("logo_asset_key", sa.String(length=512), nullable=True),
        sa.Column("seller_profile", sa.JSON(), nullable=False),
        sa.Column("render_profile", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_brands_hostname", "brands", ["hostname"], unique=True)
    op.bulk_insert(
        sa.table(
            "brands",
            sa.column("id", sa.String), sa.column("display_name", sa.String), sa.column("hostname", sa.String),
            sa.column("status", sa.String), sa.column("logo_asset_key", sa.String), sa.column("seller_profile", sa.JSON), sa.column("render_profile", sa.JSON),
        ),
        [
            {
                "id": "vietnam_safar", "display_name": "Vietnam Safar", "hostname": "journeys.vietnamsafar.vn", "status": "active",
                "logo_asset_key": "/assets/brands/vietnam_safar.png", "seller_profile": {"email": "hello@vietnamsafar.vn", "phone": "", "whatsapp": ""},
                "render_profile": _profile(name="Vietnam Safar", logo="/assets/brands/vietnam_safar.png", seller={"email": "hello@vietnamsafar.vn", "phone": "", "whatsapp": ""}, palette={"canvas": "#f9f6f0", "paper": "#fffaf1", "ink": "#11130f", "mutedInk": "#706a5d", "accent": "#b7894b", "accentAlt": "#17412e", "contrast": "#17412e", "onContrast": "#ffffff", "focus": "#b7894b"}),
            },
            {
                "id": "capella_travel", "display_name": "Capella Travel", "hostname": "journeys.capellatravel.com", "status": "active",
                "logo_asset_key": "/assets/brands/capella_travel.png", "seller_profile": {"email": "hello@capellatravel.com", "phone": "", "whatsapp": ""},
                "render_profile": _profile(name="Capella Travel", logo="/assets/brands/capella_travel.png", seller={"email": "hello@capellatravel.com", "phone": "", "whatsapp": ""}, palette={"canvas": "#f8f5ef", "paper": "#ffffff", "ink": "#1d1d1b", "mutedInk": "#67635b", "accent": "#cba135", "accentAlt": "#333333", "contrast": "#333333", "onContrast": "#ffffff", "focus": "#cba135"}),
            },
            {
                "id": "selvara", "display_name": "Selvara Journeys", "hostname": "my.selvarajourneys.com", "status": "active",
                "logo_asset_key": "/assets/brands/selvara.svg", "seller_profile": {"email": "hello@selvarajourneys.com", "phone": "", "whatsapp": ""},
                "render_profile": _profile(name="Selvara Journeys", logo="/assets/brands/selvara.svg", seller={"email": "hello@selvarajourneys.com", "phone": "", "whatsapp": ""}, palette={"canvas": "#f7f5ef", "paper": "#ffffff", "ink": "#283027", "mutedInk": "#667064", "accent": "#a98338", "accentAlt": "#4f5d4e", "contrast": "#4f5d4e", "onContrast": "#ffffff", "focus": "#a98338"}),
            },
        ],
    )
    op.create_table(
        "publication_targets",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("quotation_id", sa.String(length=64), sa.ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_id", sa.String(length=64), sa.ForeignKey("brands.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("locale", sa.String(length=5), nullable=False),
        sa.Column("public_slug", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("active_release_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("brand_id", "locale", "public_slug", name="uq_publication_targets_brand_locale_slug"),
        sa.UniqueConstraint("quotation_id", "brand_id", "locale", name="uq_publication_targets_quotation_brand_locale"),
    )
    op.create_index("ix_publication_targets_quotation", "publication_targets", ["quotation_id"])
    op.create_table(
        "publication_releases",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("target_id", sa.String(length=64), sa.ForeignKey("publication_targets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("release_number", sa.Integer(), nullable=False),
        sa.Column("document_revision", sa.Integer(), nullable=False),
        sa.Column("render_profile_snapshot", sa.JSON(), nullable=False),
        sa.Column("asset_manifest", sa.JSON(), nullable=False),
        sa.Column("pdf_r2_key", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="staging"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("target_id", "release_number", name="uq_publication_releases_target_number"),
    )
    op.create_index("ix_publication_releases_target_current", "publication_releases", ["target_id", "is_current"])
    # Existing rows in quotation_publications are V2 canonical publications. They
    # get a deterministic opaque target and redirect to React; their old R2 HTML
    # is intentionally not referenced by the new release.
    op.execute("""
        UPDATE quotations
        SET template_name = 'quote-generator'
        WHERE id IN (SELECT DISTINCT quotation_id FROM quotation_publications)
    """)
    op.execute("""
        WITH latest AS (
          SELECT DISTINCT ON (p.quotation_id, p.lang)
            p.quotation_id, p.lang, p.document_revision, q.brand_id
          FROM quotation_publications p
          JOIN quotations q ON q.id = p.quotation_id
          JOIN brands b ON b.id = q.brand_id
          ORDER BY p.quotation_id, p.lang, p.version DESC, p.created_at DESC
        )
        INSERT INTO publication_targets (id, quotation_id, brand_id, locale, public_slug, status, active_release_id)
        SELECT
          'pt_mig_' || substr(md5(quotation_id || ':' || brand_id || ':' || lang), 1, 24),
          quotation_id, brand_id, lang,
          'q-' || substr(md5('slug:' || quotation_id || ':' || brand_id || ':' || lang), 1, 20),
          'published',
          'pr_mig_' || substr(md5(quotation_id || ':' || brand_id || ':' || lang), 1, 24)
        FROM latest
    """)
    op.execute("""
        WITH latest AS (
          SELECT DISTINCT ON (p.quotation_id, p.lang)
            p.quotation_id, p.lang, p.document_revision, q.brand_id
          FROM quotation_publications p
          JOIN quotations q ON q.id = p.quotation_id
          JOIN brands b ON b.id = q.brand_id
          ORDER BY p.quotation_id, p.lang, p.version DESC, p.created_at DESC
        )
        INSERT INTO publication_releases (id, target_id, release_number, document_revision, render_profile_snapshot, asset_manifest, status, is_current, published_at)
        SELECT
          'pr_mig_' || substr(md5(l.quotation_id || ':' || l.brand_id || ':' || l.lang), 1, 24),
          'pt_mig_' || substr(md5(l.quotation_id || ':' || l.brand_id || ':' || l.lang), 1, 24),
          1, l.document_revision,
          (b.render_profile::jsonb || jsonb_build_object('id', b.id, 'displayName', b.display_name, 'hostname', b.hostname, 'logoUrl', COALESCE(b.logo_asset_key, ''), 'sellerProfile', b.seller_profile::jsonb))::json,
          '{}'::jsonb, 'published', true, now()
        FROM latest l JOIN brands b ON b.id = l.brand_id
    """)


def downgrade() -> None:
    op.drop_index("ix_publication_releases_target_current", table_name="publication_releases")
    op.drop_table("publication_releases")
    op.drop_index("ix_publication_targets_quotation", table_name="publication_targets")
    op.drop_table("publication_targets")
    op.drop_index("ix_brands_hostname", table_name="brands")
    op.drop_table("brands")
