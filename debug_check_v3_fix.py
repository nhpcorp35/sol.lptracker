import requests

resp = requests.get("https://v3.lptracker.info/api/snuggle/summary", timeout=30)
print(f"Status: {resp.status_code}")
print(f"Headers: {dict(resp.headers)}")
print(f"Body (first 500 chars): {resp.text[:500]}")
