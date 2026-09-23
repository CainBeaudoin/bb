import asyncio
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        ctx = await b.new_context(viewport={"width":1400,"height":1000}); p = await ctx.new_page()
        await p.goto("https://bridg.now/swap/"); await p.get_by_text("Pick an asset", exact=True).first.click()
        await p.wait_for_timeout(1500)
        await p.locator("input[placeholder*='Search']").fill("USDC")
        await p.wait_for_timeout(1500)
        h = await p.evaluate("""(()=>{const el=[...document.querySelectorAll('*')].filter(e=>e.children.length==0&&e.textContent.trim()=='USDC');return el.slice(0,4).map(e=>{let x=e;for(let i=0;i<4;i++)x=x.parentElement;return x.outerHTML.slice(0,1500)}).join('\\n=====\\n')})()""")
        print(h[:5000])
        p2 = await ctx.new_page(); await p2.goto("https://swap.mayan.finance/"); await p2.wait_for_timeout(5000)
        print("\n\nMAYAN\n", (await p2.evaluate("document.querySelector('main')?.outerHTML || document.body.outerHTML"))[:6000])
        await b.close()
asyncio.run(main())
