# sol.lptracker

Orca Whirlpool position tracker for Solana. Separate stack from
vfat-tracker/snuggle-tracker by necessity — no EVM, no Web3.py, raw
Solana JSON-RPC + manual account parsing instead of ABI calls.

## What works, verified against real positions

- Discovery: finds a wallet's Orca positions by checking every
  NFT-shaped token account against the Position PDA + discriminator
  directly — doesn't depend on Metaplex metadata (which doesn't exist
  for Token-2022-based positions, confirmed directly).
- Value, holdings, price range, in-range status, live uncollected
  fees, estimated APR: all matched Orca's own live UI closely on two
  separate real test positions (value within normal price drift; fees
  computed to the exact penny — $0.4409 vs Orca's own $0.44).

## The fee-calculation bug, resolved

Every struct layout (Position, Whirlpool, TickArray, Tick) was
independently confirmed against the official `@orca-so/whirlpools-sdk`'s
own published IDL. That's what caught the real bug: the `TickArray`
account's actual field order is `discriminator + startTickIndex +
ticks[88] + whirlpool` — the whirlpool pubkey comes AFTER the ticks
array, not before it. I had it second, which silently shifted every
single tick read by 32 bytes for an entire debugging session. A
byte-size coincidence (44 + 88×113 = 9988, matching the real account
size) made the wrong layout look confirmed when it wasn't — that
check only validates total size, not internal field order.

Found by reading the actual SDK source (from `nhpcorp35/v3.lptracker`,
a working reference implementation) rather than continuing to guess.
