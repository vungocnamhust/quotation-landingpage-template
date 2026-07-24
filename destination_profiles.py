import os
import hashlib
from typing import Dict, Any, List

DESTINATION_PROFILES = {
    # Vietnam
    "ha-noi": {
        "label": "Hanoi",
        "archetype": "urban",
        "restBias": 0.15,
        "mood": "layered streets, shaded boulevards and a measured urban rhythm",
        "chapterLine": "A gentle beginning among courtyards, old streets and quiet rituals.",
    },
    "ninh-binh": {
        "label": "Ninh Binh",
        "archetype": "nature",
        "restBias": 0.42,
        "mood": "river landscapes, limestone forms and a slower rural pace",
        "chapterLine": "The journey begins to breathe more slowly between water and stone.",
    },
    "quang-ninh": {
        "label": "Ha Long Bay",
        "archetype": "scenic",
        "restBias": 0.65,
        "mood": "water, sky and sculpted limestone",
        "chapterLine": "A brief chapter held between water, sky and stone.",
    },
    "lao-cai": {
        "label": "Sapa",
        "archetype": "scenic",
        "restBias": 0.35,
        "mood": "mountain air, layered valleys and an unhurried horizon",
        "chapterLine": "Cooler air and wider horizons deepen the northern chapter.",
    },
    "da-nang": {
        "label": "Da Nang",
        "archetype": "coastal",
        "restBias": 0.72,
        "mood": "open coast, softer light and room to pause",
        "chapterLine": "The centre of the journey opens towards the sea.",
    },
    "quang-nam": {
        "label": "Hoi An",
        "archetype": "heritage",
        "restBias": 0.28,
        "mood": "lantern light, preserved streets and living craft traditions",
        "chapterLine": "A smaller town allows the cultural detail to come closer.",
    },
    "ho-chi-minh": {
        "label": "Ho Chi Minh City",
        "archetype": "urban",
        "restBias": 0.12,
        "mood": "southern energy, layered history and contemporary city life",
        "chapterLine": "The final chapter gathers the pace and contrasts of the south.",
    },
    "thua-thien-hue": {
        "label": "Hue",
        "archetype": "heritage",
        "restBias": 0.30,
        "mood": "imperial history, quiet rivers and slow passing time",
        "chapterLine": "An interlude shaped by dynastic history and quiet elegance.",
    },
    "mekong": {
        "label": "Mekong Delta",
        "archetype": "nature",
        "restBias": 0.45,
        "mood": "winding waterways, floating life and green abundance",
        "chapterLine": "Moving with the slow, deliberate pulse of the delta.",
    },
    "khanh-hoa": {
        "label": "Nha Trang",
        "archetype": "coastal",
        "restBias": 0.8,
        "mood": "vast bays, clear waters and coastal tranquility",
        "chapterLine": "A long pause where the coast meets the open sea.",
    },
    # Cambodia
    "siem-reap": {
        "label": "Siem Reap",
        "archetype": "heritage",
        "restBias": 0.25,
        "mood": "ancient stone, jungle ruins and spiritual scale",
        "chapterLine": "Stepping into a landscape defined by empires of stone.",
    },
    "phnom-penh": {
        "label": "Phnom Penh",
        "archetype": "urban",
        "restBias": 0.20,
        "mood": "river confluences, modern energy and deep history",
        "chapterLine": "The river capital reflects both resilience and revival.",
    },
    # Laos
    "luang-prabang": {
        "label": "Luang Prabang",
        "archetype": "heritage",
        "restBias": 0.60,
        "mood": "monastic rhythms, misty mornings and spiritual quiet",
        "chapterLine": "Time slows down along the spiritual heart of the Mekong.",
    },
    "vientiane": {
        "label": "Vientiane",
        "archetype": "urban",
        "restBias": 0.40,
        "mood": "relaxed avenues, golden stupas and quiet riverbanks",
        "chapterLine": "A gentle capital where life unfolds at an unhurried pace.",
    },
    # Thailand
    "bangkok": {
        "label": "Bangkok",
        "archetype": "urban",
        "restBias": 0.10,
        "mood": "vibrant street life, ornate temples and flowing energy",
        "chapterLine": "A vibrant immersion into layers of devotion and modernity.",
    },
    "chiang-mai": {
        "label": "Chiang Mai",
        "archetype": "cultural",
        "restBias": 0.40,
        "mood": "mountain serenity, ancient walls and artisanal craft",
        "chapterLine": "A retreat into the craft and calm of the northern mountains.",
    },
    "phuket": {
        "label": "Phuket",
        "archetype": "coastal",
        "restBias": 0.70,
        "mood": "turquoise waters, soft sands and tropical warmth",
        "chapterLine": "An open horizon wrapped in coastal warmth.",
    },
    "default": {
        "label": "Destination",
        "archetype": "general",
        "restBias": 0.25,
        "mood": "a distinct local rhythm and a new sense of place",
        "chapterLine": "A new chapter unfolds at a measured pace.",
    }
}

