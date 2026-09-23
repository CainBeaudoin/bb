"""SimpleSwap (exchange service) adapter.

URL preselects the pair: https://simpleswap.io/?from=usdc-<net>&to=usdc-<net>
(networks: sol, eth, bsc, base). SimpleSwap's assets: "USDC (Solana)" = usdcspl, "USDC (Ethereum)" = usdc,
"USDC (BSC)" = usdcbep20 (BEP-20; SimpleSwap does not show the contract), "USDC" on base = usdcbase.
The widget only hydrates after a user-like mouse move. Default rate type is FLOATING (fixed=false);
"You get" is the estimate for the route card the UI pre-selects (observed: often the "Fast"
card, not "Best rate" -- we report the displayed You-get as out and the best card as best_card_out), network fees
already deducted; nothing is charged on top of the input.
We never type an address or press "Exchange".
"""
import re
from sites import NUM, fnum, type_into

NET = {"SOL": "sol", "ETH": "eth", "BSC": "bsc", "Base": "base"}


class SimpleSwap:
    name = "simpleswap"
    bridg_id = "simpleswap"
    crop = (100, 180, 1200, 560)
    label_url = None

    async def setup(self, page, route):
        s, d = NET[route[0]], NET[route[1]]
        await page.goto(f"https://simpleswap.io/?from=usdc-{s}&to=usdc-{d}", wait_until="domcontentloaded")
        for _ in range(30):  # widget hydrates on first user interaction
            await page.mouse.move(400 + _ % 5 * 20, 300)
            await page.wait_for_timeout(700)
            if await page.get_by_test_id("amount-field").count() >= 2 and \
                    await page.locator("[data-testid=you-send-container]:visible").count():
                break
        await page.locator("[data-testid=you-send-container]:visible [data-testid=amount-field]").first.wait_for(timeout=30000)
        await page.wait_for_timeout(2500)
        await page.locator("[data-testid=main-exchange-form]:visible").first.scroll_into_view_if_needed()
        await page.evaluate("window.scrollTo(0,0)")

    async def enter(self, page):
        await type_into(page.locator("[data-testid=you-send-container]:visible [data-testid=amount-field]").first)

    async def read(self, page):
        send = await page.locator("[data-testid=you-send-container]:visible [data-testid=amount-field]").first.input_value()
        get = await page.locator("[data-testid=you-get-container]:visible [data-testid=amount-field]").first.input_value()
        g = re.search(NUM, (get or "").replace(" ", ""))
        if not send or fnum(re.search(NUM, send).group(0)) != 100 or not g or fnum(g.group(0)) == 0:
            return None
        form = await page.locator("[data-testid=main-exchange-form]:visible").first.inner_text()
        if "not supported" in form.lower():
            return None
        # route cards: "<tag>\n...<eta> min\n\n<amount> USDC"
        cards = [{"tags": [x for x in tg.split("\n") if x.strip()], "eta": e, "out": fnum(a)}
                 for tg, e, a in re.findall(rf"((?:(?:Best rate|Fast|Fastest|Decentralized)\n+)+)([\d\-–]+ min)\n\s*({NUM}) USDC", form)]
        out = fnum(g.group(0))
        # while "100" is being typed the page can still show the quote for "1"/"10" (with a small-sum
        # warning and no route cards) — wait for the real 100-USDC quote
        if "small sum" in form or not cards or out < 50:
            return None
        for c in cards:
            c["selected"] = abs(c["out"] - out) < 1e-9
        banner = re.search(rf"Sign up to get ({NUM}) USDC", await page.evaluate("document.body.innerText"))
        fixed = await page.locator("[data-testid=rate-type-switch]:visible").first.get_attribute("aria-pressed")
        warn = "small sum" in form
        return {"out": out, "best_card_out": max((c["out"] for c in cards), default=None),
                "selected_card": next((" / ".join(c["tags"]) for c in cards if c["selected"]), None),
                "signup_offer_out": fnum(banner.group(1)) if banner else None, "amount_in": fnum(re.search(NUM, send).group(0)),
                "rate_type": "floating" if fixed in (None, "false") else "fixed",
                "route_cards": cards, "fixed_fee_on_top": 0.0, "fixed_fee_token": "USDC",
                "display_decimals": len(g.group(0).split(".")[1]) if "." in g.group(0) else 0,
                "small_sum_warning": warn}


ADAPTER = SimpleSwap()
