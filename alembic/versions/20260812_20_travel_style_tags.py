"""add travel style tags table and seed initial taxonomy"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision = "20260812_20"
down_revision = "20260810_19"
branch_labels = None
depends_on = None

travel_style_tags = table(
    "travel_style_tags",
    column("id", sa.String),
    column("category", sa.String),
    column("name_en", sa.String),
    column("name_vi", sa.String),
    column("slug", sa.String),
    column("is_active", sa.Boolean),
    column("display_order", sa.Integer),
)

SEED_TAGS = [
    # Group Composition
    {"id": "tag_solo", "category": "group_composition", "name_en": "Solo Traveler", "name_vi": "Du lịch cá nhân", "slug": "solo-traveler", "display_order": 1},
    {"id": "tag_couple", "category": "group_composition", "name_en": "Couple / Romantic", "name_vi": "Cặp đôi", "slug": "couple", "display_order": 2},
    {"id": "tag_family", "category": "group_composition", "name_en": "Family", "name_vi": "Gia đình", "slug": "family", "display_order": 3},
    {"id": "tag_friends", "category": "group_composition", "name_en": "Friends Group", "name_vi": "Nhóm bạn bè", "slug": "friends-group", "display_order": 4},
    {"id": "tag_corporate", "category": "group_composition", "name_en": "Corporate Group", "name_vi": "Đoàn công ty", "slug": "corporate-group", "display_order": 5},

    # Tour Type
    {"id": "tag_private_tour", "category": "tour_type", "name_en": "Private Tour", "name_vi": "Tour riêng cao cấp", "slug": "private-tour", "display_order": 1},
    {"id": "tag_small_group_tour", "category": "tour_type", "name_en": "Small Group Tour", "name_vi": "Tour ghép đoàn nhỏ", "slug": "small-group-tour", "display_order": 2},
    {"id": "tag_shared_tour", "category": "tour_type", "name_en": "Shared Tour", "name_vi": "Tour chia sẻ", "slug": "shared-tour", "display_order": 3},
    {"id": "tag_fit", "category": "tour_type", "name_en": "FIT / Self-Guided", "name_vi": "Free Independent Traveler", "slug": "fit-self-guided", "display_order": 4},
    {"id": "tag_tailor_made", "category": "tour_type", "name_en": "Tailor-Made", "name_vi": "Thiết kế riêng theo yêu cầu", "slug": "tailor-made", "display_order": 5},

    # Purpose & Theme
    {"id": "tag_honeymoon", "category": "purpose", "name_en": "Honeymoon & Getaway", "name_vi": "Tuần trăng mật", "slug": "honeymoon", "display_order": 1},
    {"id": "tag_mice", "category": "purpose", "name_en": "MICE (Corporate / Incentive)", "name_vi": "Hội họp & Khen thưởng", "slug": "mice", "display_order": 2},
    {"id": "tag_leisure", "category": "purpose", "name_en": "Leisure & Relaxation", "name_vi": "Nghỉ dưỡng & Thư giãn", "slug": "leisure-relaxation", "display_order": 3},
    {"id": "tag_wellness", "category": "purpose", "name_en": "Wellness & Retreat", "name_vi": "Sức khỏe & Thiền", "slug": "wellness-retreat", "display_order": 4},
    {"id": "tag_celebration", "category": "purpose", "name_en": "Celebration & Anniversary", "name_vi": "Lễ kỷ niệm", "slug": "celebration-anniversary", "display_order": 5},

    # Interest & Experience
    {"id": "tag_cultural", "category": "interest_experience", "name_en": "Cultural & Heritage", "name_vi": "Văn hóa & Di sản", "slug": "cultural-heritage", "display_order": 1},
    {"id": "tag_war_history", "category": "interest_experience", "name_en": "War Heritage & Historical", "name_vi": "Lịch sử & Di tích chiến tranh", "slug": "war-heritage-historical", "display_order": 2},
    {"id": "tag_ecotourism", "category": "interest_experience", "name_en": "Ecotourism & Nature", "name_vi": "Sinh thái & Tự nhiên", "slug": "ecotourism-nature", "display_order": 3},
    {"id": "tag_wildlife", "category": "interest_experience", "name_en": "Wildlife & Birdwatching", "name_vi": "Động vật hoang dã & Xem chim", "slug": "wildlife-birdwatching", "display_order": 4},
    {"id": "tag_adventure", "category": "interest_experience", "name_en": "Adventure & Trekking", "name_vi": "Thám hiểm & Leo núi", "slug": "adventure-trekking", "display_order": 5},
    {"id": "tag_culinary", "category": "interest_experience", "name_en": "Culinary & Gastronomy", "name_vi": "Ẩm thực & Vị giác", "slug": "culinary-gastronomy", "display_order": 6},
    {"id": "tag_photography", "category": "interest_experience", "name_en": "Photography & Scenic", "name_vi": "Nhiếp ảnh & Cảnh quan", "slug": "photography-scenic", "display_order": 7},
    {"id": "tag_luxury", "category": "interest_experience", "name_en": "Luxury & Exclusive", "name_vi": "Sang trọng & Trải nghiệm độc quyền", "slug": "luxury-exclusive", "display_order": 8},
]


def upgrade() -> None:
    op.create_table(
        "travel_style_tags",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("name_en", sa.String(128), nullable=False),
        sa.Column("name_vi", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_travel_style_tags_category_order", "travel_style_tags", ["category", "display_order"], unique=False)
    op.create_index("ix_travel_style_tags_slug", "travel_style_tags", ["slug"], unique=False)

    # Seed data
    op.bulk_insert(
        travel_style_tags,
        [
            {**item, "is_active": True}
            for item in SEED_TAGS
        ]
    )


def downgrade() -> None:
    op.drop_index("ix_travel_style_tags_slug", table_name="travel_style_tags")
    op.drop_index("ix_travel_style_tags_category_order", table_name="travel_style_tags")
    op.drop_table("travel_style_tags")
