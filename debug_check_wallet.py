import requests
resp = requests.get("https://snuggle.lptracker.info/api/debug/wallets", auth=("", "J__9EXrwEA77ScMf"), timeout=15)
print(resp.status_code, resp.text)
