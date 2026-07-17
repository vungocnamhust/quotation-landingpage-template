import json
import os
import sys
import asyncio
from functools import partial

# Add current directory to path so main can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from main import _build_ctx, templates, TourQuotationPayload, _save_translation_status

async def main():
    quotation_id = "quo_3e9bcd4f2f85"
    quo_dir = os.path.join("published", quotation_id)
    
    # Load old payload and ctx
    payload_path = os.path.join(quo_dir, "payload.json")
    ctx_path = os.path.join(quo_dir, "ctx.json")
    
    with open(payload_path, "r", encoding="utf-8") as f:
        payload_data = json.load(f)
        
    with open(ctx_path, "r", encoding="utf-8") as f:
        old_ctx = json.load(f)
        
    # Apply manual fixes to payload data in case they are old
    payload_data["quotationNarrative"] = (
        payload_data["quotationNarrative"]
        .replace("خليج هاليغ", "خليج ها لونغ")
    )
    payload_data["journeyGlance"]["domesticFlights"] = (
        payload_data["journeyGlance"]["domesticFlights"]
        .replace("nha trang", "نها ترانغ")
    )
    
    # Parse payload
    payload = TourQuotationPayload.model_validate(payload_data)
    
    # Extract destinations and hero image from old ctx
    destinations = old_ctx.get("destinations", [])
    hero_image_url = old_ctx.get("img_0", "/assets/vietnam-safar-logo.png")
    lang = payload_data.get("lang", "ar")
    
    # Re-build context using updated main.py logic
    ctx = _build_ctx(
        quotation_id=quotation_id,
        payload=payload,
        hero_image_url=hero_image_url,
        destinations=destinations,
        lang=lang,
        template_name="vietnam_heritage_luxury.html"
    )
    
    # Add translation status/baseline keys
    ctx["baseline_payload"] = payload.model_dump(mode="json")
    ctx["baseline_lang"] = lang
    ctx["translations"] = {}
    ctx["available_langs"] = [lang]
    ctx["translation_status"] = {"baseline_lang": lang, "available_langs": [lang]}
    
    # Render templates
    loop = asyncio.get_event_loop()
    tmpl_lp  = templates.get_template("vietnam_heritage_luxury.html")
    tmpl_pdf = templates.get_template("vietnam_heritage_luxury_pdf.html")

    rendered_html, rendered_pdf = await asyncio.gather(
        loop.run_in_executor(None, partial(tmpl_lp.render,  **ctx)),
        loop.run_in_executor(None, partial(tmpl_pdf.render, **ctx)),
    )
    
    # Write files back to disk
    sfx = f"_{lang}" if lang != "en" else ""
    with open(os.path.join(quo_dir, f"v1{sfx}.html"), "w", encoding="utf-8") as f:
        f.write(rendered_html)
    with open(os.path.join(quo_dir, f"pdf{sfx}.html"), "w", encoding="utf-8") as f:
        f.write(rendered_pdf)
    with open(os.path.join(quo_dir, "ctx.json"), "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=2)
    with open(os.path.join(quo_dir, "payload.json"), "w", encoding="utf-8") as f:
        json.dump(payload.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
        
    await _save_translation_status(quotation_id, {"baseline_lang": lang, "available_langs": [lang]})
    print(f"Quotation {quotation_id} successfully regenerated in {quo_dir}!")

if __name__ == "__main__":
    asyncio.run(main())