SOFT_TRANSITIONS = {
    "da-nang→quang-nam",
    "quang-nam→da-nang",
    "ha-noi→ninh-binh",
    "ninh-binh→quang-ninh"
}

def stable_index(seed: str, length: int) -> int:
    if not length:
        return 0
    hash_object = hashlib.md5(seed.encode())
    return int(hash_object.hexdigest(), 16) % length

def get_profile(slug: str) -> Dict[str, Any]:
    if not slug:
        return DESTINATION_PROFILES["default"]
    
    slug_key = slug.lower().strip()
    profile = DESTINATION_PROFILES.get(slug_key, DESTINATION_PROFILES["default"]).copy()
    if profile.get("label") == "Destination" and slug_key != "default":
        # Capitalize slug if no specific profile exists
        profile["label"] = slug_key.replace("-", " ").title()
        
    profile["slug"] = slug_key
    return profile

def get_available_images_for_destination(slug: str, base_url: str = "") -> List[str]:
    """
    Looks for images in assets/<slug>/hero/ and assets/<slug>/.
    Returns a list of image URLs, skipping hero1 when hero2+ exist.
    """
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    available_images = []
    seen = set()
    
    if slug:
        hero_dir = os.path.join(assets_dir, slug, "hero")
        if os.path.exists(hero_dir) and os.path.isdir(hero_dir):
            hero_files = [
                f for f in sorted(os.listdir(hero_dir))
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            ]
            for f in hero_files:
                rel_path = f"/assets/{slug}/hero/{f}"
                if rel_path not in seen:
                    available_images.append(rel_path)
                    seen.add(rel_path)
                        
        dest_dir = os.path.join(assets_dir, slug)
        if os.path.exists(dest_dir) and os.path.isdir(dest_dir):
            for f in sorted(os.listdir(dest_dir)):
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    rel_path = f"/assets/{slug}/{f}"
                    if rel_path not in seen:
                        available_images.append(rel_path)
                        seen.add(rel_path)

    if base_url and available_images:
        available_images = [f"{base_url}{img}" for img in available_images]

    return available_images

def get_layout_images_for_destination(slug: str, seed: str, base_url: str = "") -> Dict[str, str]:
    """
    Looks for images in assets/<slug>/hero/ and assets/<slug>/.
    Returns a dict with distinct 'hero', 'small-1', and 'small-2' image URLs.
    """
    available_images = get_available_images_for_destination(slug, base_url=base_url)
    if not available_images:
        return {
            "hero": "",
            "small-1": "",
            "small-2": "",
        }
        
    offset_hero = stable_index(f"{seed}-hero", len(available_images))
    offset_s1 = stable_index(f"{seed}-small-1", len(available_images))
    offset_s2 = stable_index(f"{seed}-small-2", len(available_images))
    
    # Ensure distinct images for hero, small-1, small-2 when multiple images are available
    if len(available_images) > 1:
        if offset_s1 == offset_hero:
            offset_s1 = (offset_hero + 1) % len(available_images)
        if offset_s2 == offset_hero or offset_s2 == offset_s1:
            offset_s2 = (offset_s1 + 1) % len(available_images)
            if offset_s2 == offset_hero and len(available_images) > 2:
                offset_s2 = (offset_s2 + 1) % len(available_images)
        
    return {
        "hero": f"{base_url}{available_images[offset_hero]}",
        "small-1": f"{base_url}{available_images[offset_s1]}",
        "small-2": f"{base_url}{available_images[offset_s2]}",
    }
