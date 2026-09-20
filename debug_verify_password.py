import requests

services = [
    ("snuggle", "https://snuggle.lptracker.info/api/health"),
    ("vfat", "https://vfat.lptracker.info/api/health"),
    ("sol", "https://sol.lptracker.info/api/health"),
    ("taoclaude", "https://taoclaude.lptracker.info/api/health"),
    ("hub", "https://v4.lptracker.info/api/health"),
]

print("=== New password ===")
for name, url in services:
    resp = requests.get(url, auth=("", "@Ak351818!!"), timeout=15)
    print(f"{name}: {resp.status_code}")

print("\n=== Old password (should now fail everywhere) ===")
for name, url in services:
    resp = requests.get(url, auth=("", "J__9EXrwEA77ScMf"), timeout=15)
    print(f"{name}: {resp.status_code}")

print("\n=== Hub's own aggregation (tests its outbound calls to the other 4) ===")
resp = requests.get("https://v4.lptracker.info/api/total?bust=1", auth=("", "@Ak351818!!"), timeout=60)
data = resp.json()
for b in data.get("breakdown", []):
    print(f"  {b['key']}: ok={b['ok']}")
