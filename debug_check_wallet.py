import requests

resp = requests.get("https://snuggle.lptracker.info/api/health", timeout=15)
print(resp.status_code, resp.text[:500])
