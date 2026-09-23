"""OpenSea swap (https://opensea.io/swap) — cross-chain token swap widget, routed via Relay (LI.FI on some routes).

Quotes are shown without a wallet (the CTA just says "Connect ... Wallet"; we never click it).
Route is preselected via URL params discovered by picking tokens once:
    ?fromChain=solana&fromAddress=<mint>&toChain=ethereum&toAddress=<contract>
Chain slugs: solana / ethereum / base. BNB Chain is NOT offered by OpenSea swap (absent from its chain list,
and the Binance-Peg USDC contract returns "No currencies found"), so the BSC routes are unsupported.

The Sell input defaults to USD ("$100"); setup clicks the "Swap Vert" toggle so the input is in USDC units.
Output digits are <number-flow-react> web components (innerText is empty) -> read `_data.valueAsString`.
The fee row ("Now: 0% OpenSea Fee  $x.xx") is an accordion; expanding it shows
Route / Provider's fee (in parentheses = deducted from output) / OpenSea fee / Gas fee / Est. Time /
Swap impact / Max slippage. Gas fee is paid separately by the sender in the native token (on top).
"""
import re
from sites import CHAINS, NUM, fnum, body_text, type_into

SLUG = {"SOL": "solana", "ETH": "ethereum", "Base": "base"}

_READ = """() => {
  const flows = [...document.querySelectorAll('number-flow-react')]
    .filter(n => n.offsetParent !== null)
    .map(n => ({v: n._data ? n._data.valueAsString : null, y: n.getBoundingClientRect().y}));
  const inp = document.querySelector('input[inputmode=decimal]');
  return {flows, amount: inp ? inp.value : null};
}"""


def _money(t, label):
    """'Provider's fee\\n($0.27)\\n0.27%' -> (0.27, deducted=True, '0.27%')"""
    m = re.search(rf"{label}\n(\()?(-)?\s*<?\s*\$({NUM})\)?(?:\n(-?[\d.]+%))?", t)
    if not m:
        return None, None, None
    return fnum(m.group(3)), bool(m.group(1)), m.group(4)


class OpenSea:
    name = "opensea"
    bridg_id = None
    kind = "platform"
    label = "OpenSea"
    label_url = None
    crop = (465, 285, 525, 690)
    routes = [("SOL", "ETH"), ("ETH", "SOL"), ("SOL", "Base"), ("Base", "SOL")]
    unsupported_routes = ["SOL->BSC", "BSC->SOL"]  # BNB Chain not offered by OpenSea swap

    def __init__(self):
        self._total = {}

    async def setup(self, page, route):
        s, d = route
        await page.goto(f"https://opensea.io/swap?fromChain={SLUG[s]}&fromAddress={CHAINS[s]['usdc']}"
                        f"&toChain={SLUG[d]}&toAddress={CHAINS[d]['usdc']}", wait_until="domcontentloaded")
        inp = page.locator("input[inputmode=decimal]").first
        await inp.wait_for(timeout=45000)
        await page.get_by_text("Receive", exact=True).first.wait_for(timeout=30000)
        await page.wait_for_timeout(3000)
        # switch the Sell input from USD to token (USDC) units
        t = await body_text(page)
        if re.search(r"Max\n\$\n", t):
            await page.locator("button:has(svg[aria-label='Swap Vert'])").first.click()
            await page.wait_for_timeout(800)
            t = await body_text(page)
            if re.search(r"Max\n\$\n", t):
                raise RuntimeError("OpenSea: could not switch amount input to token units")

    async def enter(self, page):
        await type_into(page.locator("input[inputmode=decimal]").first)

    async def read(self, page):
        r = await page.evaluate(_READ)
        if not r or r["amount"] != "100":
            return None
        flows = [f for f in r["flows"] if f["v"]]
        outs = [f["v"] for f in flows if re.fullmatch(NUM, f["v"])]
        if not outs:
            return None
        out = fnum(outs[0])
        if not (50 < out <= 101):  # guard against stale quotes for "1"/"10" while typing
            return None
        usd = next((f["v"] for f in flows if f["v"].startswith("$")), None)
        t = await body_text(page)
        total = re.search(rf"OpenSea Fee\n\$({NUM})", t)  # collapsed header shows total fees; gone once expanded
        if total:
            self._total[id(page)] = fnum(total.group(1))
        if "Provider's fee" not in t:  # expand the fee accordion (not a wallet/submit control)
            try:
                await page.locator("button[aria-expanded]").filter(has_text="OpenSea Fee").first.click(timeout=3000)
                await page.wait_for_timeout(800)
                t = await body_text(page)
            except Exception:
                pass
        route = re.search(r"\nRoute\n([^\n]+)", t)
        pf, pf_ded, pf_pct = _money(t, "Provider's fee")
        of, of_ded, of_pct = _money(t, "OpenSea fee")
        gas, gas_ded, _ = _money(t, "Gas fee")
        gas_raw = re.search(r"Gas fee\n([^\n]+)", t)
        eta = re.search(r"Est\. Time\n([^\n]+)", t)
        imp = re.search(r"Swap impact\n([^\n]+)\n(-?[\d.]+%)", t)
        slip = re.search(r"Max slippage\n([\d.]+%)", t)
        return {"out": out, "amount_in": 100.0, "out_usd": usd,
                "provider": route.group(1).strip() if route else None,
                "fee_total_usd": self._total.get(id(page)),  # provider + OpenSea + gas, USD
                "provider_fee_usd": pf, "provider_fee_pct": pf_pct, "provider_fee_deducted": pf_ded,
                "opensea_fee_usd": of, "opensea_fee_pct": of_pct,
                "gas_fee_usd": gas, "gas_fee_display": gas_raw.group(1) if gas_raw else None, "fixed_fee_on_top": gas, "fixed_fee_token": "native (gas, USD shown)" if gas else None,
                "price_impact": f"{imp.group(1)} {imp.group(2)}" if imp else None,
                "slippage": slip.group(1) if slip else None,
                "eta": eta.group(1).strip() if eta else None,
                "display_decimals": len(outs[0].split(".")[1]) if "." in outs[0] else 0}


ADAPTER = OpenSea()
