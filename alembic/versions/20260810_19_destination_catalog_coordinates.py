"""Add Facts-owned map anchors to the destination catalogue."""

from alembic import op
import sqlalchemy as sa


revision = "20260810_19"
down_revision = "20260810_18"
branch_labels = None
depends_on = None


_COORDINATES = {
    "ha-noi": (21.0285, 105.8542),
    "quang-ninh": (20.9599, 107.0436),
    "lao-cai": (22.3364, 103.8438),
    "da-nang": (16.0544, 108.2022),
    "quang-nam": (15.8801, 108.3380),
    "lam-dong": (11.9404, 108.4583),
    "ho-chi-minh": (10.8231, 106.6297),
    "khanh-hoa": (12.2388, 109.1967),
    "ninh-binh": (20.2539, 105.9750),
    "thua-thien-hue": (16.4637, 107.5909),
    "kien-giang": (10.2899, 103.9840),
    "binh-thuan": (10.9333, 108.1000),
    "can-tho": (10.0401, 105.7882),
    "mekong": (10.2435, 106.3756),
    "ha-giang": (22.8233, 104.9836),
    "nghe-an": (18.6736, 105.6811),
    "quang-binh": (17.4833, 106.6000),
    "hai-phong": (20.8449, 106.6881),
    "dak-lak": (12.6667, 108.0500),
    "gia-lai": (13.9833, 108.0000),
    "kon-tum": (14.3500, 108.0000),
    "ba-ria-vung-tau": (10.4114, 107.1363),
    "thanh-hoa": (19.8075, 105.7764),
    "phu-yen": (13.0881, 109.3025),
    "binh-dinh": (13.7753, 109.2294),
    "dien-bien": (21.3833, 103.0167),
    "son-la": (21.3333, 103.9167),
    "lai-chau": (22.4000, 103.4500),
    "yen-bai": (21.7000, 104.8667),
    "hoa-binh": (20.8167, 105.3333),
    "lang-son": (21.8500, 106.7500),
    "dong-nai": (10.9574, 106.8427),
    "binh-duong": (11.0000, 106.6667),
    "tien-giang": (10.3592, 106.3653),
    "dong-thap": (10.4500, 105.6333),
    "vinh-long": (10.2500, 105.9667),
    "an-giang": (10.3833, 105.4333),
    "cao-bang": (22.6667, 106.2500),
}


def upgrade() -> None:
    op.add_column("destination_catalog", sa.Column("latitude", sa.Numeric(8, 5), nullable=True))
    op.add_column("destination_catalog", sa.Column("longitude", sa.Numeric(8, 5), nullable=True))
    op.create_check_constraint("ck_destination_catalog_latitude_range", "destination_catalog", "latitude IS NULL OR latitude BETWEEN -90 AND 90")
    op.create_check_constraint("ck_destination_catalog_longitude_range", "destination_catalog", "longitude IS NULL OR longitude BETWEEN -180 AND 180")
    connection = op.get_bind()
    for slug, (latitude, longitude) in _COORDINATES.items():
        connection.execute(
            sa.text("UPDATE destination_catalog SET latitude = :latitude, longitude = :longitude WHERE slug = :slug AND latitude IS NULL AND longitude IS NULL"),
            {"slug": slug, "latitude": latitude, "longitude": longitude},
        )


def downgrade() -> None:
    op.drop_constraint("ck_destination_catalog_longitude_range", "destination_catalog", type_="check")
    op.drop_constraint("ck_destination_catalog_latitude_range", "destination_catalog", type_="check")
    op.drop_column("destination_catalog", "longitude")
    op.drop_column("destination_catalog", "latitude")
