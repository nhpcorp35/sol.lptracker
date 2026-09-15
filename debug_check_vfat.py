import time
import requests

url = "https://vfat.lptracker.info/api/positions"
print("=== Without auth ===")
resp = requests.get(url, timeout=15)
print(f"Status: {resp.status_code}, body: {resp.text[:200]}")

print("\n=== With the known password ===")
resp2 = requests.get(url, auth=("", "J__9EXrwEA77ScMf"), timeout=30)
print(f"Status: {resp2.status_code}")
print(f"Body (first 1500 chars): {resp2.text[:1500]}")
