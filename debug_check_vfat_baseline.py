import requests
import json

resp = requests.get(
    "https://vfat.lptracker.info/api/debug/baseline/base:uniswap:5992616",
    auth=("", "J__9EXrwEA77ScMf"),
    timeout=20,
)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2))
