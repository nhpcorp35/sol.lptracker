import requests
resp = requests.get("https://tao-scratch-production.up.railway.app/api/positions?coldkey=5Cexeg7deNSTzsqMKuBmvc9JHGHymuL4SdjAA9Jw4eeHUphb", timeout=30)
print(f"Status: {resp.status_code}")
print(f"Headers: {dict(resp.headers)}")
print(f"Body length: {len(resp.text)}")
print(f"Body repr (first 500): {repr(resp.text[:500])}")
