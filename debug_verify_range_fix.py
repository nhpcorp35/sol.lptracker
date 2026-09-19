import requests

resp = requests.get("https://snuggle.lptracker.info/api/maxfi/positions", auth=("", "J__9EXrwEA77ScMf"), timeout=30)
data = resp.json()
for p in data.get("positions", []):
    if p["token_id"] in (6042464, 6042886):
        print(f"token_id={p['token_id']}: in_range={p['in_range']}, out_of_range_seconds={p.get('out_of_range_seconds')}")
