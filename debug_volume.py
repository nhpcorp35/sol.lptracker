import solana_adapter as sa

WALLET = "FF9V5DXtZGC5nVwBKg5WBRzqo1NirJxqyaS7VTAAa2z4"
positions = sa.discover_orca_position_mints(WALLET)
for p in positions:
    data = sa.fetch_orca_position(p["mint"])
    pool_addr = data["whirlpool_address"]
    print(f"\nMint {p['mint']}: pool={pool_addr}")
    try:
        vol = sa.get_pool_volume_usd_1d(pool_addr)
        print(f"  1-day volume: ${vol}")
    except Exception as e:
        print(f"  FAILED: {e}")
