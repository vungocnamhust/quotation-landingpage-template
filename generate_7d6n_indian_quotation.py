import json
import os
import sys
import types
from fastapi.testclient import TestClient

# Add current directory to path so main can be imported
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Stub the image selector module before importing main so this script
# can run without the full AI/image-selection dependency stack.
image_selector = types.ModuleType("image_selector")
async def mock_extract_and_map_destinations(text, max_items=None):
    print("[Mock] Extracting and mapping destinations for: Hanoi, Ninh Binh, Halong Bay, Sapa")
    return [
        {"name": "Hanoi", "slug": "ha-noi"},
        {"name": "Ninh Binh", "slug": "ninh-binh"},
        {"name": "Halong Bay", "slug": "quang-ninh"},
        {"name": "Sapa", "slug": "lao-cai"}
    ]

async def mock_select_landing_image(payload, model_name=None):
    print("[Mock] Selecting landing image")
    return "/assets/halong-bay.jpg"

def mock_get_random_image_for_province(slug):
    return {
        "url": f"/assets/mock-{slug}.jpg",
        "province": slug,
        "source": "mock",
    }

def mock_get_all_images_for_province(slug):
    return [mock_get_random_image_for_province(slug)]

def mock_resolve_slug_locally(location):
    if not location:
        return None
    normalized = str(location).strip().lower()
    slug_map = {
        "hanoi": "ha-noi",
        "ninh binh": "ninh-binh",
        "ninhbinh": "ninh-binh",
        "halong bay": "quang-ninh",
        "halong": "quang-ninh",
        "ha long": "quang-ninh",
        "sapa": "lao-cai",
        "lao cai": "lao-cai",
    }
    return slug_map.get(normalized)

image_selector.extract_and_map_destinations = mock_extract_and_map_destinations
image_selector.select_landing_image = mock_select_landing_image
image_selector.get_random_image_for_province = mock_get_random_image_for_province
image_selector.get_all_images_for_province = mock_get_all_images_for_province
image_selector.resolve_slug_locally = mock_resolve_slug_locally
sys.modules["image_selector"] = image_selector

from main import app

client = TestClient(app)

# Load the structured 7-day Indian traveler English itinerary payload from published source
payload_file = os.path.join(os.path.dirname(__file__), "published", "quo_01ece847501d", "payload.json")
ctx_file = os.path.join(os.path.dirname(__file__), "published", "quo_01ece847501d", "ctx.json")

with open(payload_file, "r", encoding="utf-8") as f:
    payload = json.load(f)

