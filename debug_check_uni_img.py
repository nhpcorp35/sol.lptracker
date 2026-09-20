import requests
resp = requests.get("https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/ethereum/assets/0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984/logo.png", timeout=15)
print(f"status={resp.status_code}, content-type={resp.headers.get('content-type')}, size={len(resp.content)} bytes")
