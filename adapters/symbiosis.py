"""Symbiosis (app.symbiosis.finance) adapter.

URL preselects the route:
  https://app.symbiosis.finance/swap?chainIn=<Solana|Ethereum|BNB|Base>&chainOut=...&tokenIn=<addr>&tokenOut=<addr>
Symbiosis lists Solana USDC under a synthetic EVM-style id 0x...0003 (chainId 5426) whose attributes map to
EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v; BSC USDC is Binance-Peg 0x8ac7...d580d (18 dp); ETH/Base native USDC.
The quote shows without a wallet. "out" = the "To" amount field; the details row (Min received) is expanded
once (a pure disclosure toggle) to capture Fee (USD, already deducted), price and ETA.
We never click "Connect Wallet", "Apply" (slippage) or type a recipient address.
"""
import re
from sites import CHAINS, NUM, fnum, body_text, input_values, type_into

CH = {"SOL": "Solana", "ETH": "Ethereum", "BSC": "BNB", "Base": "Base"}
TOK = {"SOL": "0x0000000000000000000000000000000000000003", "ETH": CHAINS["ETH"]["usdc"],
       "BSC": CHAINS["BSC"]["usdc"], "Base": CHAINS["Base"]["usdc"]}


class Symbiosis:
    name = "symbiosis"
    bridg_id = "symbiosis"
    crop = (480, 120, 440, 700)
    label_url = None
    # SOL->BSC and SOL->Base show "This swap is not available" (checked 2026-09-23 at 100 and 1000 USDC)
    routes = [("SOL", "ETH"), ("ETH", "SOL"), ("BSC", "SOL"), ("Base", "SOL")]

    async def setup(self, page, route):
        s, d = route
        await page.goto(f"https://app.symbiosis.finance/swap?chainIn={CH[s]}&chainOut={CH[d]}"
                        f"&tokenIn={TOK[s]}&tokenOut={TOK[d]}", wait_until="domcontentloaded")
        await page.get_by_text(f"To: {CH[d]}").first.wait_for(timeout=30000)
        await page.get_by_text(f"From: {CH[s]}").first.wait_for(timeout=15000)
        await page.wait_for_timeout(2000)

    async def enter(self, page):
        await type_into(page.locator("input[placeholder='0.0']:visible").first)

    async def read(self, page):
        vals = [v["v"] for v in await input_values(page) if v["p"] == "0.0"]
        if len(vals) < 2 or not re.fullmatch(NUM, vals[1] or "") or fnum(vals[1]) == 0 or fnum(vals[0] or "0") != 100:
            return None
        t = await body_text(page)
        if "Min received" not in t:
            return None
        if "Estimated time:" not in t:
            try:
                await page.get_by_text("Min received").first.click(timeout=2000)
                await page.wait_for_timeout(800)
                t = await body_text(page)
            except Exception:
                pass
        g = lambda rx: (re.search(rx, t) or [None, None])[1]
        route = re.search(r"Best route\n([^\n]+)\n([^\n]+)", t)
        return {"out": fnum(vals[1]), "amount_in": fnum(vals[0]),
                "min_received": fnum(g(rf"Min received\n({NUM}) USDC")) if g(rf"Min received\n({NUM}) USDC") else None,
                "fee_usd_deducted": g(r"Fee:\n\$?([\d.,]+)"), "eta": g(r"Estimated time:\n([^\n]+)"),
                "price_impact": g(r"Price impact\n([^\n]+)"), "slippage": g(r"Slippage\n([^\n]+)"),
                "route": " ".join(route.groups()) if route else None,
                "fixed_fee_on_top": 0.0, "fixed_fee_token": None,
                "display_decimals": len(vals[1].split(".")[1]) if "." in vals[1] else 0}


ADAPTER = Symbiosis()
