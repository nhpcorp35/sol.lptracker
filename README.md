# sol.lptracker

Orca Whirlpool position tracker for Solana. Separate stack from
vfat-tracker/snuggle-tracker by necessity — no EVM, no Web3.py, raw
Solana JSON-RPC + manual account parsing instead of ABI calls.

## What works, verified against real positions

- Discovery: finds a wallet's Orca positions by checking every
  NFT-shaped token account against the Position PDA + discriminator
  directly — doesn't depend on Metaplex metadata (which doesn't exist
  for Token-2022-based positions, confirmed directly).
- Value, holdings, price range, in-range status: matched Orca's own
  live UI within normal price drift (~0.2-0.7%) on two separate real
  test positions.

## Known gap: uncollected/live fee calculation

Not implemented. A real bug was found and partially fixed (missing
`tick.initialized` check in the fee-growth-inside calculation — see
git history for the full debugging trail), which took the error from
~$108 down to ~$2.59 on a test position that should show <$0.01. But
a second, unresolved issue remains: every slot in a scanned tick array
returned an identical `fee_growth_outside` value, which shouldn't
happen for real per-tick data — ruled out caching, PDA derivation,
Fixed-vs-Dynamic tick array confusion, and slot alignment as causes,
without finding the actual root cause.

Rather than ship a fee number that might be wrong, this tracker
deliberately shows "not yet available" for fees until that's resolved.
