import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

import test_b2b
payload = test_b2b.payload

print("POST /quotations...")
response = client.post("/quotations", json=payload)
print(response.status_code)
quo_id = response.json()["quotationId"]

print(f"GET /quotations/{quo_id}/pdf...")
pdf_response = client.get(f"/quotations/{quo_id}/pdf")
print(pdf_response.status_code)
if pdf_response.status_code != 200:
    print(pdf_response.text)
else:
    print("PDF rendered successfully, length:", len(pdf_response.text))
