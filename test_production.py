import json
import re
import requests

PROD_URL = "https://journeys.vietnamsafar.vn"

# 1. Load B2B quotation payload from test_b2b.py
import test_b2b
quotation_payload = test_b2b.payload

# 2. Extract itinerary payload from test_create_itinerary.sh
with open("test_create_itinerary.sh", "r") as f:
    itinerary_content = f.read()

json_match = re.search(r"-d '(\{.*?\})'", itinerary_content, re.DOTALL)
if not json_match:
    json_match = re.search(r"\'(\{.*\})\'", itinerary_content, re.DOTALL)

itinerary_payload = json.loads(json_match.group(1))

# 3. Post to Quotation endpoint on Production
print("Sending POST request to production /quotations...")
try:
    q_response = requests.post(f"{PROD_URL}/quotations", json=quotation_payload, headers={"Content-Type": "application/json"})
    print("Quotation Status:", q_response.status_code)
    print("Quotation Response:", json.dumps(q_response.json(), indent=2))
except Exception as e:
    print("Failed to post quotation:", e)

# 4. Post to Itinerary endpoint on Production
print("\nSending POST request to production /itineraries...")
try:
    i_response = requests.post(f"{PROD_URL}/itineraries", json=itinerary_payload, headers={"Content-Type": "application/json"})
    print("Itinerary Status:", i_response.status_code)
    print("Itinerary Response:", json.dumps(i_response.json(), indent=2))
except Exception as e:
    print("Failed to post itinerary:", e)
