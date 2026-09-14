"""
sol.lptracker — Orca Whirlpool position tracker for Solana.

Separate stack from vfat-tracker/snuggle-tracker by necessity: no EVM,
no Web3.py, raw Solana JSON-RPC + manual account parsing instead of
ABI calls. See solana_adapter.py for the actual on-chain logic and its
extensive verification notes.

Known gap, on purpose: uncollected/live fee calculation isn't included
yet — a real bug in that math was found but not fully resolved (see
solana_adapter.py's module docstring). Shipping accurate value/range
tracking now rather than holding it back for a fee number that might
be wrong; fees show as "not yet available", not a guessed number.
"""
import os
import time
import base64
import logging

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from dotenv import load_dotenv

import solana_adapter as sa

load_dotenv()

app = Flask(__name__, static_folder="static")
CORS(app)
logging.basicConfig(level=logging.INFO)

_PASSWORD = os.environ.get("PASSWORD", "")
DEFAULT_WALLET = os.environ.get("DEFAULT_WALLET", "").strip()

HISTORY_DIR = os.environ.get("HISTORY_DIR", "/data")
os.makedirs(HISTORY_DIR, exist_ok=True)


@app.before_request
def require_auth():
    if not _PASSWORD:
        return
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Basic "):
        try:
            _, pw = base64.b64decode(auth[6:]).decode().split(":", 1)
            if pw == _PASSWORD:
                return
        except Exception:
            pass
    return Response("Unauthorized", 401, {"WWW-Authenticate": 'Basic realm="sol tracker"'})


# ── GeckoTerminal pricing (Solana network) ──────────────────────────────
import requests

_GECKOTERMINAL_TOKEN_PRICE_URL = "https://api.geckoterminal.com/api/v2/simple/networks/solana/token_price/{}"


def get_token_prices_usd(addresses: list) -> dict:
    """Solana addresses are base58 and case-sensitive — unlike Ethereum's
    case-insensitive hex addresses, lowercasing here corrupts them into a
    different, nonexistent string. Confirmed directly: this exact bug
    (copied from the EVM trackers' pattern) was why pricing silently
    returned nothing — the raw API call works perfectly with correct
    casing preserved throughout."""
    if not addresses:
        return {}
    unique = sorted(set(addresses))
    url = _GECKOTERMINAL_TOKEN_PRICE_URL.format(",".join(unique))
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        token_prices = data.get("data", {}).get("attributes", {}).get("token_prices", {})
        return {addr: float(price) for addr, price in token_prices.items()}
    except Exception as e:
        app.logger.warning("GeckoTerminal price fetch failed: %s", e)
        return {}


def enrich_with_usd(positions: list) -> list:
    all_addresses = []
    for p in positions:
        all_addresses.append(p["token0"]["address"])
        all_addresses.append(p["token1"]["address"])
    prices = get_token_prices_usd(all_addresses)

    for p in positions:
        price0 = prices.get(p["token0"]["address"])
        price1 = prices.get(p["token1"]["address"])
        position_value_usd = None
        if price0 is not None and price1 is not None:
            position_value_usd = p["amount0"] * price0 + p["amount1"] * price1
        p["position_value_usd"] = position_value_usd
    return positions


def compute_portfolio_summary(positions: list) -> dict:
    total_value_usd = sum(p["position_value_usd"] for p in positions if p["position_value_usd"] is not None)
    return {
        "total_value_usd": total_value_usd,
        "position_count": len(positions),
        "out_of_range_count": sum(1 for p in positions if not p["in_range"]),
    }


# ── Fetch all positions for a wallet ────────────────────────────────────
_cache = {}
_stale_cache = {}
CACHE_TTL = 90


def fetch_all_positions(wallet: str):
    discovered = sa.discover_orca_position_mints(wallet)
    positions = []
    for d in discovered:
        try:
            p = sa.fetch_orca_position(d["mint"])
            positions.append(p)
        except Exception as e:
            app.logger.warning("Failed to fetch position %s: %s", d["mint"], e)
    return positions


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/positions")
def api_positions():
    wallet = request.args.get("wallet", "").strip() or DEFAULT_WALLET
    if not wallet:
        return jsonify({"error": "No wallet specified and no default wallet configured"}), 400

    cache_key = f"positions:{wallet}"
    bust = request.args.get("bust", "0") == "1"
    cached = _cache.get(cache_key)
    if not bust and cached and time.time() - cached["fetched_at"] < CACHE_TTL:
        return jsonify({**cached, "cached": True})

    try:
        positions = fetch_all_positions(wallet)
        positions = enrich_with_usd(positions)
    except Exception as e:
        app.logger.error("Position fetch failed for %s: %s", wallet, e)
        stale = _stale_cache.get(cache_key)
        if stale:
            return jsonify({**stale, "cached": True, "stale": True})
        return jsonify({"error": str(e)}), 500

    portfolio = compute_portfolio_summary(positions)
    result = {
        "positions": positions,
        "portfolio": portfolio,
        "fetched_at": time.time(),
    }
    _cache[cache_key] = result
    _stale_cache[cache_key] = result
    return jsonify({**result, "cached": False})


@app.route("/api/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
