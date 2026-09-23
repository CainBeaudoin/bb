"""CCTP (Circle Cross-Chain Transfer Protocol) — quoted via Portal Bridge's USDC page ("CCTP via Portal").

Circle's own consumer UI (https://bridge.usdc.com, "USDC Bridge") is EVM-only: its chain list has no
Solana, so it cannot quote any of Bridg's CCTP routes (all are SOL<->ETH / SOL<->Base). Evidence:
probe/cctp_circle_from_list.png. Portal (Wormhole's first-party app) has a dedicated USDC page whose
only route is labelled "Routing via Circle CCTP" (route id CCTPv2StandardExecutorRoute).

URL preselects the route:
  https://portalbridge.com/usdc-bridge?fromChain=Solana&fromToken=USDC&toChain=Ethereum&toToken=USDC
Portal does not display the executor/relayer fee (paid in source-chain gas token) before a wallet is
connected, so fixed_fee_on_top is unknown (None). BSC is not a CCTP chain.
"""
import re
from sites import CHAINS, NUM, fnum, body_text, input_values, type_into  # noqa: F401

PORTAL_CHAIN = {"SOL": "Solana", "ETH": "Ethereum", "Base": "Base"}


class CCTP:
    name = "cctp"
    bridg_id = "cctp"
    venue_ui = "CCTP via Portal (portalbridge.com/usdc-bridge)"
    crop = (440, 140, 520, 520)
    label_url = None
    routes = [("SOL", "ETH"), ("ETH", "SOL"), ("SOL", "Base"), ("Base", "SOL")]

    async def setup(self, page, route):
        f, t = PORTAL_CHAIN[route[0]], PORTAL_CHAIN[route[1]]
        await page.goto(f"https://portalbridge.com/usdc-bridge?fromChain={f}&fromToken=USDC"
                        f"&toChain={t}&toToken=USDC", wait_until="domcontentloaded")
        await page.locator("input[placeholder='0']").first.wait_for(timeout=60000)
        await page.wait_for_timeout(2500)
        page._bench_route_id = None  # per-page state (adapter instance is shared)

    async def enter(self, page):
        await type_into(page.locator("input[placeholder='0']").first)

    async def read(self, page):
        vals = await page.evaluate("[...document.querySelectorAll(\"input[placeholder='0']\")].map(i => i.value)")
        if len(vals) < 2 or not re.fullmatch(NUM, vals[1] or "") or fnum(vals[1]) == 0:
            return None
        t = await body_text(page)
        via = re.search(r"Routing via ([^\n]+)\n+\s*([^\n]*\d[^\n]*)", t)
        if not via:
            return None
        if page._bench_route_id is None:  # peek at the Routes dialog once for the route type, then close it
            try:
                await page.get_by_text("Routing via").first.click()
                r = page.locator("[data-testid^='route-']").first
                await r.wait_for(timeout=5000)
                page._bench_route_id = (await r.get_attribute("data-testid") or "").replace("route-", "").replace("-selected", "")
                await page.get_by_test_id("routes-close-button").click()
                await page.wait_for_timeout(500)
            except Exception:
                page._bench_route_id = ""
        usd = re.search(r"\$([\d.,]+) \(([-+]?[\d.]+%)\)", t)
        return {"out": fnum(vals[1]), "amount_in": fnum(vals[0]), "venue_ui": self.venue_ui,
                "messenger": via.group(1).strip(), "route_type": page._bench_route_id or None,
                "eta": via.group(2).strip(), "usd_value": usd.group(1) if usd else None,
                "price_impact": usd.group(2) if usd else None,
                "fixed_fee_on_top": None, "fixed_fee_note": "executor/relayer fee not shown without a wallet",
                "display_decimals": len(vals[1].split(".")[1]) if "." in vals[1] else 0}


ADAPTER = CCTP()
