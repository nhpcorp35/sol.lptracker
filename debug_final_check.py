import requests
resp = requests.get("https://v3.lptracker.info/api/debug/snuggle-check", timeout=15)
print(f"Status: {resp.status_code} (expect 401, route removed)")
print(resp.text[:100])
