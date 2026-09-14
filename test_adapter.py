"""One-time verification: does the consolidated fetch_orca_position()
correctly reproduce known-good values for both real test positions?"""
import solana_adapter as sa

WALLET = "FF9V5DXtZGC5nVwBKg5WBRzqo1NirJxqyaS7VTAAa2z4"

print("--- Discovery ---")
positions = sa.discover_orca_position_mints(WALLET)
print(f"Found {len(positions)} confirmed Orca positions:")
for p in positions:
    print(f"  {p}")

print("\n--- Fetch each ---")
for p in positions:
    data = sa.fetch_orca_position(p["mint"])
    price = data["current_price"]
    value = data["amount0"] * price + data["amount1"]  # rough, token1=USDC-ish only when dec_b small
    print(f"\nMint {p['mint']}:")
    print(f"  {data['token0']['symbol']}/{data['token1']['symbol']}, in_range={data['in_range']}")
    print(f"  Holdings: {data['amount0']:.6f} {data['token0']['symbol']} + {data['amount1']:.6f} {data['token1']['symbol']}")
    print(f"  Price: {price:.4f}")
    print(f"  Rough value: ${value:.2f}")
