import requests
import json

resp = requests.get("https://v3.lptracker.info/api/snuggle/summary", timeout=30)
data = resp.json()
for p in data.get("positions", []):
    print(f"tokenId={p['tokenId']}: advertisedApr={p.get('advertisedApr')!r}, observedFeeApr={p.get('observedFeeApr')!r}, rangeStatus={p.get('rangeStatus')}")
