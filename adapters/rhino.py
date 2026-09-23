"""Rhino.fi — BLOCKED: the retail bridge app is gone.

https://app.rhino.fi (and /bridge?...) redirects to https://rhino.fi/b2c-app-deprecation:
"As of August 2026, the Rhino.fi retail offering has been deprecated" — B2B only (Console needs an account).
Evidence: probe/rhino_BLOCKED.png, probe/rhino_BLOCKED.txt.
"""
ADAPTER = None
BLOCKED = {
    "reason": "No public web UI: app.rhino.fi redirects to rhino.fi/b2c-app-deprecation "
              "(retail app deprecated Aug 2026; B2B/Console only, requires an account)",
    "url": "https://app.rhino.fi/bridge?token=USDC&chainIn=SOLANA&chainOut=ETHEREUM",
    "checked": "2026-09-23T09:22:44Z",
    "routes": ["SOL-ETH", "ETH-SOL", "SOL-BSC", "BSC-SOL", "SOL-Base", "Base-SOL"],
}
