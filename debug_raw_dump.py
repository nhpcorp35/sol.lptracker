"""Fresh look: dump a large contiguous raw byte region and inspect
directly, rather than trust derived values at computed offsets."""
import base64
import requests
import solana_adapter as sa

WALLET = "FF9V5DXtZGC5nVwBKg5WBRzqo1NirJxqyaS7VTAAa2z4"
positions = sa.discover_orca_position_mints(WALLET)
mint_str = positions[0]["mint"]

from solders.pubkey import Pubkey
mint = Pubkey.from_string(mint_str)
position_pda, _ = Pubkey.find_program_address([b"position", bytes(mint)], sa.WHIRLPOOL_PROGRAM)
pos_raw = sa.get_account_bytes(str(position_pda))
whirlpool_addr = sa.pk_at(pos_raw, 8)
tick_lower = sa.i32_at(pos_raw, 88)
tick_upper = sa.i32_at(pos_raw, 92)

wp_raw = sa.get_account_bytes(whirlpool_addr)
tick_spacing = sa.u16_at(wp_raw, 41)

def start_idx(tick, spacing):
    return (tick // (88 * spacing)) * (88 * spacing)

start_lower = start_idx(tick_lower, tick_spacing)
seeds = [b"tick_array", bytes(Pubkey.from_string(whirlpool_addr)), str(start_lower).encode()]
pda_lower, _ = Pubkey.find_program_address(seeds, sa.WHIRLPOOL_PROGRAM)

raw = sa.get_account_bytes(str(pda_lower))
print(f"Total account length: {len(raw)}")
print(f"\n--- Bytes 44 to 44+400 (should cover ~3.5 full ticks of REAL varying data) ---")
chunk = raw[44:44+400]
print(chunk.hex())

print(f"\n--- Same check: bytes 44+113 to 44+113+400 (next tick onward) ---")
chunk2 = raw[44+113:44+113+400]
print(chunk2.hex())

print(f"\nAre these two chunks identical? {chunk == chunk2}")
print(f"\n--- Last 200 bytes of the account (should be tick #87, near the end) ---")
print(raw[-200:].hex())
