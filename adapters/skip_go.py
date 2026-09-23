"""Skip Go (go.skip.build) adapter. Route preselected via URL params (src_chain/src_asset/dest_chain/dest_asset)."""
import re
from sites import CHAINS, NUM, fnum, body_text, input_values, type_into  # noqa: F401

SKIP_CHAIN = {"SOL": "solana", "ETH": "1", "BSC": "56", "Base": "8453"}


class SkipGo:
    name = "skip-go"
    bridg_id = "skip-go"
    crop = (455, 340, 490, 350)
    # BSC USDC (Binance-Peg, 0x8ac7...) is listed but Skip's router returns "no routes found" for
    # SOL<->BSC (checked via UI and api.skip.build/v2/fungible/route, 2026-09-23): output stays 0.
    routes = [("SOL", "ETH"), ("ETH", "SOL"), ("SOL", "Base"), ("Base", "SOL")]

    async def setup(self, page, route):
        s, d = route
        await page.goto(f"https://go.skip.build/?src_chain={SKIP_CHAIN[s]}&src_asset={CHAINS[s]['usdc']}"
                        f"&dest_chain={SKIP_CHAIN[d]}&dest_asset={CHAINS[d]['usdc']}", wait_until="domcontentloaded")
        await page.get_by_text("on Solana").first.wait_for(timeout=30000)
        await page.wait_for_timeout(2500)

    async def enter(self, page):
        await type_into(page.locator("input:visible").first)

    async def read(self, page):
        vals = [v["v"] for v in await input_values(page) if v["m"] == "decimal"]
        if len(vals) < 2 or not re.fullmatch(NUM, vals[1] or "") or fnum(vals[1]) == 0:
            return None
        t = await body_text(page)
        fee = re.search(r"\$([\d.,]+) in fees", t)
        eta = re.search(r"Settings\n([^\n]*(?:sec|min|hour|day)[^\n]*)", t)
        usd = re.findall(r"\n\$([\d.,]+)\n", t)
        return {"out": fnum(vals[1]), "amount_in": fnum(vals[0]),
                "fees_usd_in_quote": fnum(fee.group(1)) if fee else None,  # already deducted from out
                "eta": eta.group(1) if eta else None,
                "usd_values": usd[:2], "display_decimals": len(vals[1].split(".")[-1]) if "." in vals[1] else 0}

ADAPTER = SkipGo()
