import asyncio
from playwright.async_api import async_playwright
from sites import ADAPTERS
async def main():
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        p = await (await b.new_context(viewport={"width":1400,"height":1000})).new_page()
        a = ADAPTERS["bridg"]; await a.setup(p, ("Base","SOL")); await a.enter(p); await p.wait_for_timeout(9000)
        h = await p.evaluate("""(()=>{const e=[...document.querySelectorAll('main *')].find(e=>e.children.length==0&&e.textContent.trim()=='Relay');let x=e;for(let i=0;i<6;i++){x=x.parentElement; if(['BUTTON','A','LI'].includes(x.tagName)||x.getAttribute('role')||x.onclick) break;} return x.outerHTML.slice(0,2500)})()""")
        print(h)
        await b.close()
asyncio.run(main())
