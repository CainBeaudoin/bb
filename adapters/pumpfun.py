"""Pump.fun (pump.fun) - Solana memecoin launchpad/terminal. Not quotable.
Solana-only trading. Since Mar 2026 it has a MoonPay-powered "Cross Chain Deposit" (funds a Pump.fun account
from Arbitrum, Base, Bitcoin, BNB, Ethereum, Hyperliquid, Plasma, Polygon, Solana) - inbound to the user's Solana
account only, so SOL->ETH/BSC/Base is impossible; and the deposit flow lives in the signed-in account (Sign in),
behind a first-visit Terms/18+ "Continue" modal (probe/pumpfun_home.png) that we must not accept.
"""
ADAPTER = None
BLOCKED = {
    "bridg_id": "pumpfun",
    "kind": "platform",
    "reason": "Solana-only + login required: no general bridge; the only cross-chain feature is a MoonPay "
              "'Cross Chain Deposit' into the user's own Pump.fun (Solana) account, which needs sign-in (and "
              "accepting the ToS modal). SOL->EVM directions are not offered at all.",
    "url": "https://pump.fun/",
    "checked": "2026-09-23T13:32:00Z",
    "routes": [],
    "unsupported_routes": ["SOL->ETH", "ETH->SOL", "SOL->BSC", "BSC->SOL", "SOL->Base", "Base->SOL"],
    "evidence": ["probe/pumpfun_home.png"],
    "sources": ["https://cryptobriefing.com/moonpay-expands-crypto-funding-options/",
                "https://www.cryptopolitan.com/pump-fun-accepts-tokens-from-nine-chains/",
                "https://thedefiant.io/news/defi/pump-fun-launches-usdc-paired-liquidity-pools-gi72da"],
}
