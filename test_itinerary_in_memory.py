import json
import re
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Load the JSON from test_create_itinerary.sh
with open("test_create_itinerary.sh", "r") as f:
    content = f.read()

# Extract the JSON payload (everything between -d '{ and }')
json_match = re.search(r"-d '(\{.*?\})'", content, re.DOTALL)
if not json_match:
    # Fallback regex in case formatting is slightly different
    json_match = re.search(r"\'(\{.*\})\'", content, re.DOTALL)

if json_match:
    payload = json.loads(json_match.group(1))
    print("Sending POST request to /itineraries...")
    response = client.post("/itineraries", json=payload)
    print("Response status code:", response.status_code)
    try:
        print("Response JSON:", json.dumps(response.json(), indent=2))
    except Exception as e:
        print("Response text:", response.text)
else:
    print("Error: Could not extract JSON payload from test_create_itinerary.sh")