# If sale has edited the quotation inline (ctx.json exists with latest version updates), merge changes
if os.path.exists(ctx_file):
    print(f"Syncing latest inline edits from {ctx_file} into payload...")
    with open(ctx_file, "r", encoding="utf-8") as f:
        ctx = json.load(f)
    
    edited = ctx.get("html_sync", {}).get("en", {}).get("edited_fields", {})
    
    # 1. Sync overview and narrative metadata
    narrative = edited.get("lede") or ctx.get("lede")
    if narrative:
        payload["quotationNarrative"] = narrative
        
    headline = edited.get("quotation_title") or ctx.get("quotation_title")
    if headline and "landingpageContent" in payload:
        payload["landingpageContent"]["heroSection"]["headline"] = headline
        
    subtitle = edited.get("tour_title") or ctx.get("tour_title")
    if subtitle and "landingpageContent" in payload:
        payload["landingpageContent"]["heroSection"]["subtitle"] = subtitle
        
    # 2. Sync Journey Glance info
    if "journeyGlance" in payload:
        market = edited.get("nationality") or ctx.get("nationality")
        if market:
            payload["journeyGlance"]["market"] = market
            
        profile = edited.get("customer_name") or ctx.get("guests_txt")
        if profile:
            payload["journeyGlance"]["guestProfile"] = profile
            
        style = edited.get("travel_style") or ctx.get("travel_style")
        if style:
            payload["journeyGlance"]["partnerNote"] = style
            
        validity = edited.get("valid_until") or ctx.get("valid_until")
        if validity:
            payload["journeyGlance"]["validity"] = validity

    # 3. Sync Day-by-Day Itinerary updates
    ctx_iti = ctx.get("itinerary", [])
    pay_iti = payload.get("itinerary", [])
    import re
    
    for idx, day in enumerate(ctx_iti, 1):
        if idx - 1 < len(pay_iti):
            p_day = pay_iti[idx - 1]
            
            # Title
            title_key = f"day_title_{idx}"
            p_day["title"] = edited.get(title_key) or day.get("title")
            
            # Summary (description paragraphs)
            desc_paras = []
            p = 0
            while True:
                desc_key = f"day_desc_{idx}_{p}"
                if desc_key in edited:
                    desc_paras.append(edited[desc_key])
                    p += 1
                else:
                    break
            if desc_paras:
                p_day["summary"] = "\n\n".join(desc_paras)
            elif day.get("description"):
                p_day["summary"] = "\n\n".join(day["description"]) if isinstance(day["description"], list) else day["description"]
                
            # Overnight
            overnight_key = f"day_overnight_{idx}"
            p_day["overnight"] = edited.get(overnight_key) or day.get("overnight")
            
            # Meals
            meals_key = f"day_meals_{idx}"
            if meals_key in edited:
                p_day["meals"] = [m.strip() for m in re.split(r'[·•\-,/]', edited[meals_key]) if m.strip()]
            else:
                p_day["meals"] = day.get("meals")
                
            # Activities
            highlights_key = f"day_highlights_{idx}"
            if highlights_key in edited:
                p_day["activities"] = [h.strip() for h in re.split(r'[·•\-,/]', edited[highlights_key]) if h.strip()]
            else:
                p_day["activities"] = day.get("activities")
                
            # Notes
            notes_list = []
            p = 0
            while True:
                note_key = f"day_note_{idx}_{p}"
                if note_key in edited:
                    notes_list.append(edited[note_key])
                    p += 1
                else:
                    break
            if notes_list:
                p_day["notes"] = notes_list
            else:
                p_day["notes"] = day.get("notes")

    # 4. Sync Hotels room notes
    room_notes = edited.get("room_notes") or ctx.get("room_notes")
    if room_notes and "hotelPlan" in payload:
        payload["hotelPlan"]["roomNotes"] = room_notes
        
    # 5. Sync Inclusions & Exclusions
    inclusions = []
    p = 1
    while True:
        inc_key = f"inc_{p}"
        if inc_key in edited:
            inclusions.append(edited[inc_key])
            p += 1
        else:
            break
    if inclusions:
        payload["inclusions"] = inclusions
    elif ctx.get("inclusions"):
        payload["inclusions"] = ctx["inclusions"]
        
    exclusions = []
    p = 1
    while True:
        exc_key = f"exc_{p}"
        if exc_key in edited:
            exclusions.append(edited[exc_key])
            p += 1
        else:
            break
    if exclusions:
        payload["exclusions"] = exclusions
    elif ctx.get("exclusions"):
        payload["exclusions"] = ctx["exclusions"]

    # 6. Sync Terms
    if "bookingTerms" in payload:
        term_deposit = edited.get("term_deposit") or ctx.get("term_deposit")
        if term_deposit:
            payload["bookingTerms"]["deposit"] = term_deposit
            
        term_balance = edited.get("term_balance") or ctx.get("term_balance")
        if term_balance:
            payload["bookingTerms"]["balance"] = term_balance
            
        term_cancellation = edited.get("term_cancellation") or ctx.get("term_cancellation")
        if term_cancellation:
            payload["bookingTerms"]["cancellation"] = term_cancellation
            
        term_confirmation = edited.get("term_confirmation") or ctx.get("term_confirmation")
        if term_confirmation:
            payload["bookingTerms"]["confirmation"] = term_confirmation

    # 7. Sync Finalization
    if "finalization" in payload:
        final_reqs = []
        p = 0
        while True:
            fr_key = f"final_req_{p}"
            if fr_key in edited:
                final_reqs.append(edited[fr_key])
                p += 1
            else:
                break
        if final_reqs:
            payload["finalization"]["finalDetailsRequired"] = ", ".join(final_reqs)
        elif ctx.get("final_req"):
            payload["finalization"]["finalDetailsRequired"] = ", ".join(ctx["final_req"]) if isinstance(ctx["final_req"], list) else ctx["final_req"]
            
        final_afters = []
        p = 0
        while True:
            fa_key = f"final_after_{p}"
            if fa_key in edited:
                final_afters.append(edited[fa_key])
                p += 1
            else:
                break
        if final_afters:
            payload["finalization"]["afterConfirmation"] = ", ".join(final_afters)
        elif ctx.get("final_after"):
            payload["finalization"]["afterConfirmation"] = ", ".join(ctx["final_after"]) if isinstance(ctx["final_after"], list) else ctx["final_after"]

    # 8. Sync Pricing Options & Totals
    if "pricing" in payload:
        if ctx.get("grand_total"):
            payload["pricing"]["grandTotal"] = ctx["grand_total"]
        if ctx.get("subtotal"):
            payload["pricing"]["subtotal"] = ctx["subtotal"]
        
        ctx_opts = ctx.get("price_options", [])
        pay_opts = payload["pricing"].get("priceOptions", [])
        for p_idx, opt in enumerate(ctx_opts, 1):
            if p_idx - 1 < len(pay_opts):
                p_opt = pay_opts[p_idx - 1]
                
                pax_key = f"price_pax_{p_idx}"
                if pax_key in edited:
                    try:
                        import re
                        val_str = edited[pax_key]
                        num_match = re.search(r'([\d,.]+)', val_str)
                        if num_match:
                            clean_val = float(num_match.group(1).replace(",", ""))
                            p_opt["amount"] = clean_val
                    except Exception:
                        pass
                elif opt.get("pricePerPerson", {}).get("amount"):
                    p_opt["amount"] = opt["pricePerPerson"]["amount"]
                
                if opt.get("hotelCategory"):
                    p_opt["label"] = opt["hotelCategory"]
                if opt.get("optionName"):
                    p_opt["notes"] = opt["optionName"]



