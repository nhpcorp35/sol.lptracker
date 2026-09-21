import requests

resp = requests.get("https://taoclaude.lptracker.info/api/history/0?range=7d", auth=("", "@Ak351818!!"), timeout=20)
data = resp.json()
snapshots = data.get("snapshots", [])
print(f"Total snapshots in 7d window: {len(snapshots)}")
for s in snapshots[-20:]:
    print(f"  ts={s['ts']}, alpha={s.get('alpha')}")
