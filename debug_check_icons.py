import requests

tokens = {
    "WETH": "0x4200000000000000000000000000000000000006",
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "UNI": "0xc3De830EA07524a0761646a6a4e4be0e114a3C83",
    "cbBTC": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
    "Cake": "0x3055913c90Fcc1A6CE9a358911721eEb942013A1",
}
for sym, addr in tokens.items():
    url = f"https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/base/assets/{addr}/logo.png"
    resp = requests.head(url, timeout=10)
    print(f"{sym}: {resp.status_code} - {url}")
