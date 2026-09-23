"""NEAR Intents (bridg_id "near-intents").
- app.near-intents.org now redirects to near-intents.org, which only shows "NEAR Intents has moved to near.com"
  (site decommissioned 2026-06-30).                                         -> probe/nearx.png
- near.com/swap (the successor swap UI) redirects to /login ("Sign in or create an account", passkey/wallet).
                                                                            -> probe/near_swap.png
- near.com's landing page has a public "Live demo" swap, but its token list has a single chain-less "USDC"
  (backed by nep141:eth-0xa0b8...omft.near, i.e. Ethereum USDC) and no network selector, so a Solana-USDC ->
  EVM-USDC (or reverse) quote cannot be selected.                           -> probe/near_demo.png, near_pick2.png
"""
ADAPTER = None
BLOCKED = {
    "reason": "Official NEAR Intents app (app.near-intents.org) is decommissioned and just points to near.com; "
              "near.com's swap requires signing in / creating an account (passkey or wallet). The public landing-page "
              "demo swap has no chain selector (one unified USDC = Ethereum USDC), so no SOL<->EVM USDC route can be quoted.",
    "url": "https://near.com/swap",
    "checked": "2026-09-23T09:27:00Z",
    "routes": ["SOL->ETH", "ETH->SOL", "SOL->BSC", "BSC->SOL", "SOL->Base", "Base->SOL"],
    "evidence": ["probe/nearx.png", "probe/near_swap.png", "probe/near_demo.png", "probe/near_pick2.png"],
}
