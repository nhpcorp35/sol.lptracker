import requests
import re

resp = requests.get("https://snuggle.lptracker.info/", auth=("", "J__9EXrwEA77ScMf"), timeout=20)
html = resp.text
# Find the JS to confirm TOKEN_ICON_OVERRIDES is actually present in what's served
idx = html.find("TOKEN_ICON_OVERRIDES")
print("TOKEN_ICON_OVERRIDES found in served JS:", idx != -1)
if idx != -1:
    print(html[idx:idx+300])
