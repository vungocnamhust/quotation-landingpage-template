import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from db.models.media_library import MediaLibraryObject
from main import _apply_missing_media_defaults
from repositories.destination_repository import DestinationRepository
from repositories.media_library_repository import MediaLibraryRepository


@pytest.fixture
async def async_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.anyio
async def test_apply_missing_media_defaults_uses_db_destination_prefix(async_session: AsyncSession):
    dest_repo = DestinationRepository(async_session)

    # 1. Create a custom destination in DB with a custom media_prefix
    await dest_repo.create(
        destination_id="dst_buon_ma_thuot",
        canonical_name="Buon Ma Thuot",
        slug="dak-lak",
        country_slug="vietnam",
        region_slug="central-highlands",
        province_slug="dak-lak",
        latitude=12.6667,
        longitude=108.0500,
        aliases=["bmt", "buon ma thuot", "đắk lắk", "daklak"],
        media_prefix="destination/custom-dak-lak-folder",
    )

    # 2. Seed media items in active candidates
    async_session.add(
        MediaLibraryObject(
            bucket="quotation-media",
            r2_key="destination/custom-dak-lak-folder/coffee_plantation_hero.jpg",
            parent_prefix="destination/custom-dak-lak-folder",
            file_name="coffee_plantation_hero.jpg",
            size_bytes=1024,
            content_type="image/jpeg",
            width=1600,
            height=900,
            preview_status="ready",
            is_active=True,
        )
    )
    async_session.add(
        MediaLibraryObject(
            bucket="quotation-media",
            r2_key="destination/custom-dak-lak-folder/dray_nur_waterfall.jpg",
            parent_prefix="destination/custom-dak-lak-folder",
            file_name="dray_nur_waterfall.jpg",
            size_bytes=1024,
            content_type="image/jpeg",
            width=1600,
            height=900,
            preview_status="ready",
            is_active=True,
        )
    )
    await async_session.commit()

    # 3. Create a document with a day having raw destination name
    document = {
        "itinerary": {
            "days": [
                {
                    "day_number": 1,
                    "destination": "Buon Ma Thuot",
                    "images": {"carousel": []},
                }
            ]
        },
        "assets": {},
        "stays": {"hotels": []},
    }

    # 4. Run _apply_missing_media_defaults
    await _apply_missing_media_defaults(
        session=async_session,
        document=document,
        quotation_id="quo_test_prefix",
        lang="en",
    )

    # 5. Verify that destinationRef was pre-hydrated with custom media_prefix and string defaultMediaPrefix
    day1 = document["itinerary"]["days"][0]
    assert day1["destinationRef"] is not None
    assert day1["destinationRef"]["slug"] == "dak-lak"
    assert day1["destinationRef"]["mediaPrefix"] == "destination/custom-dak-lak-folder"
    assert isinstance(day1["destinationRef"]["defaultMediaPrefix"], str)

    # 6. Verify that carousel images were picked from the custom dak-lak folder
    carousel = day1["images"]["carousel"]
    assert len(carousel) >= 1
    for img in carousel:
        assert img["r2Key"].startswith("destination/custom-dak-lak-folder/")

    # 7. Verify document is JSON serializable
    import json
    json_str = json.dumps(document)
    assert "destination/custom-dak-lak-folder" in json_str
