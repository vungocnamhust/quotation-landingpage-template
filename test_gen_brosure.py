import os
import sys
import json
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import image_selector
async def mock_extract_and_map_destinations(text, max_items=None):
    return [
        {"name": "Hà Nội", "slug": "ha-noi"},
        {"name": "Vịnh Hạ Long", "slug": "quang-ninh"},
        {"name": "Hội An", "slug": "quang-nam"},
        {"name": "Đà Nẵng", "slug": "da-nang"}
    ]
image_selector.extract_and_map_destinations = mock_extract_and_map_destinations

from generate_8d7n_quotation import payload

from main import app
client = TestClient(app)

response = client.post("/quotations?lang=en", json=payload)
if response.status_code == 200:
    q_id = response.json().get("quotationId")
    
    html_res = client.get(f"/quotations/{q_id}?lang=en")
    with open("test-brosure.html", "w") as f:
        f.write(html_res.text)
        
    pdf_res = client.get(f"/quotations/{q_id}/pdf?lang=en")
    with open("test-brosure-pdf.html", "w") as f:
        f.write(pdf_res.text)
        
    print("test-brosure.html and test-brosure-pdf.html generated.")
else:
    print("Failed to generate quotation:", response.text)
