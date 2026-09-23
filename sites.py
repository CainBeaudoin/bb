"""Per-site adapters: open a route with 100 USDC ready to type, then read the visible quote.

Each adapter exposes:
  setup(page, route)   -> navigate + select route (no amount entered yet)
  enter(page)          -> type the amount (called behind the barrier)
  read(page)           -> dict with a parsed quote, or None if not visible yet
"""
import re

AMOUNT = "100"

CHAINS = {
    "SOL":  dict(bridg_keys=["solana"], bridg="Solana",    relay_id=792703809, relay_slug="solana",   debridge=7565164, jumper=1151111081099710, across="solana",   mayan="Solana",
                 usdc="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"),
    "ETH":  dict(bridg_keys=["ethereum"], bridg="Ethereum",  relay_id=1,         relay_slug="ethereum", debridge=1,       jumper=1,                across="ethereum", mayan="Ethereum",
                 usdc="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"),
    "BSC":  dict(bridg_keys=["bnb","bsc","binance"], bridg="BNB Chain", relay_id=56,        relay_slug="bsc",      debridge=56,      jumper=56,               across="bsc",      mayan="BSC",
                 usdc="0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d"),  # Binance-Peg USDC, 18 dp (bridged)
    "Base": dict(bridg_keys=["base"], bridg="Base",      relay_id=8453,      relay_slug="base",     debridge=8453,    jumper=8453,             across="base",     mayan="Base",
                 usdc="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"),
}

ROUTES = [("SOL", "ETH"), ("ETH", "SOL"), ("SOL", "BSC"), ("BSC", "SOL"), ("SOL", "Base"), ("Base", "SOL")]

NUM = r"\d[\d,]*\.?\d*"


def fnum(s):
    return float(s.replace(",", ""))


async def body_text(page):
    return await page.evaluate("document.body.innerText")


async def input_values(page):
    return await page.evaluate(
        """[...document.querySelectorAll('input')].filter(i=>i.offsetParent!==null)
             .map(i=>({v:i.value, p:i.placeholder, m:i.inputMode, t:i.type}))""")


async def type_into(loc):
    for _ in range(60):  # some widgets render the input disabled until token metadata loads
        if await loc.is_enabled():
            break
        await loc.page.wait_for_timeout(500)
    await loc.click()
    await loc.press("Meta+a")
    await loc.press("Backspace")
    await loc.type(AMOUNT, delay=20)


# ---------------------------------------------------------------- Bridg
class Bridg:
    bridg_id = None
    crop = (140, 40, 1120, 960)
    label_url = None
    name = "bridg"

    async def _pick(self, page, idx, chain):
        await page.get_by_text("Pick an asset", exact=True).nth(idx if idx == 0 else 0).click()
        modal = page.locator("input[placeholder*='Search a token']")
        await modal.wait_for(timeout=15000)
        await modal.fill("USDC")
        await page.wait_for_timeout(800)
        row = page.locator(", ".join(f"button[data-testid=asset-selector-option][data-asset=USDC][data-chain={k}]"
                                     for k in chain["bridg_keys"]))
        await row.first.scroll_into_view_if_needed(timeout=10000)
        self.picked = getattr(self, "picked", [])
        self.picked.append(await row.first.inner_text())
        await row.first.click(timeout=10000)
        await page.wait_for_timeout(500)

    async def setup(self, page, route):
        src, dst = CHAINS[route[0]], CHAINS[route[1]]
        self.picked = []
        await page.goto("https://bridg.now/swap/", wait_until="domcontentloaded")
        await page.get_by_text("Pick an asset", exact=True).first.wait_for(timeout=30000)
        await self._pick(page, 0, src)
        await self._pick(page, 1, dst)

    async def enter(self, page):
        await type_into(page.locator("input").first)

    async def read(self, page):
        t = await body_text(page)
        if "venues priced this amount" not in t:
            return None
        venues = await page.evaluate("""[...document.querySelectorAll('[data-testid=board-row]')].map(r => ({
            venue: r.querySelector('.sw-row__name')?.innerText, venue_id: r.dataset.venue,
            out: parseFloat((r.querySelector('[data-testid=board-row-amount] .br-amt__val')?.innerText || '').replace(/,/g, '')),
            delta: r.querySelector('[data-testid=board-row-shortfall]')?.innerText || null,
            eta: r.querySelector('.sw-row__meta')?.innerText || null,
            tags: [...r.querySelectorAll('.br-tag')].map(x => x.innerText.trim()),
            compare_only: /Compare only/i.test(r.innerText)}))""")
        venues = [v for v in venues if v["out"] == v["out"]]  # drop NaN (still loading)
        if not venues:
            return None
        return {"venues": venues, **self._detail(t),
                "priced": re.search(r"(\d+) venues priced", t).group(1)}

    @staticmethod
    def _detail(t):
        det = t.split("Yours is quoted", 1)[-1]
        det = det[det.find("You receive"):]
        route = re.search(r"Route\n([^\n]+)", det)
        pay = re.search(rf"You pay\n({NUM})", det)
        fees = [(k.strip(), fnum(v)) for k, v in re.findall(rf"\n([^\n]*fee[^\n]*)\n\s*[−-]\s*({NUM})", det, re.I)]
        recv = re.findall(rf"You receive\n({NUM})", det)
        return {"detail_route": route.group(1) if route else None, "amount_in": fnum(pay.group(1)) if pay else None,
                "detail_fees": fees, "best_out": fnum(recv[-1]) if recv else None}

    async def fastest_detail(self, page):
        """Toggle to 'Fastest' so the right panel breaks down that venue's fees, then toggle back."""
        await page.get_by_text("Fastest", exact=True).first.click()
        await page.wait_for_timeout(1200)
        d = self._detail(await body_text(page))
        await page.get_by_text("Best price", exact=True).first.click()
        await page.wait_for_timeout(500)
        return d


