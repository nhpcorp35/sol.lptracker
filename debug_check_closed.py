import requests
import json

resp2 = requests.get("https://snuggle.lptracker.info/api/maxfi/closed", auth=("", "J__9EXrwEA77ScMf"), timeout=20)
print(f"status={resp2.status_code}, len={len(resp2.text)}")
print(f"repr: {resp2.text!r}")
try:
    data = resp2.json()
    print(f"parsed type: {type(data)}, content: {json.dumps(data, indent=2)[:3000]}")
except Exception as e:
    print(f"json parse failed: {e}")
