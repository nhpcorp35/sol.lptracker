import requests
import json

resp = requests.get("https://snuggle.lptracker.info/api/cashout-log", auth=("", "J__9EXrwEA77ScMf"), timeout=20)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2))