# ---------------------------------------------------------------- Relay
class Relay:
    bridg_id = 'relay'
    crop = (480, 140, 440, 500)
    label_url = None
    name = "relay"

    async def setup(self, page, route):
        s, d = CHAINS[route[0]], CHAINS[route[1]]
        await page.goto(f"https://relay.link/bridge/{d['relay_slug']}?fromChainId={s['relay_id']}"
                        f"&fromCurrency={s['usdc']}&toCurrency={d['usdc']}", wait_until="domcontentloaded")
        await page.locator("input[inputmode=decimal]").first.wait_for(timeout=30000)
        await page.wait_for_timeout(2000)

    async def enter(self, page):
        await type_into(page.locator("input[inputmode=decimal]").first)

    async def read(self, page):
        vals = await input_values(page)
        dec = [v["v"] for v in vals if v["m"] == "decimal"]
        if len(dec) < 2 or not dec[1] or fnum(dec[1] or "0") == 0:
            return None
        t = await body_text(page)
        rate = re.search(rf"1 USDC = ({NUM}) USDC", t)
        return {"out": fnum(dec[1]), "amount_in": fnum(dec[0]), "rate": rate.group(1) if rate else None}


# ---------------------------------------------------------------- deBridge
class DeBridge:
    bridg_id = 'debridge'
    crop = (440, 240, 520, 640)
    label_url = None
    name = "debridge"

    async def setup(self, page, route):
        s, d = CHAINS[route[0]], CHAINS[route[1]]
        await page.goto(f"https://app.debridge.finance/?inputChain={s['debridge']}&outputChain={d['debridge']}"
                        f"&inputCurrency={s['usdc']}&outputCurrency={d['usdc']}&dlnMode=simple",
                        wait_until="domcontentloaded")
        await page.get_by_text("You pay").first.wait_for(timeout=30000)
        await page.wait_for_timeout(2500)

    def _inputs(self, page):
        return page.locator("input:visible")

    async def enter(self, page):
        vals = await input_values(page)
        # first visible numeric-ish input is "You pay"
        await type_into(self._inputs(page).nth(0))

    async def read(self, page):
        vals = await input_values(page)
        nums = [v["v"] for v in vals if re.fullmatch(NUM, v["v"] or "")]
        if len(nums) < 2 or fnum(nums[1]) == 0:
            return None
        t = await body_text(page)
        extra = re.search(rf"\+\s*({NUM})\s*(USDC|SOL|ETH|BNB)", t)
        return {"out": fnum(nums[1]), "amount_in": fnum(nums[0]),
                "fixed_fee_on_top": fnum(extra.group(1)) if extra else None,
                "fixed_fee_token": extra.group(2) if extra else None}


# ---------------------------------------------------------------- Jumper (LI.FI)
class Jumper:
    bridg_id = 'lifi'
    crop = (270, 160, 900, 740)
    label_url = None
    name = "lifi"

    async def setup(self, page, route):
        s, d = CHAINS[route[0]], CHAINS[route[1]]
        await page.goto(f"https://jumper.exchange/?fromChain={s['jumper']}&toChain={d['jumper']}"
                        f"&fromToken={s['usdc']}&toToken={d['usdc']}", wait_until="domcontentloaded")
        await page.get_by_text("Send", exact=True).first.wait_for(timeout=30000)
        gs = page.get_by_text("Get started", exact=True)
        if await gs.count():
            await gs.first.click()
        await page.wait_for_timeout(2500)

    async def enter(self, page):
        await type_into(page.locator("input[inputmode=decimal], input[name=fromAmount]").first)

    async def read(self, page):
        t = re.sub(r"\n\s*\n+", "\n", await body_text(page))
        if "Best Return" not in t:
            return None
        seg = t.split("Enter wallet address", 1)[-1]
        routes = [{"out": fnum(a), "usd": u, "venue": v.strip(), "gas_usd": g, "eta": e}
                  for a, u, v, g, e in re.findall(
                      rf"\n({NUM})\n(\$[\d.,]+)\n•\n([^\n]+)\n1 USDC ≈ [^\n]+\n([^\n]+)\n([^\n]+)", "\n" + seg)]
        if not routes:
            return None
        return {"out": routes[0]["out"], "best_return_venue": routes[0]["venue"],
                "max_out": max(r["out"] for r in routes), "routes": routes}


