import requests
import json

resp = requests.get(
    "https://vfat.lptracker.info/api/debug/volume-split-history?days=30",
    auth=("", "J__9EXrwEA77ScMf"),
    timeout=30,
)
print(f"Status: {resp.status_code}")
data = resp.json()
print("Summary:", json.dumps(data.get("summary"), indent=2))
print("\nDaily rows:")
for r in data.get("rows", []):
    print(f"  ts={r['ts']}: 0.30%=${r['vol_030']:,.0f}  0.05%=${r['vol_005']:,.0f}  0.05%_share={r['pct_005_of_combined']:.1f}%")
