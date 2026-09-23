"""Husher (https://www.husher.io/) — CEX-backed instant exchange (default provider "Husher / Best Rate").

No URL params for the pair, so the token pickers are scripted: open the Send / Receive selector,
type "USDC" into "Type a currency or ticker", click the "USD Coin / USDC / <NETWORK>" row.
A quote shows without wallet or destination address (the Destination field is left empty).
Floating rate (Fixed rate toggle left off). The fee (feeAmount) and a flat withdrawal networkFee are
deducted from the output, not charged on top; we capture them from the page's own
/api/exchange/rate response for context.
"""
import re
from sites import NUM, fnum, body_text, type_into

NET = {"SOL": "SOLANA", "ETH": "ERC20", "BSC": "BEP20", "Base": "BASE"}  # label shown in the picker

_BOX = """(sel) => {  // center of the token-selector part of the amount box that holds `sel`
  let e = document.querySelector(sel);
  while (e && e.getBoundingClientRect().width < 380) e = e.parentElement;
  const r = e.getBoundingClientRect();
  return [r.x + r.width * 0.72, r.y + r.height / 2];
}"""

_ROW = """([net, bx]) => {  // matching row in the open dropdown nearest to x=bx, scrolled into view
  const els = [...document.querySelectorAll('div,li,button,a')]
    .filter(e => e.offsetParent && new RegExp('^USD Coin\\\\s+USDC\\\\s+' + net + '$').test(e.innerText.trim()));
  if (!els.length) return null;
  const c = r => r.x + r.width / 2;
  const el = els.sort((a, b) => Math.abs(c(a.getBoundingClientRect()) - bx) - Math.abs(c(b.getBoundingClientRect()) - bx))[0];
  el.scrollIntoView({block: 'center'});
  const r = el.getBoundingClientRect();
  return [r.x + r.width / 2, r.y + r.height / 2];
}"""


class Husher:
    name = "husher"
    bridg_id = "husher"
    crop = (230, 270, 940, 530)
    label_url = None
    routes = [("SOL", "ETH"), ("ETH", "SOL"), ("SOL", "BSC"), ("BSC", "SOL"), ("SOL", "Base"), ("Base", "SOL")]

    async def _pick(self, page, box_sel, net):
        for attempt in range(3):
            box = await page.evaluate(_BOX, box_sel)
            await page.mouse.click(*box)
            await page.wait_for_timeout(800)
            # the search box of the dropdown that just opened = the visible one nearest to this selector
            idx = await page.evaluate("""(bx) => {
                const c = [...document.querySelectorAll('input[placeholder*=ticker]')].map((e, i) => {
                    const r = e.getBoundingClientRect(), st = getComputedStyle(e);
                    return {i, ok: r.width > 0 && st.visibility !== 'hidden', d: Math.abs(r.x + r.width / 2 - bx)}; })
                    .filter(o => o.ok).sort((a, b) => a.d - b.d);
                return c.length ? c[0].i : -1; }""", box[0])
            if idx >= 0:
                await page.locator("input[placeholder*=ticker]").nth(idx).fill("USDC")
                rows = None
                for _ in range(20):
                    await page.wait_for_timeout(500)
                    rows = await page.evaluate(_ROW, [net, box[0]])
                    if rows:
                        break
                if rows:
                    await page.wait_for_timeout(300)
                    await page.mouse.click(*rows)
                    await page.wait_for_timeout(1200)
                    if await self._selected(page, box_sel) == net:
                        return
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(1000)
        raise RuntimeError(f"husher: could not select USDC {net} in {box_sel}")

    async def _selected(self, page, box_sel):
        return await page.evaluate("""(sel) => {
            let e = document.querySelector(sel);
            while (e && e.getBoundingClientRect().width < 380) e = e.parentElement;
            const m = e && e.innerText.match(/USDC\\s+USD Coin\\s+([A-Z0-9.]+)/);
            return m ? m[1] : null; }""", box_sel)

    async def setup(self, page, route):
        self.api = None

        async def on_resp(r):
            if "/api/exchange/rate" in r.url and "sendAmount=100" in r.url and "amountType=send" in r.url:
                try:
                    self.api = (await r.json()).get("data")
                except Exception:
                    pass
        page.on("response", on_resp)
        await page.goto("https://www.husher.io/", wait_until="domcontentloaded")
        await page.locator("input.send-input").wait_for(timeout=30000)
        await page.wait_for_timeout(3000)
        await self._pick(page, "input.send-input", NET[route[0]])
        await self._pick(page, "input.receive-input", NET[route[1]])
        await page.evaluate("window.scrollTo(0, 0)")  # row scrollIntoView may scroll the page; crop assumes top

    async def enter(self, page):
        self.api = None
        await type_into(page.locator("input.send-input"))

    async def read(self, page):
        v = await page.evaluate("[document.querySelector('input.send-input')?.value, document.querySelector('input.receive-input')?.value]")
        if v[0] != "100" or not v[1] or not re.fullmatch(NUM, v[1]) or fnum(v[1]) == 0:
            return None
        t = await body_text(page)
        seg = t[t.find("Receive"):t.find("Destination")]
        usd = re.search(r"\n(\$[\d.,]+)\n", seg)
        a = self.api or {}
        return {"out": fnum(v[1]), "amount_in": 100.0, "out_usd": usd.group(1) if usd else None,
                "provider": "Husher (Best Rate)", "rate_type": "floating",
                "fee_deducted": fnum(a["feeAmount"]) if a.get("feeAmount") else None,
                "network_fee_deducted": fnum(a["networkFee"]) if a.get("networkFee") else None,
                "api_receive": a.get("receiveAmount"), "eta_s": a.get("estimatedTimeSeconds"),
                "fixed_fee_on_top": None, "display_decimals": len(v[1].split(".")[1]) if "." in v[1] else 0}


ADAPTER = Husher()
