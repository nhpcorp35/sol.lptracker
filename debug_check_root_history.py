import requests

resp = requests.get("https://taoclaude.lptracker.info/api/history/0?range=all", auth=("", "@Ak351818!!"), timeout=20)
print(f"Status: {resp.status_code}")
data = resp.json()
snapshots = data.get("snapshots", [])
print(f"Total snapshots: {len(snapshots)}")
print("First 5:", snapshots[:5])
print("Last 5:", snapshots[-5:])
# Check if alpha is genuinely constant across all snapshots
alphas = set(s.get("alpha") for s in snapshots)
print(f"\nDistinct alpha values seen: {len(alphas)}")
print(alphas if len(alphas) < 10 else list(alphas)[:10])
