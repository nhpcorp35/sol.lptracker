"""Final fee calculation attempt with the tick.initialized fix,
explicitly labeled per mint, against both real known positions."""
import solana_adapter as sa
from solders.pubkey import Pubkey

WALLET = "FF9V5DXtZGC5nVwBKg5WBRzqo1NirJxqyaS7VTAAa2z4"
Q64 = 2 ** 64
TICK_ARRAY_SIZE = 88


def tick_array_start_index(tick_index, tick_spacing):
    ticks_in_array = TICK_ARRAY_SIZE * tick_spacing
    return (tick_index // ticks_in_array) * ticks_in_array


def derive_tick_array_pda(whirlpool, start_tick_index):
    seeds = [b"tick_array", bytes(whirlpool), str(start_tick_index).encode()]
    pda, _ = Pubkey.find_program_address(seeds, sa.WHIRLPOOL_PROGRAM)
    return pda


def get_tick(raw, tick_index, start_tick_index, tick_spacing):
    offset_in_array = (tick_index - start_tick_index) // tick_spacing
    off = 12 + offset_in_array * 113
    initialized = raw[off] != 0
    fg_a = sa.u128_at(raw, off + 1 + 16 + 16)
    fg_b = sa.u128_at(raw, off + 1 + 16 + 16 + 16)
    return initialized, fg_a, fg_b


def fee_growth_inside(current_tick, tick_lower, tick_upper, fg_global_a, fg_global_b,
                       lower_init, lower_out_a, lower_out_b, upper_init, upper_out_a, upper_out_b):
    if not lower_init:
        below_a, below_b = fg_global_a, fg_global_b
    elif current_tick < tick_lower:
        below_a = (fg_global_a - lower_out_a) % (2 ** 128)
        below_b = (fg_global_b - lower_out_b) % (2 ** 128)
    else:
        below_a, below_b = lower_out_a, lower_out_b

    if not upper_init:
        above_a, above_b = 0, 0
    elif current_tick < tick_upper:
        above_a, above_b = upper_out_a, upper_out_b
    else:
        above_a = (fg_global_a - upper_out_a) % (2 ** 128)
        above_b = (fg_global_b - upper_out_b) % (2 ** 128)

    inside_a = (fg_global_a - below_a - above_a) % (2 ** 128)
    inside_b = (fg_global_b - below_b - above_b) % (2 ** 128)
    return inside_a, inside_b


for mint_str, label, expected in [
    ("6eeinqbDCX1sHJPuuAqs6Rzs71v2CGCbESJGvXP68UnL", "OLD position", "$0.44"),
    ("CsezH1MBuFYece5kyFm2bTAoJMYEfdEs1yGJwsbzNGnG", "NEW position", "<$0.01"),
]:
    print(f"\n{'='*60}")
    print(f"{label} ({mint_str}) — Orca UI shows {expected}")
    print('='*60)

    mint = Pubkey.from_string(mint_str)
    position_pda, _ = Pubkey.find_program_address([b"position", bytes(mint)], sa.WHIRLPOOL_PROGRAM)
    pos_raw = sa.get_account_bytes(str(position_pda))

    whirlpool_addr = sa.pk_at(pos_raw, 8)
    liquidity = sa.u128_at(pos_raw, 72)
    tick_lower = sa.i32_at(pos_raw, 88)
    tick_upper = sa.i32_at(pos_raw, 92)
    fee_growth_checkpoint_a = sa.u128_at(pos_raw, 96)
    fee_owed_a = sa.u64_at(pos_raw, 112)
    fee_growth_checkpoint_b = sa.u128_at(pos_raw, 120)
    fee_owed_b = sa.u64_at(pos_raw, 136)

    wp_raw = sa.get_account_bytes(whirlpool_addr)
    tick_current = sa.i32_at(wp_raw, 81)
    fg_global_a = sa.u128_at(wp_raw, 165)
    fg_global_b = sa.u128_at(wp_raw, 245)
    dec_a = 9  # SOL
    dec_b = 6  # USDC

    start_lower = tick_array_start_index(tick_lower, 4)
    start_upper = tick_array_start_index(tick_upper, 4)
    pda_lower = derive_tick_array_pda(Pubkey.from_string(whirlpool_addr), start_lower)
    pda_upper = derive_tick_array_pda(Pubkey.from_string(whirlpool_addr), start_upper)

    if str(pda_lower) == str(pda_upper):
        raw_lower = raw_upper = sa.get_account_bytes(str(pda_lower))
    else:
        raw_lower, raw_upper = sa.get_multiple_account_bytes([str(pda_lower), str(pda_upper)])

    lower_init, lower_out_a, lower_out_b = get_tick(raw_lower, tick_lower, start_lower, 4)
    upper_init, upper_out_a, upper_out_b = get_tick(raw_upper, tick_upper, start_upper, 4)

    print(f"tick_lower={tick_lower} (init={lower_init}), tick_upper={tick_upper} (init={upper_init})")
    print(f"lower_out_a={lower_out_a}, upper_out_a={upper_out_a}")

    fg_inside_a, fg_inside_b = fee_growth_inside(
        tick_current, tick_lower, tick_upper, fg_global_a, fg_global_b,
        lower_init, lower_out_a, lower_out_b, upper_init, upper_out_a, upper_out_b,
    )

    live_owed_a = fee_owed_a + liquidity * ((fg_inside_a - fee_growth_checkpoint_a) % (2 ** 128)) // Q64
    live_owed_b = fee_owed_b + liquidity * ((fg_inside_b - fee_growth_checkpoint_b) % (2 ** 128)) // Q64

    fee_a_human = live_owed_a / (10 ** dec_a)
    fee_b_human = live_owed_b / (10 ** dec_b)
    print(f"\nComputed uncollected fees: {fee_a_human:.8f} SOL + {fee_b_human:.6f} USDC")
    print(f"Rough USD (SOL~$104): ${fee_a_human * 104 + fee_b_human:.4f}  (Orca UI says {expected})")
