import requests
import json

resp = requests.get(
    "https://vfat.lptracker.info/api/debug/range-compare",
    auth=("", "J__9EXrwEA77ScMf"),
    timeout=60,
)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2))
