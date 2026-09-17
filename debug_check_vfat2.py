import time
import requests

print("=== Direct call to vfat's own API (bypassing hub) ===")
start = time.time()
try:
    resp = requests.get("https://vfat.lptracker.info/api/positions", auth=("", "J__9EXrwEA77ScMf"), timeout=60)
    print(f"Status: {resp.status_code}, elapsed: {time.time()-start:.2f}s, body length: {len(resp.text)}")
except Exception as e:
    print(f"FAILED after {time.time()-start:.2f}s: {type(e).__name__}: {e}")

print("\n=== Hub's /api/total with bust=1 (forces a fresh check) ===")
start = time.time()
try:
    resp = requests.get("https://v4.lptracker.info/api/total?bust=1", auth=("", "J__9EXrwEA77ScMf"), timeout=90)
    print(f"Status: {resp.status_code}, elapsed: {time.time()-start:.2f}s")
    data = resp.json()
    for b in data.get("breakdown", []):
        print(f"  {b['key']}: ok={b['ok']}, total_usd={b.get('total_usd')}")
except Exception as e:
    print(f"FAILED after {time.time()-start:.2f}s: {type(e).__name__}: {e}")
