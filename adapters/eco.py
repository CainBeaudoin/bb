"""Eco (bridg_id "eco"). Official quoting UI is Eco Portal, https://portal.eco.com (it does quote without a
wallet, e.g. ?oc=BASE&ot=USDC&dc=ETHEREUM&dt=USDC -> 100 USDC in / 100 USDC out, $0 network fee, est. 20 sec).
But its origin/destination chain pickers only list Arbitrum, Base, Celo, Ethereum, Ink, Optimism, Plasma,
Polygon, Sonic, Unichain: no Solana and no BNB Chain, so none of the benchmark's six routes (all have
Solana on one side) can be priced in Eco's own UI.
Evidence: probe/ecoportal.png, probe/eco_destchain.png (chain list), probe/eco_base_eth.png (non-route quote).
"""
ADAPTER = None
BLOCKED = {
    "reason": "Eco Portal (portal.eco.com, Eco's official transfer UI) does not offer Solana or BNB Chain as "
              "origin or destination (chains: Arbitrum, Base, Celo, Ethereum, Ink, Optimism, Plasma, Polygon, "
              "Sonic, Unichain), so no SOL<->ETH/BSC/Base USDC route can be quoted there. The UI itself quotes "
              "without a wallet for supported chains (e.g. Base->Ethereum 100 USDC -> 100 USDC).",
    "url": "https://portal.eco.com/",
    "checked": "2026-09-23T09:27:00Z",
    "routes": [],
    "unsupported_routes": ["SOL->ETH", "ETH->SOL", "SOL->BSC", "BSC->SOL", "SOL->Base", "Base->SOL"],
    "evidence": ["probe/ecoportal.png", "probe/eco_destchain.png", "probe/eco_base_eth.png"],
}
