from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.travel_designer import TravelDesignerBrandDefault, TravelDesignerProfile


def normalize_designer_email(email: str) -> str:
    return (email or "").strip().lower()


class TravelDesignerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_profiles(
        self,
        *,
        active_only: bool | None = True,
        search: str = "",
        limit: int = 100,
    ) -> list[TravelDesignerProfile]:
        stmt = select(TravelDesignerProfile).order_by(TravelDesignerProfile.name.asc(), TravelDesignerProfile.id.asc())
        if active_only is True:
            stmt = stmt.where(TravelDesignerProfile.is_active.is_(True))
        elif active_only is False:
            stmt = stmt.where(TravelDesignerProfile.is_active.is_(False))
        term = (search or "").strip()
        if term:
            pattern = f"%{term}%"
            stmt = stmt.where(or_(TravelDesignerProfile.name.ilike(pattern), TravelDesignerProfile.email.ilike(pattern)))
        stmt = stmt.limit(max(1, min(limit, 200)))
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def get_profile(self, profile_id: str) -> TravelDesignerProfile | None:
        return await self.session.get(TravelDesignerProfile, profile_id)

    async def get_by_email(self, email: str) -> TravelDesignerProfile | None:
        normalized = normalize_designer_email(email)
        if not normalized:
            return None
        return await self.session.scalar(
            select(TravelDesignerProfile).where(TravelDesignerProfile.email == normalized)
        )

    async def get_active_by_email(self, email: str) -> TravelDesignerProfile | None:
        normalized = normalize_designer_email(email)
        if not normalized:
            return None
        profile = await self.get_by_email(normalized)
        return profile if profile is not None and profile.is_active else None

    async def create_profile(
        self,
        *,
        profile_id: str,
        email: str,
        name: str,
        phone: str = "",
        image_asset_id: str | None = None,
        image_url: str | None = None,
        storage_slug: str | None = None,
        image_r2_key: str | None = None,
        signature_initial: str | None = None,
    ) -> TravelDesignerProfile:
        profile = TravelDesignerProfile(
            id=profile_id,
            email=normalize_designer_email(email),
            name=name.strip(),
            phone=(phone or "").strip(),
            image_asset_id=image_asset_id,
            image_url=image_url,
            storage_slug=storage_slug,
            image_r2_key=image_r2_key,
            signature_initial=(signature_initial or "").strip() or None,
            is_active=True,
        )
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def update_profile(
        self,
        profile: TravelDesignerProfile,
        *,
        email: str,
        name: str,
        phone: str = "",
        image_asset_id: str | None = None,
        image_url: str | None = None,
        storage_slug: str | None = None,
        image_r2_key: str | None = None,
        signature_initial: str | None = None,
    ) -> TravelDesignerProfile:
        profile.email = normalize_designer_email(email)
        profile.name = name.strip()
        profile.phone = (phone or "").strip()
        profile.image_asset_id = image_asset_id or None
        profile.image_url = image_url or None
        profile.storage_slug = storage_slug or profile.storage_slug
        profile.image_r2_key = image_r2_key or None
        profile.signature_initial = (signature_initial or "").strip() or None
        await self.session.flush()
        return profile

    async def set_status(self, profile: TravelDesignerProfile, *, is_active: bool) -> TravelDesignerProfile:
        profile.is_active = is_active
        await self.session.flush()
        return profile

    async def get_brand_default(self, brand_id: str) -> TravelDesignerProfile | None:
        stmt = (
            select(TravelDesignerProfile)
            .join(
                TravelDesignerBrandDefault,
                TravelDesignerBrandDefault.designer_profile_id == TravelDesignerProfile.id,
            )
            .where(
                TravelDesignerBrandDefault.brand_id == brand_id,
                TravelDesignerProfile.is_active.is_(True),
            )
        )
        return await self.session.scalar(stmt)

    async def set_brand_default(self, *, brand_id: str, profile_id: str) -> TravelDesignerBrandDefault:
        profile = await self.get_profile(profile_id)
        if profile is None or not profile.is_active:
            raise ValueError("Travel Designer profile is not active")
        existing = await self.session.get(TravelDesignerBrandDefault, brand_id)
        if existing is None:
            existing = TravelDesignerBrandDefault(brand_id=brand_id, designer_profile_id=profile_id)
            self.session.add(existing)
        else:
            existing.designer_profile_id = profile_id
        await self.session.flush()
        return existing


def serialize_travel_designer(profile: TravelDesignerProfile | dict[str, Any] | None) -> dict[str, Any]:
    if profile is None:
        return {}
    if isinstance(profile, dict):
        return {
            "id": profile.get("id") or "",
            "name": profile.get("name") or "",
            "email": profile.get("email") or "",
            "phone": profile.get("phone") or "",
            "signatureInitial": profile.get("signatureInitial") or profile.get("signature_initial") or None,
            "imageAssetId": profile.get("imageAssetId") or profile.get("image_asset_id") or "",
            "imageR2Key": profile.get("imageR2Key") or profile.get("image_r2_key") or "",
            "imageUrl": profile.get("imageUrl") or profile.get("image_url") or "",
            "isActive": profile.get("isActive", profile.get("is_active", True)),
        }
    return {
        "id": profile.id,
        "name": profile.name,
        "email": profile.email,
        "phone": profile.phone or "",
        "signatureInitial": profile.signature_initial or None,
        "imageAssetId": profile.image_asset_id or "",
        "imageR2Key": profile.image_r2_key or "",
        "imageUrl": profile.image_url or "",
        "isActive": profile.is_active,
    }


def apply_travel_designer_snapshot(document: dict[str, Any], profile: dict[str, Any] | None) -> None:
    """Apply only profile-owned designer fields, preserving editorial copy."""
    designer = document.setdefault("designer", {})
    profile_fields = ("profileId", "name", "email", "phone", "image", "signatureInitial")
    if profile is None:
        for field in profile_fields:
            designer.pop(field, None)
        return
    designer.update(
        {
            "profileId": profile["id"],
            "name": profile.get("name") or "",
            "email": profile.get("email") or "",
            "phone": profile.get("phone") or "",
            "signatureInitial": profile.get("signatureInitial") or None,
            "image": {
                "assetId": profile.get("imageAssetId") or "",
                "r2Key": profile.get("imageR2Key") or "",
                "url": profile.get("imageUrl") or "",
                "status": "ready" if (profile.get("imageAssetId") or profile.get("imageR2Key") or profile.get("imageUrl")) else "empty",
            },
        }
    )

