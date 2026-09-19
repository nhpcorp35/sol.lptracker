import requests

resp = requests.get("https://v3.lptracker.info/api/debug/snuggle-check", timeout=30)
print(f"Status: {resp.status_code}")
print(resp.text)
