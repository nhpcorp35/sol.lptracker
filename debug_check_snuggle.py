import requests
import json

for endpoint in ["/api/snuggle/positions", "/api/maxfi/positions"]:
    resp = requests.get(f"https://snuggle.lptracker.info{endpoint}", timeout=20)
    print(f"=== {endpoint} ===")
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(json.dumps(data, indent=2)[:4000])
    print()
