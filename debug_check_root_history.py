import requests

resp = requests.get("https://taoclaude.lptracker.info/api/history?range=all&netuid=0", auth=("", "@Ak351818!!"), timeout=20)
print(f"Status: {resp.status_code}")
print(resp.text[:3000])
