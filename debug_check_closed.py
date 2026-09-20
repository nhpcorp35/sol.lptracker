import requests
import json

resp = requests.get("https://snuggle.lptracker.info/api/maxfi/positions", auth=("", "J__9EXrwEA77ScMf"), timeout=20)
data = resp.json()
print("=== Open positions ===")
for p in data.get("positions", []):
    print(f"token_id={p['token_id']}, deposit_ts={p.get('deposit_ts')}, total_rebalances={p.get('total_rebalances')}, value=${p.get('position_value_usd')}")

resp2 = requests.get("https://snuggle.lptracker.info/api/maxfi/closed", auth=("", "J__9EXrwEA77ScMf"), timeout=20)
print(f"\n=== Closed positions endpoint status: {resp2.status_code} ===")
print(resp2.text[:2000])
