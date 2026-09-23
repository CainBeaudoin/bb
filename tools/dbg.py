import sys, asyncio, json, traceback
from playwright.async_api import async_playwright
from sites import ADAPTERS, ROUTES
async def one(b, name, route):
    a = ADAPTERS[name]; tag=f"{name}_{route[0]}-{route[1]}"
    ctx = await b.new_context(viewport={"width":1400,"height":1000}); p = await ctx.new_page()
    try:
        await a.setup(p, route); await p.screenshot(path=f"probe/{tag}_setup.png")
        await a.enter(p)
        q=None
        for _ in range(40):
            await p.wait_for_timeout(500)
            q = await a.read(p)
            if q: break
        await p.wait_for_timeout(3000); q = await a.read(p) or q
        print(tag, json.dumps(q)[:1500])
    except Exception as e:
        print(tag, "ERR", repr(e)[:400])
    await p.screenshot(path=f"probe/{tag}.png")
    open(f"probe/{tag}.txt","w").write(await p.evaluate("document.body.innerText"))
    await ctx.close()
async def main():
    names = sys.argv[1].split(","); r = tuple(sys.argv[2].split("-")) if len(sys.argv)>2 else ROUTES[0]
    async with async_playwright() as pw:
        b = await pw.chromium.launch(headless=True)
        await asyncio.gather(*[one(b,n,r) for n in names]); await b.close()
asyncio.run(main())
