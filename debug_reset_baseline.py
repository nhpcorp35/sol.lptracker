import requests
import json

resp = requests.post(
    "https://vfat.lptracker.info/api/debug/reset-baseline/base:uniswap:5992616",
    auth=("", "J__9EXrwEA77ScMf"),
    timeout=30,
)
print(f"Status: {resp.status_code}")
print(json.dumps(resp.json(), indent=2))
