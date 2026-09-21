import requests

resp = requests.get("https://vfat.lptracker.info/api/positions", auth=("", "@Ak351818!!"), timeout=30)
data = resp.json()
print(f"Total positions: {len(data.get('positions', []))}")
for p in data.get("positions", []):
    print(f"  chain={p.get('chain')}, token_id={p['token_id']}, pool={p['token0']['symbol']}/{p['token1']['symbol']}, value=${p.get('position_value_usd')}")
