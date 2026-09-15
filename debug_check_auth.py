import requests

PASSWORD = "J__9EXrwEA77ScMf"
AUTH = ("", PASSWORD)

targets = [
    ("vfat", "https://vfat.lptracker.info/api/positions"),
    ("sol", "https://sol.lptracker.info/api/positions"),
    ("tao", "https://taoclaude.lptracker.info/api/positions"),
    ("snuggle", "https://snuggle.lptracker.info/api/snuggle/positions"),
    ("hub /api/total", "https://v4.lptracker.info/api/total"),
]

for label, url in targets:
    try:
        r_noauth = requests.get(url, timeout=15)
        r_auth = requests.get(url, auth=AUTH, timeout=20)
        print(f"{label}: no-auth={r_noauth.status_code}, with-auth={r_auth.status_code}, body[:150]={r_auth.text[:150]!r}")
    except Exception as e:
        print(f"{label}: FAILED {e}")