print("POST /quotations (B2B English)...")
response = client.post("/quotations?lang=en", json=payload)
print("Response status code:", response.status_code)
try:
    res_json = response.json()
    print("Response JSON:", json.dumps(res_json, indent=2))
    quotation_id = res_json.get("quotationId")
    if quotation_id:
        print(f"Quotation {quotation_id} generated successfully!")
        
        # Sync 100% context data (including specialist info, translations, html_sync edits) from quo_01ece847501d
        if os.path.exists(ctx_file):
            print(f"Cloning baseline ctx.json from quo_01ece847501d to {quotation_id}...")
            
            # 1. Clone ctx.json
            with open(ctx_file, "r", encoding="utf-8") as f:
                cloned_ctx = json.load(f)
            cloned_ctx["quotation_id"] = quotation_id
            
            if "quotation_number" in cloned_ctx:
                cloned_ctx["quotation_number"] = f"QT-2026-CAPELLA-7D6N-IND"
            
            # Write cloned ctx.json to the new quotation directory
            new_quo_dir = os.path.join("published", quotation_id)
            os.makedirs(new_quo_dir, exist_ok=True)
            with open(os.path.join(new_quo_dir, "ctx.json"), "w", encoding="utf-8") as f:
                json.dump(cloned_ctx, f, ensure_ascii=False, default=str)
                
            # Update uvicorn in-memory cache directly
            from main import quotations
            if quotation_id in quotations:
                quotations[quotation_id]["ctx"] = cloned_ctx
                # Remove static HTML in-memory cache to force a dynamic render from JINJA2 templates
                if "html" in quotations[quotation_id]:
                    del quotations[quotation_id]["html"]
            
            # Remove any baseline cached files on disk to prevent GET fallback cache hits
            for cached_file in ["v1.html", "v1_pdf.html", "pdf.html", "pdf_en.html"]:
                local_cached = os.path.join(new_quo_dir, cached_file)
                if os.path.exists(local_cached):
                    try:
                        os.remove(local_cached)
                    except Exception:
                        pass

            # 2. Copy translation status
            ts_file = os.path.join(os.path.dirname(ctx_file), "translation_status.json")
            if os.path.exists(ts_file):
                with open(ts_file, "r", encoding="utf-8") as f:
                    ts_content = f.read()
                with open(os.path.join(new_quo_dir, "translation_status.json"), "w", encoding="utf-8") as f:
                    f.write(ts_content)
        
        # Verify get endpoint and save HTML (forces dynamic render of user's updated templates)
        get_res = client.get(f"/quotations/{quotation_id}?lang=en")
        print(f"GET /quotations/{quotation_id} status:", get_res.status_code)
        if get_res.status_code == 200:
            html_content = get_res.text
            
            # Apply regex replacements to update data-editable texts from edited_fields (resolves hardcoded signature issue)
            if os.path.exists(ctx_file):
                edited = cloned_ctx.get("html_sync", {}).get("en", {}).get("edited_fields", {})
                
                # Replace ID and data-editable inner contents
                html_content = html_content.replace("quo_01ece847501d", quotation_id)
                for key, new_val in edited.items():
                    if new_val:
                        # Target tags with data-editable="key" or data-editable='key'
                        pattern = r'(<[^>]*data-editable=["\']' + re.escape(key) + r'["\'][^>]*>)(.*?)(</[a-zA-Z0-9]+>)'
                        def repl(match, val=new_val):
                            return match.group(1) + str(val) + match.group(3)
                        html_content = re.sub(pattern, repl, html_content, flags=re.DOTALL)
                
                # Replace designer avatar to Hieu's avatar if signature matches Hieu/Eddie
                sig_val = edited.get("designer_signature", "")
                if "Eddie" in sig_val or "Hieu" in sig_val:
                    html_content = html_content.replace("/assets/dias_team/hieu.jpg", "/assets/dias_team/hieu.jpg")
            
            # Save updated HTML to disk as v1.html for permanent cache
            with open(os.path.join(new_quo_dir, "v1.html"), "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Update memory cache
            from main import quotations
            if quotation_id in quotations:
                quotations[quotation_id]["html"] = html_content
            
            output_file = "vietnam-heritage-luxury-indian-7d6n-quotation.html"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"HTML saved to: {output_file}")
        
        get_pdf_res = client.get(f"/quotations/{quotation_id}/pdf?lang=en")
        print(f"GET /quotations/{quotation_id}/pdf status:", get_pdf_res.status_code)
        if get_pdf_res.status_code == 200:
            pdf_content = get_pdf_res.text
            
            # Apply similar replacements to PDF view
            if os.path.exists(ctx_file):
                edited = cloned_ctx.get("html_sync", {}).get("en", {}).get("edited_fields", {})
                pdf_content = pdf_content.replace("quo_01ece847501d", quotation_id)
                for key, new_val in edited.items():
                    if new_val:
                        pattern = r'(<[^>]*data-editable=["\']' + re.escape(key) + r'["\'][^>]*>)(.*?)(</[a-zA-Z0-9]+>)'
                        # Also target non-editable tags if they display the same keys (PDF uses plain spans)
                        # To keep it safe, we just use regex replacement for data-editable if present, or do general fallback replacements
                        def repl(match, val=new_val):
                            return match.group(1) + str(val) + match.group(3)
                        pdf_content = re.sub(pattern, repl, pdf_content, flags=re.DOTALL)
                
                # Replace designer avatar in PDF as well
                sig_val = edited.get("designer_signature", "")
                if "Eddie" in sig_val or "Hieu" in sig_val:
                    pdf_content = pdf_content.replace("/assets/dias_team/hieu.jpg", "/assets/dias_team/hieu.jpg")
            
            # Save to disk as pdf.html / pdf_en.html
            with open(os.path.join(new_quo_dir, "pdf.html"), "w", encoding="utf-8") as f:
                f.write(pdf_content)
            with open(os.path.join(new_quo_dir, "pdf_en.html"), "w", encoding="utf-8") as f:
                f.write(pdf_content)
                
            pdf_output_file = "vietnam-heritage-luxury-indian-7d6n-quotation-pdf.html"
            with open(pdf_output_file, "w", encoding="utf-8") as f:
                f.write(pdf_content)
            print(f"PDF view saved to: {pdf_output_file}")
        
except Exception as e:
    print("Failed to parse response:", e)
    print("Response text:", response.text)
