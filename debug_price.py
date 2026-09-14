import requests
url = "https://api.geckoterminal.com/api/v2/simple/networks/solana/token_price/So11111111111111111111111111111111111111112,EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
resp = requests.get(url, timeout=8)
print(f"Status: {resp.status_code}")
print(f"Body: {resp.text}")
