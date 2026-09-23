"""Axiom (axiom.trade) - memecoin trading terminal. Not quotable.
Every axiom.trade page (/, /bridge) returns HTTP 403 with a Cloudflare "Performing security verification"
bot challenge in a fresh Playwright context (probe/axiom_home.png, probe/axiom_bridge.png); not bypassed.
Official docs (docs.axiom.trade) have no bridge / cross-chain transfer page: only in-wallet "Convert" (crypto->USDC
swap) and a Hyperliquid perps deposit (SOL->USDC on Hyperliquid), both inside the logged-in wallet modal.
Third-party guides mention SOL<->BNB moves inside the multi-chain wallet, but that is only reachable after signup
(email / Google / Phantom), i.e. login required.
"""
ADAPTER = None
BLOCKED = {
    "bridg_id": "axiom",
    "kind": "platform",
    "reason": "bot protection + login required: axiom.trade serves a Cloudflare bot-verification page (HTTP 403) "
              "to a fresh browser; its official docs list no bridge/cross-chain transfer feature (only in-wallet "
              "Convert/swap and a Hyperliquid perps deposit), and any wallet features need an Axiom account.",
    "url": "https://axiom.trade/",
    "checked": "2026-09-23T13:32:00Z",
    "routes": [],
    "unsupported_routes": ["SOL->ETH", "ETH->SOL", "SOL->BSC", "BSC->SOL", "SOL->Base", "Base->SOL"],
    "evidence": ["probe/axiom_home.png", "probe/axiom_bridge.png"],
    "sources": ["https://docs.axiom.trade/llms.txt", "https://docs.axiom.trade/axiom/swap/convert",
                "https://docs.axiom.trade/perpetuals/deposit", "https://docs.axiom.trade/getting-started/signup",
                "https://docs.axiom.trade/faqs"],
}
