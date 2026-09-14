"""
Orca Whirlpool position adapter — Solana, not EVM, so this is a
genuinely separate stack from vfat-tracker/snuggle-tracker: raw Solana
JSON-RPC (no solana-py needed beyond `solders` for Pubkey/PDA math),
manual Borsh-shaped struct parsing instead of ABI-based contract calls.

Everything here was verified directly against orca-so/whirlpools' own
GitHub source and cross-checked against real on-chain positions before
being trusted — not assumed from the Uniswap V3 textbook formula
(Orca's checkpoint/tick-array semantics have real, confirmed
differences). See README.md for the specifics and the one known
unresolved gap (live uncollected-fee calculation).
"""
import os
import struct
import base64
import hashlib
import requests
from solders.pubkey import Pubkey

RPC_URL = os.environ.get("SOLANA_RPC", "https://api.mainnet-beta.solana.com")
WHIRLPOOL_PROGRAM = Pubkey.from_string("whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc")
TICK_ARRAY_SIZE = 88
Q64 = 2 ** 64

SPL_TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

# Anchor account discriminators are deterministic: sha256("account:<Name>")[:8].
# Confirmed directly against a real Position account before trusting it.
POSITION_DISCRIMINATOR = hashlib.sha256(b"account:Position").digest()[:8]


def rpc_call(method, params, retries=2):
    last_err = None
    for _ in range(retries + 1):
        try:
            resp = requests.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"{method} failed: {data['error']}")
            return data["result"]
        except Exception as e:
            last_err = e
    raise last_err


def get_account_bytes(pubkey_str):
    result = rpc_call("getAccountInfo", [pubkey_str, {"encoding": "base64"}])
    if result["value"] is None:
        return None
    return base64.b64decode(result["value"]["data"][0])


def get_multiple_account_bytes(pubkey_strs):
    if not pubkey_strs:
        return []
    result = rpc_call("getMultipleAccounts", [pubkey_strs, {"encoding": "base64"}])
    return [base64.b64decode(v["data"][0]) if v else None for v in result["value"]]


# ── Byte helpers (all struct layouts verified against orca-so/whirlpools) ──
def pk_at(raw, o):
    return str(Pubkey(raw[o:o + 32]))


def u16_at(raw, o):
    return struct.unpack_from("<H", raw, o)[0]


def u128_at(raw, o):
    return int.from_bytes(raw[o:o + 16], "little", signed=False)


def i32_at(raw, o):
    return struct.unpack_from("<i", raw, o)[0]


def u64_at(raw, o):
    return struct.unpack_from("<Q", raw, o)[0]


# ── Discovery: find Orca positions for a wallet ─────────────────────────
def discover_orca_position_mints(wallet: str) -> list:
    """Scans the wallet's SPL + Token-2022 accounts for NFT-shaped
    holdings (amount=1, decimals=0), then confirms which ones are
    genuinely Orca positions by deriving the Position PDA and checking
    its discriminator directly — more robust than relying on Metaplex
    metadata, which doesn't even exist for Token-2022-based positions
    (confirmed directly: Orca's newer positions use a Token-2022
    metadata extension instead of a separate Metaplex account)."""
    candidate_mints = []
    for program_id in (SPL_TOKEN_PROGRAM, TOKEN_2022_PROGRAM):
        result = rpc_call("getTokenAccountsByOwner", [
            wallet, {"programId": program_id}, {"encoding": "jsonParsed"},
        ])
        for acc in result.get("value", []):
            info = acc["account"]["data"]["parsed"]["info"]
            if info["tokenAmount"]["uiAmount"] == 1 and info["tokenAmount"]["decimals"] == 0:
                candidate_mints.append(info["mint"])

    confirmed = []
    for mint_str in candidate_mints:
        mint = Pubkey.from_string(mint_str)
        position_pda, _ = Pubkey.find_program_address([b"position", bytes(mint)], WHIRLPOOL_PROGRAM)
        raw = get_account_bytes(str(position_pda))
        if raw is not None and raw[:8] == POSITION_DISCRIMINATOR:
            confirmed.append({"mint": mint_str, "position_pda": str(position_pda)})
    return confirmed


# ── Core math (same formulas as any Uniswap V3 fork — verified identical) ──
def tick_to_sqrt_price(tick: int) -> float:
    return 1.0001 ** (tick / 2)


