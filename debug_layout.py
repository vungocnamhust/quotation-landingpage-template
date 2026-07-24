import sys
sys.path.append(".")
from main import _load_ctx_data, _build_ctx, TourQuotationPayload

ctx_data = _load_ctx_data("quo_62861a208ec5")
payload = TourQuotationPayload.model_validate(ctx_data["baseline_payload"])
lang_ctx = _build_ctx(
    quotation_id="quo_62861a208ec5",
    payload=payload,
    hero_image_url=ctx_data.get("img_0", ""),
    destinations=ctx_data.get("destinations", []),
    lang="en",
    template_name="vietnam_luxury_brosure.html",
    brand={}
)

c0 = lang_ctx["chapters"][0]
print("Chapter 0:", c0.get("destination"))
for idx, d in enumerate(c0.get("days", [])):
    t = d.get("title")
    lt = d.get("layout_type")
    li = d.get("layout_images")
    print(f"Day {idx+1}: {t} | layout_type: {lt} | layout_images: {li}")
