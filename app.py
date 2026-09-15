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
import json
import fcntl
import base64
import logging
import threading

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
_history_lock = threading.Lock()
SNAPSHOT_INTERVAL = 3600  # 1 hour


def _read_json_locked(path: str, default):
    try:
        with open(path, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                return json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _write_json_locked(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(data, f)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _history_file_path(name: str) -> str:
    return os.path.join(HISTORY_DIR, f"history_{name}.json")


def _closed_positions_file_path() -> str:
    return os.path.join(HISTORY_DIR, "closed_positions.json")


def _known_positions_file_path() -> str:
    return os.path.join(HISTORY_DIR, "known_positions.json")


def append_history_snapshot(name: str, snapshot: dict):
    path = _history_file_path(name)
    with _history_lock:
        history = _read_json_locked(path, [])
        history.append(snapshot)
        _write_json_locked(path, history)


def load_history(name: str) -> list:
    return _read_json_locked(_history_file_path(name), [])


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

        fees_usd = None
        if p.get("fees_available") and price0 is not None and price1 is not None:
            fees_usd = p["uncollected_fees0"] * price0 + p["uncollected_fees1"] * price1
        p["uncollected_fees_usd"] = fees_usd

        # Range-bar support fields, same convention as vfat-tracker.
        cp, pl, pu = p.get("current_price"), p.get("price_lower"), p.get("price_upper")
        pct_from_lower = pct_from_upper = None
        if cp and pl is not None and pu is not None and cp > 0:
            pct_from_lower = (cp - pl) / cp * 100.0
            pct_from_upper = (pu - cp) / cp * 100.0
        p["pct_from_lower"] = pct_from_lower
        p["pct_from_upper"] = pct_from_upper

        if pl and pu and pl > 0:
            p["range_width_pct"] = (pu - pl) / pl * 100.0
        else:
            p["range_width_pct"] = None
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


def attach_estimated_apr(positions: list) -> list:
    """Instant APR estimate from current pool activity — same approach
    as vfat-tracker tonight: most recent day's volume × fee rate × your
    share of the pool's active liquidity. Doesn't need history/baseline
    tracking, unlike a true 'since deposited' APR."""
    volume_cache = {}
    for p in positions:
        if not p["in_range"]:
            p["estimated_apr_pct"] = 0.0
            continue
        if not p.get("pool_liquidity") or not p.get("position_value_usd"):
            p["estimated_apr_pct"] = None
            continue

        pool_addr = p["whirlpool_address"]
        if pool_addr not in volume_cache:
            try:
                volume_cache[pool_addr] = sa.get_pool_volume_usd_1d(pool_addr)
            except Exception as e:
                app.logger.warning("Pool volume fetch failed for estimated APR (%s): %s", pool_addr, e)
                volume_cache[pool_addr] = None

        daily_volume_usd = volume_cache[pool_addr]
        if daily_volume_usd is None:
            p["estimated_apr_pct"] = None
            continue

        fee_fraction = p["fee_tier"] / 1_000_000
        daily_pool_fees_usd = daily_volume_usd * fee_fraction
        share = p["liquidity"] / p["pool_liquidity"]
        your_daily_fees_usd = daily_pool_fees_usd * share
        p["estimated_apr_pct"] = (your_daily_fees_usd / p["position_value_usd"]) * 365 * 100
    return positions


def capture_snapshot():
    """Runs hourly. Records a baseline (value + uncollected-fees, both
    USD) for any position that doesn't have one yet — same self-healing
    approach as vfat-tracker: never overwrites an existing baseline,
    and resets it on a detected deposit/withdrawal (liquidity change)
    so P&L doesn't count your own capital moves as gains or losses."""
    if not DEFAULT_WALLET:
        return
    try:
        positions = fetch_all_positions(DEFAULT_WALLET)
        positions = enrich_with_usd(positions)
    except Exception as e:
        app.logger.warning("Snapshot capture failed: %s", e)
        return

    now = time.time()
    with _history_lock:
        known = _read_json_locked(_known_positions_file_path(), {})
        current_keys = {p["position_mint"] for p in positions}
        closed_now = [k for k in known if k not in current_keys]

        if closed_now:
            closed_list = _read_json_locked(_closed_positions_file_path(), [])
            for key in closed_now:
                last_known = known[key]
                closed_list.append({
                    "key": key,
                    "pool": last_known.get("pool"),
                    "closed_at": now,
                    "last_value_usd": last_known.get("last_value_usd"),
                })
                _append_closed_marker(key, now)
            _write_json_locked(_closed_positions_file_path(), closed_list)

        for p in positions:
            key = p["position_mint"]
            prior = known.get(key, {})
            baseline_value_usd = prior.get("baseline_value_usd")
            baseline_fees_usd = prior.get("baseline_fees_usd")
            baseline_ts = prior.get("baseline_ts")

            prior_liquidity = prior.get("last_liquidity")
            liquidity_changed = prior_liquidity is not None and p["liquidity"] != prior_liquidity

            if (baseline_value_usd is None or liquidity_changed) and p["position_value_usd"] is not None:
                baseline_value_usd = p["position_value_usd"]
                baseline_fees_usd = p["uncollected_fees_usd"] or 0.0
                baseline_ts = now
            known[key] = {
                "pool": f"{p['token0']['symbol']}/{p['token1']['symbol']}",
                "whirlpool_address": p["whirlpool_address"],
                "last_liquidity": p["liquidity"],
                "baseline_value_usd": baseline_value_usd,
                "baseline_fees_usd": baseline_fees_usd,
                "baseline_ts": baseline_ts,
                "last_value_usd": p["position_value_usd"],
                "last_seen": now,
            }
        _write_json_locked(_known_positions_file_path(), known)

    portfolio = compute_portfolio_summary(positions)
    append_history_snapshot("portfolio", {
        "ts": now,
        "total_value_usd": portfolio["total_value_usd"],
        "position_count": portfolio["position_count"],
        "out_of_range_count": portfolio["out_of_range_count"],
    })

    for p in positions:
        append_history_snapshot(f"pos_{p['position_mint']}", {
            "ts": now,
            "value_usd": p["position_value_usd"],
            "fees_usd": p["uncollected_fees_usd"],
            "in_range": p["in_range"],
        })


def _append_closed_marker(key: str, ts: float):
    path = _history_file_path(f"pos_{key}")
    history = _read_json_locked(path, [])
    history.append({"ts": ts, "key": key, "closed": True})
    _write_json_locked(path, history)


def _snapshot_loop():
    while True:
        try:
            capture_snapshot()
        except Exception as e:
            app.logger.error("Snapshot loop error: %s", e)
        time.sleep(SNAPSHOT_INTERVAL)


def attach_pnl_and_apr(positions: list) -> list:
    """Same approach as vfat-tracker: P&L and APR are 'since we started
    tracking,' not true lifetime figures (no cumulative-fee counter
    exists on-chain for a raw position). Read-only — the background
    snapshot loop is the sole writer of known_positions.json."""
    known = _read_json_locked(_known_positions_file_path(), {})
    now = time.time()
    for p in positions:
        entry = known.get(p["position_mint"])
        baseline_value = entry.get("baseline_value_usd") if entry else None
        baseline_fees = entry.get("baseline_fees_usd") if entry else None
        baseline_ts = entry.get("baseline_ts") if entry else None

        pnl_usd = pnl_pct = apr_pct = None
        if baseline_value is not None and baseline_value > 0 and p["position_value_usd"] is not None:
            pnl_usd = p["position_value_usd"] - baseline_value
            pnl_pct = pnl_usd / baseline_value * 100.0

        if not p["in_range"]:
            apr_pct = 0.0
        elif (baseline_fees is not None and baseline_ts is not None
                and p["uncollected_fees_usd"] is not None and p["position_value_usd"]):
            days_tracked = (now - baseline_ts) / 86400.0
            fees_earned = max(0.0, p["uncollected_fees_usd"] - baseline_fees)
            if days_tracked > 0.5 and p["position_value_usd"] > 0:
                apr_pct = fees_earned / p["position_value_usd"] * (365.0 / days_tracked) * 100.0

        p["baseline_value_usd"] = baseline_value
        p["pnl_usd"] = pnl_usd
        p["pnl_pct"] = pnl_pct
        p["apr_pct"] = apr_pct
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
        positions = attach_estimated_apr(positions)
        positions = attach_pnl_and_apr(positions)
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


_RANGE_TO_SECONDS = {"7d": 7 * 86400, "30d": 30 * 86400, "90d": 90 * 86400, "all": None}
_VOLUME_RANGE_DAYS = {"7d": 7, "30d": 30, "60d": 60, "90d": 90, "180d": 180}
_POOL_VOLUME_CACHE = {}
_POOL_VOLUME_CACHE_TTL = 1800


def get_pool_volume_usd(pool_address: str, days: int) -> list:
    cache_key = f"{pool_address}:{days}"
    cached = _POOL_VOLUME_CACHE.get(cache_key)
    if cached and time.time() - cached["fetched_at"] < _POOL_VOLUME_CACHE_TTL:
        return cached["candles"]
    candles = sa.get_pool_volume_candles(pool_address, days)
    _POOL_VOLUME_CACHE[cache_key] = {"candles": candles, "fetched_at": time.time()}
    return candles


@app.route("/api/history")
def api_history():
    range_key = request.args.get("range", "30d")
    if range_key not in _RANGE_TO_SECONDS:
        return jsonify({"error": "range must be one of: 7d, 30d, 90d, all"}), 400
    history = load_history("portfolio")
    window_seconds = _RANGE_TO_SECONDS[range_key]
    if window_seconds is not None:
        cutoff = time.time() - window_seconds
        history = [s for s in history if s["ts"] >= cutoff]
    return jsonify({"snapshots": history, "range": range_key})


@app.route("/api/history/<mint>")
def api_position_history(mint):
    range_key = request.args.get("range", "30d")
    if range_key not in _RANGE_TO_SECONDS:
        return jsonify({"error": "range must be one of: 7d, 30d, 90d, all"}), 400
    history = load_history(f"pos_{mint}")
    window_seconds = _RANGE_TO_SECONDS[range_key]
    if window_seconds is not None:
        cutoff = time.time() - window_seconds
        history = [s for s in history if s["ts"] >= cutoff]
    return jsonify({"snapshots": history, "range": range_key, "mint": mint})


@app.route("/api/closed")
def api_closed_positions():
    closed = _read_json_locked(_closed_positions_file_path(), [])
    closed_sorted = sorted(closed, key=lambda c: c["closed_at"], reverse=True)
    return jsonify({"closed": closed_sorted})


@app.route("/api/pool-volume/<mint>")
def api_pool_volume(mint):
    range_key = request.args.get("range", "30d")
    if range_key not in _VOLUME_RANGE_DAYS:
        return jsonify({"error": "range must be one of: 7d, 30d, 60d, 90d, 180d"}), 400

    known = _read_json_locked(_known_positions_file_path(), {})
    entry = known.get(mint)
    pool_address = entry.get("whirlpool_address") if entry else None
    if not pool_address:
        return jsonify({"error": "Pool address not yet known for this position — "
                                  "check back after the next snapshot cycle."}), 404
    try:
        candles = get_pool_volume_usd(pool_address, _VOLUME_RANGE_DAYS[range_key])
    except Exception as e:
        app.logger.warning("Pool volume fetch failed for %s: %s", pool_address, e)
        return jsonify({"error": "Volume data unavailable right now"}), 502
    return jsonify({"candles": candles, "range": range_key, "mint": mint})


_snapshot_thread = threading.Thread(target=_snapshot_loop, daemon=True)
_snapshot_thread.start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