def amounts_for_liquidity(sqrt_price, sqrt_lower, sqrt_upper, liquidity):
    if sqrt_price <= sqrt_lower:
        amount_a = liquidity * (1 / sqrt_lower - 1 / sqrt_upper)
        amount_b = 0
    elif sqrt_price < sqrt_upper:
        amount_a = liquidity * (1 / sqrt_price - 1 / sqrt_upper)
        amount_b = liquidity * (sqrt_price - sqrt_lower)
    else:
        amount_a = 0
        amount_b = liquidity * (sqrt_upper - sqrt_lower)
    return amount_a, amount_b


_mint_meta_cache = {}


def get_mint_meta(mint_address: str):
    if mint_address in _mint_meta_cache:
        return _mint_meta_cache[mint_address]
    result = rpc_call("getAccountInfo", [mint_address, {"encoding": "jsonParsed"}])
    info = result["value"]["data"]["parsed"]["info"]
    decimals = info["decimals"]
    # jsonParsed doesn't include the symbol — mints don't carry it on-chain
    # directly for SPL tokens (that's Metaplex metadata territory, which
    # legitimately doesn't exist for every token). Well-known ones are
    # hardcoded as a display convenience; unknown ones show the mint's
    # first 4 chars rather than guessing a name.
    known_symbols = {
        "So11111111111111111111111111111111111111112": "SOL",
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
    }
    symbol = known_symbols.get(mint_address, mint_address[:4].upper())
    meta = (symbol, decimals)
    _mint_meta_cache[mint_address] = meta
    return meta


def fetch_orca_position(mint_str: str) -> dict:
    """Core value/range/holdings data for one Orca Whirlpool position.
    Deliberately does NOT include live uncollected-fee calculation —
    that logic has a confirmed-real remaining bug (verified: computed
    values were off by 10-100x against Orca's own UI on two separate
    test positions, root cause partially found and fixed — the
    tick.initialized check — but a second issue remains unresolved).
    Shipping accurate value/range data now rather than holding it back
    for a fee number that might be wrong."""
    mint = Pubkey.from_string(mint_str)
    position_pda, _ = Pubkey.find_program_address([b"position", bytes(mint)], WHIRLPOOL_PROGRAM)
    pos_raw = get_account_bytes(str(position_pda))
    if pos_raw is None or pos_raw[:8] != POSITION_DISCRIMINATOR:
        raise ValueError(f"No valid Position account at {position_pda} for mint {mint_str}")

    whirlpool_addr = pk_at(pos_raw, 8)
    liquidity = u128_at(pos_raw, 72)
    tick_lower = i32_at(pos_raw, 88)
    tick_upper = i32_at(pos_raw, 92)

    wp_raw = get_account_bytes(whirlpool_addr)
    tick_spacing = u16_at(wp_raw, 41)
    fee_rate = u16_at(wp_raw, 45)
    sqrt_price_raw = u128_at(wp_raw, 65)
    tick_current = i32_at(wp_raw, 81)
    token_mint_a = pk_at(wp_raw, 101)
    token_mint_b = pk_at(wp_raw, 181)

    sym_a, dec_a = get_mint_meta(token_mint_a)
    sym_b, dec_b = get_mint_meta(token_mint_b)

    sqrt_price = sqrt_price_raw / Q64
    sqrt_lower = tick_to_sqrt_price(tick_lower)
    sqrt_upper = tick_to_sqrt_price(tick_upper)
    amt_a_raw, amt_b_raw = amounts_for_liquidity(sqrt_price, sqrt_lower, sqrt_upper, liquidity)

    price = (sqrt_price ** 2) * (10 ** (dec_a - dec_b))
    price_lower = (sqrt_lower ** 2) * (10 ** (dec_a - dec_b))
    price_upper = (sqrt_upper ** 2) * (10 ** (dec_a - dec_b))

    in_range = tick_lower <= tick_current < tick_upper

    return {
        "position_mint": mint_str,
        "position_pda": str(position_pda),
        "whirlpool_address": whirlpool_addr,
        "token0": {"address": token_mint_a, "symbol": sym_a, "decimals": dec_a},
        "token1": {"address": token_mint_b, "symbol": sym_b, "decimals": dec_b},
        "fee_tier": fee_rate,  # hundredths of a bip, same convention as EVM trackers tonight
        "tick_lower": tick_lower,
        "tick_upper": tick_upper,
        "current_tick": tick_current,
        "in_range": in_range,
        "liquidity": liquidity,
        "amount0": amt_a_raw / (10 ** dec_a),
        "amount1": amt_b_raw / (10 ** dec_b),
        "current_price": price,
        "price_lower": price_lower,
        "price_upper": price_upper,
        # Deliberately not computed yet — see module docstring.
        "uncollected_fees0": None,
        "uncollected_fees1": None,
        "fees_available": False,
    }
