"""GMGN (gmgn.ai) - multi-chain memecoin trading terminal (SOL/BSC/Base/ETH...). Not quotable.
gmgn.ai (/ and /bridge) returns HTTP 403 "Sorry, you have been blocked" (Cloudflare) to a fresh Playwright
context (probe/gmgn_home.png, probe/gmgn_bridge.png); not bypassed. Official docs (docs.gmgn.ai) have no bridge
page: per-chain token trading, TG-wallet deposit/withdraw and trading APIs only (API needs an API key).
Trading requires connecting a wallet / logging in.
"""
ADAPTER = None
BLOCKED = {
    "bridg_id": "gmgn",
    "kind": "platform",
    "reason": "bot protection: gmgn.ai blocks a fresh browser with a Cloudflare 'you have been blocked' page "
              "(HTTP 403); official docs list no cross-chain bridge feature (only same-chain token swaps, which "
              "need a connected wallet/login).",
    "url": "https://gmgn.ai/",
    "checked": "2026-09-23T13:32:00Z",
    "routes": [],
    "unsupported_routes": ["SOL->ETH", "ETH->SOL", "SOL->BSC", "BSC->SOL", "SOL->Base", "Base->SOL"],
    "evidence": ["probe/gmgn_home.png", "probe/gmgn_bridge.png"],
    "sources": ["https://docs.gmgn.ai/index", "https://docs.gmgn.ai/llms.txt",
                "https://docs.gmgn.ai/index/tg-wallet-import-export-private-key-deposit-withdraw",
                "https://docs.gmgn.ai/index/cooperation-api-integrate-gmgn-eth-base-bsc-trading-api"],
}
