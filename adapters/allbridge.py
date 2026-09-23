"""Allbridge Core (https://core.allbridge.io) — USDC->USDC.

URL preselects the route: ?fee=native&ft=USDC&tt=USDC&f=<SOL|ETH|BAS>&t=<...>
The relayer fee is paid ON TOP in the source chain's native gas token (fee=native, the UI default);
the Details card shows it plus the messenger (CCTP / Allbridge / ...) and the transfer fee.
Allbridge Core has no USDC on BNB Chain (only USDT), so SOL<->BSC is not supported.
"""
import re
from sites import CHAINS, NUM, fnum, body_text, input_values, type_into  # noqa: F401

AB_CHAIN = {"SOL": "SOL", "ETH": "ETH", "Base": "BAS", "BSC": "BSC"}
NATIVE = {"SOL": "SOL", "ETH": "ETH", "Base": "ETH", "BSC": "BNB"}


class Allbridge:
    name = "allbridge"
    bridg_id = "allbridge-core"
    crop = (250, 140, 900, 600)
    label_url = None
    routes = [("SOL", "ETH"), ("ETH", "SOL"), ("SOL", "Base"), ("Base", "SOL")]

    async def setup(self, page, route):
        page._bench_route = route  # per-page: the adapter instance is shared across concurrent routes
        f, t = AB_CHAIN[route[0]], AB_CHAIN[route[1]]
        await page.goto(f"https://core.allbridge.io/?fee=native&ft=USDC&tt=USDC&f={f}&t={t}",
                        wait_until="domcontentloaded")
        await page.locator("input.form__input").first.wait_for(timeout=30000)
        await page.wait_for_timeout(3000)
        rej = page.get_by_text("Reject all", exact=True)  # CMP cookie banner overlays the widget
        if await rej.count() and await rej.first.is_visible():
            await rej.first.click()
            await page.wait_for_timeout(800)

    async def enter(self, page):
        await type_into(page.locator("input.form__input").first)

    async def read(self, page):
        vals = await page.evaluate("[...document.querySelectorAll('input.form__input')].map(i => i.value)")
        if len(vals) < 2 or not re.fullmatch(NUM, vals[1] or "") or fnum(vals[1]) == 0:
            return None
        det = page.locator("button.details__btn")
        if await det.count() and await det.first.is_visible() \
                and not await page.locator("app-details-card").count():
            await det.first.click()
            await page.wait_for_timeout(800)
        card = page.locator("app-details-card")
        ct = await card.first.inner_text() if await card.count() else ""
        nums = [l.strip() for l in ct.split("\n") if re.fullmatch(NUM, l.strip())]
        messenger = await page.locator("app-select-messaging .messaging__text").first.inner_text() \
            if await page.locator("app-select-messaging .messaging__text").count() else None
        tf = re.search(rf"Transfer fee\s*\n\s*({NUM})\s*(\w+)", ct)
        eta = re.search(r"~\s*\d+\s*\w+", ct)
        # numeric-only lines of the card: amount_in, amount_out (2dp), src gas, dst extra gas, relayer fee (last)
        out2 = fnum(nums[1]) if len(nums) > 1 else None
        relayer = fnum(nums[-1]) if len(nums) > 4 else None
        picked = [s.replace("\n", " ") for s in await page.locator("button.select__btn").all_inner_texts()]
        out = fnum(vals[1])
        if out2 is not None and len(nums[1].split(".")[-1]) > len(vals[1].split(".")[-1]) and abs(out2 - out) < 0.1:
            out = out2  # the input box trims trailing digits; the details card shows 2dp
        return {"out": out, "out_input_box": vals[1], "amount_in": fnum(vals[0]), "out_details_2dp": out2,
                "fixed_fee_on_top": relayer, "fixed_fee_token": NATIVE[page._bench_route[0]] + " (relayer fee, fee=native)",
                "transfer_fee": f"{tf.group(1)} {tf.group(2)}" if tf else None,
                "messenger": messenger.strip() if messenger else None, "eta": eta.group(0) if eta else None,
                "display_decimals": len(vals[1].split(".")[1]) if "." in vals[1] else 0,
                "picked": picked}


ADAPTER = Allbridge()
