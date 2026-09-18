import requests
import json
import sys

for endpoint in ["/api/snuggle/positions", "/api/maxfi/positions"]:
    resp = requests.get(f"https://snuggle.lptracker.info{endpoint}", auth=("", "J__9EXrwEA77ScMf"), timeout=20)
    data = resp.json()
    sys.stdout.write(f"\n########## {endpoint} (status {resp.status_code}) ##########\n")
    portfolio = data.get("portfolio", {})
    sys.stdout.write(f"PORTFOLIO: {json.dumps(portfolio)}\n")
    for i, p in enumerate(data.get("positions", [])):
        sys.stdout.write(f"\n---- position {i} (token_id={p.get('token_id')}) ----\n")
        keys = ["in_range", "position_value_usd", "baseline_value_usd", "pnl_usd", "pnl_pct",
                "cumulative_fees_usd", "lifetime_apr_pct", "days_held", "deposit_timestamp",
                "out_of_range_seconds", "out_of_range_since", "range_width_pct",
                "is_staked", "pending_reward_usd", "current_price", "price_lower", "price_upper",
                "pool_address", "fee_tier"]
        for k in keys:
            sys.stdout.write(f"  {k}: {p.get(k)}\n")
    sys.stdout.flush()