# ---------------------------------------------------------------- Across
class Across:
    bridg_id = 'across'
    crop = (370, 260, 660, 480)
    label_url = None
    name = "across"

    async def setup(self, page, route):
        s, d = CHAINS[route[0]], CHAINS[route[1]]
        await page.goto(f"https://app.across.to/?from={s['across']}&to={d['across']}&inputToken=USDC&outputToken=USDC",
                        wait_until="domcontentloaded")
        await page.get_by_text("From", exact=True).first.wait_for(timeout=30000)
        await page.wait_for_timeout(2500)

    async def enter(self, page):
        await type_into(page.locator("input:visible").first)

    async def read(self, page):
        vals = await input_values(page)
        nums = [v["v"] for v in vals if re.fullmatch(NUM, v["v"] or "")]
        if len(nums) >= 2 and fnum(nums[1]) > 0:
            return {"out": fnum(nums[1]), "amount_in": fnum(nums[0])}
        return None


# ---------------------------------------------------------------- Mayan
class Mayan:
    bridg_id = 'mayan'
    crop = (470, 140, 460, 600)
    label_url = None
    name = "mayan"

    async def _pick(self, page, idx, chain):
        # token boxes render as "<SYMBOL>\n<Chain>"; click the idx-th (0=From, 1=To) by position
        boxes = await page.evaluate("""[...document.querySelectorAll('div,button')]
            .filter(e => /^[A-Za-z0-9.]{2,10}\\n[A-Za-z ]{3,20}$/.test(e.innerText.trim()))
            .map(e => e.getBoundingClientRect()).filter(r => r.width > 80 && r.width < 220)
            .map(r => [r.x + r.width / 2, r.y + r.height / 2])""")
        ys = sorted({round(b[1]) for b in boxes})
        box = [b for b in boxes if round(b[1]) == ys[idx]][0]
        await page.mouse.click(*box)
        dlg = page.locator(".MuiModal-root, [role=dialog], [role=presentation]").last
        await dlg.get_by_text(chain["mayan"], exact=True).first.click()
        await page.wait_for_timeout(800)
        await dlg.locator("input").first.fill(chain["usdc"])  # search by contract = exact asset
        await page.wait_for_timeout(2000)
        await dlg.get_by_text("USDC", exact=True).last.click()
        await page.wait_for_timeout(800)

    async def setup(self, page, route):
        await page.goto("https://swap.mayan.finance/", wait_until="domcontentloaded")
        await page.get_by_text("From", exact=True).first.wait_for(timeout=30000)
        await page.wait_for_timeout(2000)
        await self._pick(page, 0, CHAINS[route[0]])
        await self._pick(page, 1, CHAINS[route[1]])

    async def enter(self, page):
        await type_into(page.locator("input:visible").first)

    async def read(self, page):
        t = await body_text(page)
        m = re.search(rf"\nTo\nUSDC\n[^\n]+\n({NUM})\n", t)
        if not m or fnum(m.group(1)) == 0:
            return None
        mode = re.search(r"(Swift[^\n]*|MCTP[^\n]*|WH[^\n]*|Fast MCTP[^\n]*)\n(\d+\w)", t)
        return {"out": fnum(m.group(1)), "amount_in": 100.0, "mode": mode.group(1) if mode else None,
                "eta": mode.group(2) if mode else None, "display_decimals": len(m.group(1).split(".")[-1])}


ADAPTERS = {a.name: a for a in (Bridg(), Relay(), DeBridge(), Jumper(), Across(), Mayan())}

# Additional venues live in adapters/<name>.py, each exposing ADAPTER = <instance> with the same
# interface (name, bridg_id, crop, setup, enter, read) and optionally BLOCKED = {"reason": ...}.
BLOCKED = {}


def _load_extra():
    import importlib, pkgutil, os
    pkg = os.path.join(os.path.dirname(__file__), "adapters")
    for m in pkgutil.iter_modules([pkg]):
        if m.name.startswith("_"):
            continue
        mod = importlib.import_module(f"adapters.{m.name}")
        if getattr(mod, "ADAPTER", None) is not None:
            ADAPTERS[mod.ADAPTER.name] = mod.ADAPTER
        if getattr(mod, "BLOCKED", None):
            BLOCKED[m.name] = mod.BLOCKED


_load_extra()
