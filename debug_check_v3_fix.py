import requests

resp = requests.get("https://v3.lptracker.info/api/snuggle/summary", auth=("", "J__9EXrwEA77ScMf"), timeout=30)
print(f"Status: {resp.status_code}")
print(f"Body (first 300 chars): {resp.text[:300]}")
