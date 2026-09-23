"""Bridg vs direct-venue UI cross-reference.

For each route and sample: open every site in its own fresh browser context (no shared cookies,
no wallet), select the route, then type 100 into all pages behind one barrier. Record timestamps
(UTC, ms), full-page + cropped screenshots with SHA-256, and append immutable JSONL records.

usage: python runner.py [--samples N] [--routes SOL-ETH,ETH-SOL] [--sites bridg,relay,...] [--headed]
"""
import argparse, asyncio, hashlib, json, os, time, uuid
from datetime import datetime, timezone
from playwright.async_api import async_playwright
from sites import ADAPTERS, ROUTES

CROP = {  # x, y, w, h at 1400x1000 viewport
    "bridg": (140, 40, 1120, 960), "relay": (480, 140, 440, 500), "debridge": (440, 240, 520, 640),
    "lifi": (270, 160, 900, 740), "across": (370, 260, 660, 480), "mayan": (470, 140, 460, 600),
}
BRIDG_NAMES = {"relay": "Relay", "across": "Across", "mayan": "Mayan", "lifi": "Lifi", "debridge": "Debridge"}
MAX_GAP_S = 5.0


class Barrier:
    def __init__(self, n):
        self.n, self.count, self.ev = n, 0, asyncio.Event()

    async def wait(self):
        self.count += 1
        if self.count >= self.n:
            self.ev.set()
        await self.ev.wait()


def now():
    return datetime.now(timezone.utc)


def iso(t):
    return t.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


async def run_site(browser, name, route, run_dir, barrier, sample):
    a = ADAPTERS[name]
    rec = {"site": name, "route": f"{route[0]}->{route[1]}", "sample": sample, "amount_in_typed": 100}
    ctx = await browser.new_context(viewport={"width": 1400, "height": 1000}, locale="en-US")
    page = await ctx.new_page()
    try:
        for attempt in range(2):
            try:
                await a.setup(page, route)
                break
            except Exception as e:
                rec.setdefault("setup_errors", []).append(repr(e)[:300])
                if attempt:
                    raise
        if name == "bridg":
            rec["bridg_picked_rows"] = list(a.picked)
        rec["url"] = page.url
    except Exception as e:
        rec["status"] = "SETUP_FAILED"
        await barrier.wait()  # still release the barrier for others
        await page.screenshot(path=f"{run_dir}/{name}_{route[0]}-{route[1]}_s{sample}_setupfail.png")
        await ctx.close()
        return rec

    await barrier.wait()
    rec["requestStart"] = iso(now())
    try:
        await a.enter(page)
    except Exception as e:
        rec["status"] = "ENTER_FAILED"; rec["error"] = repr(e)[:300]
        await ctx.close(); return rec

    q, t0 = None, time.monotonic()
    while time.monotonic() - t0 < 45:
        q = await a.read(page)
        if q:
            rec["quoteVisible"] = iso(now()); break
        await page.wait_for_timeout(250)
    if not q:
        rec["status"] = "NO_QUOTE"
    else:
        # let streaming quotes settle: stop when headline value is unchanged for 2s (max 12s)
        last, stable_since, t1 = None, time.monotonic(), time.monotonic()
        while time.monotonic() - t1 < 12:
            q2 = await a.read(page) or q
            key = json.dumps(q2.get("venues") or q2.get("out"), sort_keys=True)
            if key != last:
                last, stable_since, q = key, time.monotonic(), q2
            elif time.monotonic() - stable_since >= 2:
                break
            await page.wait_for_timeout(300)
        rec["status"] = "OK"
    base = f"{run_dir}/{name}_{route[0]}-{route[1]}_s{sample}"
    rec["screenshotAt"] = iso(now())
    q_final = await a.read(page) or q
    await page.screenshot(path=base + "_full.png", full_page=True)
    x, y, w, h = getattr(a, "crop", None) or CROP.get(name, (0, 0, 1400, 1000))
    await page.screenshot(path=base + "_crop.png", clip={"x": x, "y": y, "width": w, "height": h})
    rec["quote"] = q_final
    rec["quote_at_first_visible"] = q
    rec["screenshots"] = {k: {"path": os.path.relpath(base + f"_{k}.png"), "sha256": sha(base + f"_{k}.png")}
                          for k in ("full", "crop")}
    open(base + "_text.txt", "w").write(await page.evaluate("document.body.innerText"))
    if name == "bridg" and q_final:
        try:
            rec["fastest_detail"] = await a.fastest_detail(page)
            rec["fastest_detail_at"] = iso(now())
        except Exception as e:
            rec["fastest_detail"] = {"error": repr(e)[:200]}
    await ctx.close()
    return rec


async def run_route(browser, route, sites, run_dir, sample, out):
    sites = [s for s in sites if tuple(route) in [tuple(x) for x in (getattr(ADAPTERS[s], "routes", None) or [tuple(route)])]]
    barrier = Barrier(len(sites))
    recs = await asyncio.gather(*[run_site(browser, s, route, run_dir, barrier, sample) for s in sites])
    by = {r["site"]: r for r in recs}
    b = by.get("bridg", {})
    for r in recs:
        if r is not b and r.get("quoteVisible") and b.get("quoteVisible"):
            gap = abs((datetime.fromisoformat(r["quoteVisible"][:-1]) -
                       datetime.fromisoformat(b["quoteVisible"][:-1])).total_seconds())
            r["gap_vs_bridg_s"] = round(gap, 3)
            r["gap_flag"] = gap > MAX_GAP_S
    run_id = uuid.uuid4().hex[:12]
    with open(out, "a") as f:
        for r in recs:
            r["run_id"] = run_id
            f.write(json.dumps(r) + "\n")
    return recs


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--routes", default=",".join(f"{a}-{b}" for a, b in ROUTES))
    ap.add_argument("--sites", default=",".join(ADAPTERS))
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--out", default="data/raw_quotes.jsonl")
    args = ap.parse_args()
    sites = args.sites.split(",")
    routes = [tuple(r.split("-")) for r in args.routes.split(",")]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = f"evidence/{stamp}"
    os.makedirs(run_dir, exist_ok=True); os.makedirs(os.path.dirname(args.out), exist_ok=True)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not args.headed)
        for sample in range(1, args.samples + 1):
            for route in routes:
                t = time.monotonic()
                recs = await run_route(browser, route, sites, run_dir, sample, args.out)
                # retry any site whose quote landed >5s from Bridg's (one retry, whole route)
                if any(r.get("gap_flag") for r in recs):
                    flagged = [r["site"] for r in recs if r.get("gap_flag")]
                    print(f"  gap>5s for {flagged}; retrying route")
                    recs = await run_route(browser, route, ["bridg"] + flagged, run_dir, sample, args.out)
                summ = " ".join(f"{r['site']}={(r.get('quote') or {}).get('out', (r.get('quote') or {}).get('best_out', r.get('status')))}"
                                for r in recs)
                print(f"[s{sample}] {route[0]}->{route[1]} ({time.monotonic()-t:.0f}s): {summ}", flush=True)
                await asyncio.sleep(7)  # stay well under Bridg's 10 quotes/min/IP
        await browser.close()


asyncio.run(main())
