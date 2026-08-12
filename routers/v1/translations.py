"""V1 Translation routes."""
from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix="/api/v1", tags=["translations"])


class TranslateBlockRequest(BaseModel):
    text: str
    target_lang: str
    source_lang: str = "en"


def _get_helpers():
    import main
    return main


@router.post("/translate-block")
async def translate_block_endpoint(payload: TranslateBlockRequest):
    """Translates a single block of text into target language."""
    if payload.target_lang not in ("en", "vi", "ar"):
        raise HTTPException(status_code=400, detail="Unsupported language")
    
    if not payload.text.strip():
        return {"translated_text": ""}

    from pydantic_ai import Agent
    import llm_client
    
    target_lang_name = {
        "en": "English",
        "vi": "Vietnamese (Tiếng Việt)",
        "ar": "Arabic (العربية)"
    }.get(payload.target_lang, payload.target_lang.upper())
    
    system_prompt = (
        "You are an expert multilingual Luxury Travel Copywriter.\n"
        f"Your task is to translate the given travel text string into {target_lang_name}.\n\n"
        "RULES FOR PREMIUM & LUXURY TRANSLATION:\n"
        "1. Tone and vocabulary:\n"
        "   - English ('en'): Evoke bespoke elegance, exclusive privileges, and poetic serenity (e.g., 'Serene sanctuary', 'Heritage journey', 'Curated experiences').\n"
        "   - Vietnamese ('vi'): Use elegant, respectful, and sophisticated Sino-Vietnamese phrasing (e.g., 'Thượng khách', 'Kiệt tác trú ẩn', 'Hành trình di sản', 'Điểm hẹn yên bình').\n"
        "   - Arabic ('ar'): Use Royal Modern Standard Arabic (Fusha) with respectful honorifics (e.g., 'الضيوف الكرام', 'رحلة منسقة خصيصاً', 'ملاذات هادئة'). Ensure proper Right-to-Left layout flow.\n"
        "2. Output format:\n"
        "   - Return ONLY the translation of the input text. Keep HTML tags intact if any exist in the source.\n"
        "   - Do NOT wrap the translation in quotes or code fences. Do NOT include any chat preamble, comments, or explanations."
    )
    
    try:
        agent = Agent(
            model=llm_client.get_model(),
            system_prompt=system_prompt
        )
        res = await agent.run(payload.text)
        translated_text = res.output.strip()
        
        if translated_text.startswith("```"):
            lines = translated_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            translated_text = "\n".join(lines).strip()
            
        return {"translated_text": translated_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quotations/{quotation_id}/translate")
async def translate_quotation_endpoint(quotation_id: str, lang: str):
    """Triggers on-demand translation for a quotation."""
    h = _get_helpers()
    if lang not in ("en", "vi", "ar"):
        raise HTTPException(status_code=400, detail="Unsupported language")
    success = await h._translate_item_on_demand(quotation_id, lang, is_itinerary=False)
    if not success:
        raise HTTPException(status_code=500, detail="Translation failed")
    status = h._load_translation_status(quotation_id)
    return status


@router.post("/itineraries/{itinerary_id}/translate")
async def translate_itinerary_endpoint(itinerary_id: str, lang: str):
    """Triggers on-demand translation for an itinerary."""
    h = _get_helpers()
    if lang not in ("en", "vi", "ar"):
        raise HTTPException(status_code=400, detail="Unsupported language")
    success = await h._translate_item_on_demand(itinerary_id, lang, is_itinerary=True)
    if not success:
        raise HTTPException(status_code=500, detail="Translation failed")
    status = h._load_translation_status(itinerary_id)
    return status


@router.get("/quotations/{quotation_id}/translation-status")
async def get_quotation_translation_status(quotation_id: str):
    """Returns the translation status of a quotation."""
    h = _get_helpers()
    status = h._load_translation_status(quotation_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Translation status was not found.")
    try:
        from github_publish import get_next_version
        next_ver = await get_next_version(quotation_id)
        status["latest_version"] = max(1, next_ver - 1)
    except Exception:
        status["latest_version"] = 1
    return status


@router.get("/itineraries/{itinerary_id}/translation-status")
async def get_itinerary_translation_status(itinerary_id: str):
    """Returns the translation status of an itinerary."""
    h = _get_helpers()
    status = h._load_translation_status(itinerary_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Translation status was not found.")
    try:
        from github_publish import get_next_version
        next_ver = await get_next_version(itinerary_id)
        status["latest_version"] = max(1, next_ver - 1)
    except Exception:
        status["latest_version"] = 1
    return status
