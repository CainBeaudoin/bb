import sys, asyncio, json
from playwright.async_api import async_playwright
SITES = dict(
 bridg="https://bridg.now/swap/",
 relay="https://relay.link/bridge",
 across="https://app.across.to/bridge?from=solana&to=ethereum&inputToken=USDC&outputToken=USDC",
 jumper="https://jumper.exchange/?fromChain=1151111081099710&toChain=1&fromToken=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&toToken=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48&fromAmount=100",
 debridge="https://app.debridge.finance/?inputChain=7565164&outputChain=1&inputCurrency=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&outputCurrency=0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48&amount=100",
 mayan="https://swap.mayan.finance/?fromChain=solana&toChain=ethereum&fromToken=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&toToken=0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48&amount=100",
)
async def one(b, k, u):
    ctx = await b.new_context(viewport={"width":1400,"height":1000})
    p = await ctx.new_page()
    try:
        await p.goto(u, wait_until="domcontentloaded", timeout=45000)
        await p.wait_for_timeout(12000)
        await p.screenshot(path=f"probe/{k}.png")
        t = await p.inner_text("body")
        open(f"probe/{k}.txt","w").write(p.url+"\n----\n"+t)
        print(k, "OK", p.url)
    except Exception as e: print(k, "ERR", e)
    await ctx.close()
async def main():
    ks = sys.argv[1:] or list(SITES)
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        await asyncio.gather(*[one(b,k,SITES[k]) for k in ks])
        await b.close()
asyncio.run(main())
