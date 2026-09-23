"""Meson (meson.fi) adapter.

No URL params for the route; https://meson.fi/swap is scripted: click the chain title under "From"/"To",
pick the chain in the "Search chains" modal, then pick USDC in the token dropdown that opens.
Meson's USDC per chain (relayer.meson.fi/api/v1/list) matches sites.CHAINS exactly, incl. Binance-Peg
USDC 0x8ac7...d580d (18 dp) on BSC. The quote ("Fee" + "You will receive") shows without a wallet;
the fee is deducted from the amount (not on top). We never click "Connect Your Wallet".
"""
import re
from sites import NUM, fnum, body_text, type_into

CHAIN = {"SOL": "Solana", "ETH": "Ethereum", "BSC": "BNB Smart Chain", "Base": "Base"}


class Meson:
    name = "meson"
    bridg_id = "meson"
    crop = (553, 222, 482, 520)
    label_url = None

    async def _pick(self, page, side, chain):
        box = page.locator(f"xpath=//div[normalize-space(text())='{side}']/following-sibling::div[1]") \
                  .locator("visible=true").first
        await box.click()
        await page.locator("text='Mainstream' >> visible=true").first.wait_for(timeout=15000)
        search = page.locator("input:visible").last
        await search.fill(chain)
        await page.wait_for_timeout(800)
        # modal chain tile; exact text match, last visible is inside the modal
        await page.locator(f"text='{chain}' >> visible=true").last.click()
        await page.wait_for_timeout(1200)
        # a token dropdown opens under the chain with the current token (USDC) on top; USDC is kept,
        # close the dropdown by clicking blank page area (verified in setup)
        await page.mouse.click(1200, 800)
        await page.wait_for_timeout(600)

    async def setup(self, page, route):
        await page.goto("https://meson.fi/swap", wait_until="domcontentloaded")
        await page.get_by_text("Amount", exact=True).first.wait_for(timeout=30000)
        await page.wait_for_timeout(3000)
        await self._pick(page, "From", CHAIN[route[0]])
        await self._pick(page, "To", CHAIN[route[1]])
        t = await body_text(page)
        want = f"From\n{CHAIN[route[0]]}\nUSDC\nTo\n{CHAIN[route[1]]}\nUSDC"
        if want not in t:
            raise RuntimeError("meson route not selected: " + t[:200].replace("\n", "|"))

    async def enter(self, page):
        await type_into(page.locator("input[placeholder='0']:visible").first)

    async def read(self, page):
        t = await body_text(page)
        m = re.search(rf"You will receive\n({NUM}) USDC", t)
        if not m or fnum(m.group(1)) == 0:
            return None
        seg = t.split("Amount", 1)[-1].split("You will receive", 1)[0]
        fees = [(k.strip(), fnum(v), tok) for k, v, tok in re.findall(rf"\n([^\n]*Fee[^\n]*)\n({NUM}) (\w+)", seg)]
        return {"out": fnum(m.group(1)), "amount_in": 100.0, "fees_deducted": fees,
                "fee_total": sum(f[1] for f in fees if f[2] == "USDC"),
                "fixed_fee_on_top": 0.0, "fixed_fee_token": None,
                "display_decimals": len(m.group(1).split(".")[1]) if "." in m.group(1) else 0}


ADAPTER = Meson()
