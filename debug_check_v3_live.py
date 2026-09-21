import requests

resp = requests.get("https://v3.lptracker.info/api/tao/position?coldkey=5Cexeg7deNSTzsqMKuBmvc9JHGHymuL4SdjAA9Jw4eeHUphb", timeout=20)
print(f"Status: {resp.status_code}")
print(resp.text[:3000])
