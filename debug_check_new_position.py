import requests
import json

resp = requests.get("https://snuggle.lptracker.info/api/maxfi/positions", auth=("", "J__9EXrwEA77ScMf"), timeout=20)
data = resp.json()
print("=== Current live maxfi positions ===")
for p in data.get("positions", []):
    print(f"token_id={p['token_id']}, pool={p['token0']['symbol']}/{p['token1']['symbol']}, value=${p.get('position_value_usd')}, total_rebalances={p.get('total_rebalances')}")
print(f"\nTotal count: {len(data.get('positions', []))}")
