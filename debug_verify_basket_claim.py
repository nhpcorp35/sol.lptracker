import requests

resp = requests.get("https://taoclaude.lptracker.info/api/positions", auth=("", "@Ak351818!!"), timeout=30)
data = resp.json()
for p in data.get("positions", []):
    if p["netuid"] == 0:
        print(f"Root network: basketClaimableTao={p.get('basketClaimableTao')}, basketClaimableUsd={p.get('basketClaimableUsd')}")
