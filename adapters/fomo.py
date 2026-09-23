"""FOMO - official app is fomo.family (FOMO Labs Inc., "social-first trading app", iOS/Android + web).
(docs.onfomo.com appears to be a different "FOMO" product; it too is account-only with no bridge.) Not quotable.
fomo.family is an account-based app (email / Apple ID login) with one unified USD balance usable on Solana, Base,
BNB Chain and Monad; its own docs say "No manual bridging ... No bridges needed" - there is no user-facing bridge
or chain-to-chain USDC transfer quote. Crypto deposits are USDC-only on supported networks; withdrawals go to a
wallet address. All of this is behind login (probe/fomo_home.png shows only Login / Start trading / Download).
"""
ADAPTER = None
BLOCKED = {
    "bridg_id": "fomo",
    "kind": "platform",
    "reason": "no bridge feature + login required: fomo.family abstracts chains behind a single USD balance "
              "(Solana/Base/BNB/Monad, 'no bridges needed'); no cross-chain USDC transfer quote exists, and "
              "deposit/withdraw/trade all require creating an account. Ethereum mainnet not supported.",
    "url": "https://fomo.family/",
    "checked": "2026-09-23T13:32:00Z",
    "routes": [],
    "unsupported_routes": ["SOL->ETH", "ETH->SOL", "SOL->BSC", "BSC->SOL", "SOL->Base", "Base->SOL"],
    "evidence": ["probe/fomo_home.png"],
    "sources": ["https://fomo.family/answers/what-is-cross-chain-crypto-trading",
                "https://fomo.family/blog/learn/a-guide-to-deposits-and-withdrawals",
                "https://fomo.family/blog/learn/fomo-vs-phantom-wallet"],
}
