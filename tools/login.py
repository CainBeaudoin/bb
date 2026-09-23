"""Open a headed, isolated Playwright browser so YOU can sign in to a platform yourself.

    .venv/bin/python tools/login.py axiom

The session (cookies/local storage) is kept in profiles/<platform>/, which is git- and vercel-ignored.
Adapters for login-gated platforms reuse that profile for quote-only reads. This is NOT your Chrome profile.
Close the browser window when you're signed in.
"""
import asyncio, sys
from playwright.async_api import async_playwright

URLS = {"axiom": "https://axiom.trade", "gmgn": "https://gmgn.ai", "fomo": "https://fomo.family",
        "pumpfun": "https://pump.fun"}


async def main(name):
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(f"profiles/{name}", headless=False,
                                                          viewport={"width": 1400, "height": 1000})
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(URLS[name])
        print(f"Sign in to {name} in the window that opened, then close it. Session saves to profiles/{name}/")
        closed = asyncio.Event()
        ctx.on("close", lambda *_: closed.set())
        await closed.wait()


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in URLS:
        sys.exit(f"usage: tools/login.py {{{'|'.join(URLS)}}}")
    asyncio.run(main(sys.argv[1]))
