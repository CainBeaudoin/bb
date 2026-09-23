"""Layerswap (https://layerswap.io/app) — route preselected via URL params.

The received amount is rendered by a <number-flow-react> web component (digits live in a shadow
root as spinning columns, so innerText is empty); we read its displayed string from `_data.valueAsString`.
The Details panel (opened by clicking the ETA row) lists Fees / Rate / Slippage / Est. time; the fee is
deducted from the output (100 in -> out), nothing is charged on top.
"""
import re
from sites import NUM, fnum, body_text, type_into

NET = {"SOL": "SOLANA_MAINNET", "ETH": "ETHEREUM_MAINNET", "BSC": "BSC_MAINNET", "Base": "BASE_MAINNET"}

_READ_OUT = """() => {
  const lbl = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === 'Receive at');
  if (!lbl) return null;
  let box = lbl;
  while (box && !box.querySelector('number-flow-react')) box = box.parentElement;
  if (!box) return null;
  const flows = [...box.querySelectorAll('number-flow-react')].map(n => n._data ? n._data.valueAsString : null);
  const token = box.innerText.match(/\\b(USDC(?:\\.e)?|USDbC)\\n+([^\\n]+)/);
  return {flows, token: token ? token[1] : null, chain: token ? token[2] : null};
}"""


class Layerswap:
    name = "layerswap"
    bridg_id = "layerswap"
    crop = (455, 95, 490, 720)
    label_url = None
    routes = [("SOL", "ETH"), ("ETH", "SOL"), ("SOL", "BSC"), ("BSC", "SOL"), ("SOL", "Base"), ("Base", "SOL")]

    async def setup(self, page, route):
        await page.goto(f"https://layerswap.io/app?from={NET[route[0]]}&to={NET[route[1]]}"
                        f"&fromAsset=USDC&toAsset=USDC", wait_until="domcontentloaded")
        await page.locator("input[name=amount]").wait_for(timeout=30000)
        await page.get_by_text("Receive at", exact=True).first.wait_for(timeout=30000)
        await page.wait_for_timeout(2500)

    async def enter(self, page):
        await type_into(page.locator("input[name=amount]"))

    async def read(self, page):
        r = await page.evaluate(_READ_OUT)
        if not r or not r["flows"] or not r["flows"][0]:
            return None
        s = r["flows"][0]
        if not re.fullmatch(NUM, s) or fnum(s) == 0:
            return None
        t = await body_text(page)
        if "Fees\n" not in t:  # open the Details panel (click the ETA row; not a wallet/submit control)
            try:
                await page.locator("text=/^\\d+\\s*(secs?|mins?|hours?)$/").first.click(timeout=2000)
                await page.wait_for_timeout(800)
                t = await body_text(page)
            except Exception:
                pass
        fee = re.search(rf"Fees\n\$?({NUM})", t)
        eta = re.search(r"Est\. time\n+([^\n]+)", t) or re.search(r"\n(\d+\s*(?:secs?|mins?|hours?))\n", t)
        slip = re.search(r"Slippage\n(?:\(Auto\)\n)?([\d.]+%)", t)
        usd = r["flows"][1] if len(r["flows"]) > 1 else None
        return {"out": fnum(s), "amount_in": 100.0, "out_usd": usd, "fee_usd": fnum(fee.group(1)) if fee else None,
                "fee_on_top": None, "slippage": slip.group(1) if slip else None,
                "eta": eta.group(1).strip() if eta else None, "to_token": r["token"], "to_chain": r["chain"],
                "display_decimals": len(s.split(".")[1]) if "." in s else 0}


ADAPTER = Layerswap()
