import asyncio
from main import app, quotations, _load_ctx_data
from fastapi.testclient import TestClient

client = TestClient(app)
quo_id = "quo_210ccc310279"

# Ensure it's loaded in memory
response = client.get(f"/quotations/{quo_id}?lang=en")

# 1. Get current ctx
ctx_data = _load_ctx_data(quo_id)
old_template = ctx_data.get("template_name")
print(f"Old template: {old_template}")

# 2. Simulate publish page with new template
payload = {
    "html": "<html><body>test</body></html>",
    "template_name": "vietnam_heritage_luxury.html"
}

response = client.post(f"/quotations/{quo_id}/publish?lang=en", json=payload)
print(f"Publish status: {response.status_code}")

# 3. Check what was saved to disk for vX.html
import os
import glob
files = glob.glob(f"published/{quo_id}/v*.html")
if files:
    latest_file = max(files, key=os.path.getmtime)
    with open(latest_file, "r") as f:
        content = f.read()
    print(f"Content of latest published file starts with:")
    print(content[:200])
    
    if "vietnam_heritage_luxury" in content or "Heritage" in content or "pb-page" in content:
        print("SUCCESS: The new template was rendered and published!")
    else:
        print("FAILED: The new template might not have been used.")
