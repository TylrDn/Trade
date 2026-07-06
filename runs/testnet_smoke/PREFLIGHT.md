# Kraken pre-flight (2026-07-05)

## Instrument catalog

- **Production API** (`futures.kraken.com/derivatives/api/v3/instruments`): `PF_XBTUSD` and `PI_XBTUSD` both listed (324 instruments).
- **Demo API** (`demo-futures.kraken.com`): returned HTTP 503 during automated check — retry at operator smoke time.

## Decision

Proceed with **`PF_XBTUSD.KRAKEN`** as the default Kraken staging instrument (USD linear perp). Inverse `PI_XBTUSD` fallback requires a separate scope expansion per plan.
