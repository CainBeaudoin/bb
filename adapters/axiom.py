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


# Signed-in re-check 2026-09-23T14:07:33Z
BLOCKED["reason"] = "PARTIAL — no 100 USDC quote without funds. Signed-in check (user logged in; built-in browser, 2026-09-23): Axiom 'Exchange' has a cross-chain Convert (e.g. 'Swap USDC on Solana for USDC on Ethereum', indicative 1 USDC = 1.0000 USDC) but the amount field clamps to the wallet balance (0), so 100 can't be priced. Deposit auto-bridges EVM→Solana and shows fees only at its minimum: ETH→SOL USDC ($3 min) ~26s, impact −0.388%, fees ~$0.27 (gas $0.27, routing/liquidity <$0.01); BSC→SOL ($2 min) ~26s, impact −8.357%, fees ~$0.21 (gas); Base→SOL ($2 min) ~26s, impact −0.455%, fees ~$0.02. Indicative only — not comparable to a 100 USDC quote."
BLOCKED["checked"] = '2026-09-23T14:07:33Z'
