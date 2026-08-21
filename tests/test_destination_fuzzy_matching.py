"""Unit tests for Destination DB Fuzzy & Token Substring Matching and media_prefix."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from db.models.destination import DestinationCatalog, DestinationAlias
from repositories.destination_repository import DestinationRepository
from services.media_locations import destination_location


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
async def test_destination_crud_with_media_prefix(async_session: AsyncSession):
    repo = DestinationRepository(async_session)

    # 1. Create with custom media_prefix
    created = await repo.create(
        destination_id="dst_ninh_binh",
        canonical_name="Ninh Binh",
        slug="ninh-binh",
        aliases=["Trang An", "Tam Coc", "Hang Mua"],
        country_slug="vietnam",
        region_slug="north",
        province_slug="ninh-binh",
        latitude=20.2539,
        longitude=105.9750,
        media_prefix="destination/vietnam/north/ninh-binh",
    )
    assert created.id == "dst_ninh_binh"
    assert created.media_prefix == "destination/vietnam/north/ninh-binh"

    # 2. Test destination_location uses custom media_prefix
    loc = destination_location(created)
    assert loc.leaf_prefix == "destination/vietnam/north/ninh-binh"

    # 3. Update media_prefix
    updated = await repo.update(
        created,
        canonical_name="Ninh Binh Province",
        aliases=["Trang An", "Tam Coc", "Hang Mua", "Bich Dong"],
        country_slug="vietnam",
        region_slug="north",
        province_slug="ninh-binh",
        latitude=20.2539,
        longitude=105.9750,
        media_prefix="destination/custom/nb-assets",
    )
    assert updated.media_prefix == "destination/custom/nb-assets"
    loc_updated = destination_location(updated)
    assert loc_updated.leaf_prefix == "destination/custom/nb-assets"


@pytest.mark.anyio
async def test_destination_layer3_fuzzy_and_substring_matching(async_session: AsyncSession):
    repo = DestinationRepository(async_session)

    # Create destinations in DB
    await repo.create(
        destination_id="dst_ninh_binh",
        canonical_name="Ninh Binh",
        slug="ninh-binh",
        aliases=["Trang An", "Tam Coc", "Hang Mua", "Bich Dong"],
        country_slug="vietnam",
        region_slug="north",
        province_slug="ninh-binh",
        latitude=20.2539,
        longitude=105.9750,
    )

    await repo.create(
        destination_id="dst_phong_nha",
        canonical_name="Phong Nha",
        slug="phong-nha",
        aliases=["Hang En", "Son Doong", "Ke Bang", "Hang Va"],
        country_slug="vietnam",
        region_slug="central",
        province_slug="quang-binh",
        latitude=17.5833,
        longitude=106.2833,
    )

    # Test 1: Multi-word phrase containment in a long sentence
    resolved_1 = await repo.resolve("Tour 1 ngay tham quan Trang An Ninh Binh tuyet dep")
    assert resolved_1 is not None
    assert resolved_1.id == "dst_ninh_binh"

    # Test 2: Phrase match with diacritics
    resolved_2 = await repo.resolve("Khám phá Hang Én 3 ngày 2 đêm cùng chuyên gia")
    assert resolved_2 is not None
    assert resolved_2.id == "dst_phong_nha"

    # Test 3: Substring alias match
    resolved_3 = await repo.resolve("Check in Tam Coc - Bich Dong")
    assert resolved_3 is not None
    assert resolved_3.id == "dst_ninh_binh"

    # Test 4: Son Doong expedition
    resolved_4 = await repo.resolve("Thám hiểm Sơn Đoòng")
    assert resolved_4 is not None
    assert resolved_4.id == "dst_phong_nha"

    # Test 5: Completely unrelated text -> returns None (no false positives)
    resolved_none = await repo.resolve("Một địa điểm ngẫu nhiên không có trong danh mục")
    assert resolved_none is None
