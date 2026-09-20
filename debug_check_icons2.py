import requests

urls = {
    "UNI (ethereum mainnet)": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/ethereum/assets/0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984/logo.png",
    "Base chain logo": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/base/info/logo.png",
    "cbBTC (ethereum mainnet)": "https://raw.githubusercontent.com/trustwallet/assets/master/blockchains/ethereum/assets/0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf/logo.png",
}
for label, url in urls.items():
    resp = requests.head(url, timeout=10)
    print(f"{label}: {resp.status_code}")
