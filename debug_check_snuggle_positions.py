import requests
resp = requests.get("https://snuggle.lptracker.info/api/snuggle/positions", auth=("", "J__9EXrwEA77ScMf"), timeout=20)
data = resp.json()
for p in data.get("positions", []):
    print(f"token_id={p['token_id']}, pool={p['token0']['symbol']}/{p['token1']['symbol']}, value=${p.get('position_value_usd')}")
print(f"Total: {len(data.get('positions', []))}")
