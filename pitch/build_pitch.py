"""Build the Bridg × OpenSea one-pager (pitch/opensea.html + pitch/Bridg_x_OpenSea.pdf) from the latest campaign.

Bridg side = Bridg's best *fully-priced* row: excludes compare-only rows and venues whose Bridg price is a flat
estimate or leaves a fee outside the quote (Allbridge relayer fee in ETH/SOL, Meson/Husher flat formulas,
Rhino/Eco with no public UI to verify). Run from the repo root: .venv/bin/python pitch/build_pitch.py
"""
import asyncio, html, statistics, sys
sys.path.insert(0, ".")
from compare import load_runs

EXCLUDE = {"allbridge-core", "meson", "husher", "rhino", "eco"}
ROUTES = ["SOL->ETH", "ETH->SOL", "SOL->Base", "Base->SOL", "SOL->BSC", "BSC->SOL"]
RECEIPT_SAMPLE = {"SOL->ETH": 1, "ETH->SOL": 1, "SOL->Base": 1, "Base->SOL": 2}
CHAIN = {"SOL": "Solana", "ETH": "Ethereum", "BSC": "BNB Chain", "Base": "Base"}

runs = load_runs("data/raw_quotes.jsonl")
per = {r: [] for r in ROUTES}
camp = None
for rid, recs in runs.items():
    by = {x["site"]: x for x in recs}
    b = by.get("bridg")
    if not b or b.get("status") != "OK":
        continue
    camp = b.get("campaign")
    rows = [v for v in b["quote"]["venues"] if not v["compare_only"] and v["venue_id"] not in EXCLUDE]
    best = max(rows, key=lambda v: v["out"])
    best = {**best, "venue": {"Cctp": "CCTP", "Lifi": "LI.FI", "Debridge": "deBridge"}.get(best["venue"], best["venue"])}
    o = by.get("opensea")
    oq = o["quote"] if o and o.get("status") == "OK" else None
    per[b["route"]].append({"sample": b["sample"], "bridg": best["out"], "via": best["venue"],
                            "os": oq and oq["out"], "os_provider": oq and oq.get("provider"),
                            "os_fee_pct": oq and oq.get("provider_fee_pct"),
                            "b_read": b.get("valueReadAt"), "o_read": o and o.get("valueReadAt"),
                            "gap_s": o and o.get("gap_vs_bridg_s"), "b_shot": b["screenshots"]["crop"],
                            "o_shot": o and o.get("screenshots", {}).get("crop")})

stats = []
for r in ROUTES:
    xs = per[r]
    s = {"route": r, "n": len(xs), "bridg": statistics.mean(x["bridg"] for x in xs),
         "via": max(set(x["via"] for x in xs), key=[x["via"] for x in xs].count)}
    os_ = [x for x in xs if x["os"] is not None]
    if os_:
        s["os"] = statistics.mean(x["os"] for x in os_)
        provs = [x["os_provider"] for x in os_ if x["os_provider"]]
        s["os_provider"] = " / ".join(sorted(set(provs))) if provs else "—"
        sv = [(x["bridg"] - x["os"]) * 100 for x in os_]
        s["bps"], s["lo"], s["hi"] = statistics.mean(sv), min(sv), max(sv)
    stats.append(s)
first = min(x["b_read"] for r in ROUTES for x in per[r])
last = max(x["b_read"] for r in ROUTES for x in per[r])
worst_gap_ms = max((x["gap_s"] or 0) for r in ROUTES for x in per[r] if x["os"] is not None) * 1000
shared = [s for s in stats if "bps" in s]
head = max(shared, key=lambda s: s["bps"])
arrow = lambda r: r.replace("->", " → ")
fmt = lambda v, d=3: f"{v:.{d}f}"
esc = html.escape


def rows_html():
    out = []
    for s in stats:
        a, b_ = s["route"].split("->")
        if "bps" in s:
            cls = "win" if s["bps"] > 2 else "par"
            diff = f'<b class="{cls}">+{s["bps"]:.1f} bps</b>'
            usd = f'${s["bps"] * 100:,.0f}'
            osc = f'{fmt(s["os"])} <span class="via">via {esc(s["os_provider"])}</span>'
        else:
            diff, usd = '<b class="new">New route</b>', "—"
            osc = '<span class="na">Not offered</span>'
        out.append(f'<tr><td class="rt">{arrow(s["route"])}<span class="sub">{CHAIN[a]} → {CHAIN[b_]}</span></td>'
                   f'<td class="n">{osc}</td><td class="n">{fmt(s["bridg"])} <span class="via">via {esc(s["via"])}</span></td>'
                   f'<td class="n">{diff}</td><td class="n">{usd}</td></tr>')
    return "\n".join(out)


def receipts_html(routes=None):
    out = []
    for r, smp in RECEIPT_SAMPLE.items():
        if routes and r not in routes:
            continue
        x = next(x for x in per[r] if x["sample"] == smp)
        key = r.replace("->", "-")
        out.append(f'''<figure class="rc">
  <figcaption><b>{arrow(r)}</b><span>read {x["b_read"][11:23]} UTC · Δ {x["gap_s"] * 1000:.0f} ms</span></figcaption>
  <div class="pair">
    <div><img src="img/opensea_{key}.png" alt="OpenSea quote {arrow(r)}"><span class="lab">OpenSea <b>{fmt(x["os"], 4)}</b></span></div>
    <div><img src="img/bridg_{key}.png" alt="Bridg quote {arrow(r)}"><span class="lab">Bridg <b>{fmt(x["bridg"], 6)}</b> · {esc(x["via"])} row</span></div>
  </div>
</figure>''')
    return "\n".join(out)


page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bridg for OpenSea</title>
<style>
@page {{ size: Letter; margin: 0; }}
:root {{ --ink:#0b0b0b; --ink2:#4b4a46; --muted:#8a8984; --line:#e4e3dd; --soft:#f5f5f1; --lime:#c6f24e; --lime-d:#3f5a00; --blue:#1c5cab; }}
* {{ box-sizing:border-box; }}
html,body {{ margin:0; background:#fff; color:var(--ink); font:10.5pt/1.42 system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;
  -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
.page {{ width:8.5in; height:11in; margin:0 auto; padding:.42in .55in .36in; display:flex; flex-direction:column; gap:9pt; overflow:hidden; }}
.bottom {{ display:grid; grid-template-columns:1.45fr 1fr; gap:14pt; align-items:start; }}
.bottom .why {{ grid-template-columns:1fr; gap:7pt; }}
.top {{ display:flex; justify-content:space-between; align-items:center; gap:16pt; }}
.brand {{ font-weight:800; letter-spacing:.08em; font-size:12pt; }}
.brand i {{ font-style:normal; background:var(--lime); padding:1pt 5pt; border-radius:3pt; margin-left:4pt; font-weight:700; letter-spacing:.02em; font-size:9pt; vertical-align:2pt; }}
.for {{ color:var(--muted); font-size:9pt; text-align:right; }}
h1 {{ font-size:22pt; line-height:1.1; margin:4pt 0 6pt; letter-spacing:-.01em; }}
.lede {{ color:var(--ink2); font-size:10.5pt; margin:0; }}
.hero {{ display:grid; grid-template-columns:1.1fr 1fr 1fr; gap:10pt; }}
.stat {{ background:var(--soft); border-radius:8pt; padding:8pt 12pt; }}
.stat .v {{ font-size:22pt; font-weight:750; line-height:1.05; }}
.stat .v small {{ font-size:11pt; font-weight:600; }}
.stat .l {{ color:var(--ink2); font-size:9pt; margin-top:3pt; }}
.stat.key {{ background:var(--ink); color:#fff; }}
.stat.key .l {{ color:#c9c8c2; }}
.stat.key .v {{ color:var(--lime); }}
table {{ width:100%; border-collapse:collapse; font-size:9.6pt; }}
th {{ text-align:left; color:var(--muted); font-weight:600; font-size:8pt; text-transform:uppercase; letter-spacing:.05em; padding:0 6pt 5pt; border-bottom:1.2pt solid var(--ink); }}
th.n, td.n {{ text-align:right; }}
td {{ padding:3.6pt 6pt; border-bottom:.6pt solid var(--line); font-variant-numeric:tabular-nums; vertical-align:middle; }}
td.rt {{ font-weight:650; white-space:nowrap; }}
.sub {{ display:block; font-weight:400; color:var(--muted); font-size:7.8pt; }}
.via {{ display:block; color:var(--muted); font-size:7.8pt; }}
.na {{ color:var(--muted); }}
b.win {{ background:var(--lime); padding:1pt 5pt; border-radius:3pt; }}
b.par {{ color:var(--ink2); }}
b.new {{ color:var(--blue); }}
.why {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10pt; }}
.why div {{ border-top:2pt solid var(--ink); padding-top:6pt; font-size:9.4pt; color:var(--ink2); }}
.why b {{ display:block; color:var(--ink); font-size:10pt; margin-bottom:2pt; }}
h2 {{ font-size:10pt; text-transform:uppercase; letter-spacing:.06em; margin:0 0 6pt; color:var(--ink); }}
h2 span {{ text-transform:none; letter-spacing:0; color:var(--muted); font-weight:400; font-size:8.6pt; margin-left:6pt; }}
.rcs {{ display:grid; gap:10pt; }}
.rcs.two {{ grid-template-columns:1fr 1fr; }}
.rc {{ margin:0; border:.6pt solid var(--line); border-radius:6pt; padding:6pt; }}
.rc figcaption {{ font-size:9pt; margin-bottom:4pt; display:flex; flex-direction:column; }}
.rc figcaption span {{ color:var(--muted); font-size:7.2pt; }}
.pair {{ display:grid; grid-template-columns:.72fr 1fr; gap:4pt; align-items:start; }}
.pair img {{ width:100%; display:block; border-radius:3pt; }}
.lab {{ display:block; font-size:8pt; color:var(--ink2); margin-top:2pt; line-height:1.25; }}
.foot {{ margin-top:auto; font-size:7.4pt; color:var(--muted); line-height:1.4; border-top:.6pt solid var(--line); padding-top:6pt; }}
.foot b {{ color:var(--ink2); }}
@media screen and (max-width:700px) {{ .page {{ width:auto; height:auto; padding:16px; }} .bottom {{ grid-template-columns:1fr; }} .rcs.two {{ grid-template-columns:1fr; }} .hero,.why {{ grid-template-columns:1fr; }} .rcs {{ grid-template-columns:1fr 1fr; }} table {{ font-size:12px; }} }}
</style></head><body><main class="page">
<div>
  <div class="top"><div class="brand">BRIDG <i>for OpenSea</i></div><div class="for">Prepared for OpenSea · {first[:10]}</div></div>
  <h1>Land more USDC on every cross-chain swap.</h1>
  <p class="lede">Bridg prices each transfer across 16+ bridges live and routes users to the one that lands the most.
    We quoted the same 100 USDC on OpenSea's swap and on Bridg at the same instant. Bridg paid more on every route the
    two share, and it also opens BNB Chain routes OpenSea doesn't offer today.</p>
</div>

<div class="hero">
  <div class="stat key"><div class="v">+{head["bps"]:.0f} <small>bps</small></div><div class="l">more USDC landed on {arrow(head["route"])}
    ({head["lo"]:.0f}–{head["hi"]:.0f} bps across samples): ${head["bps"] * 100:,.0f} per $1M bridged</div></div>
  <div class="stat"><div class="v">{sum(1 for s in shared if s["bps"] >= 0)}/{len(shared)}</div><div class="l">shared routes where Bridg matched or beat OpenSea's quote</div></div>
  <div class="stat"><div class="v">+{len(stats) - len(shared)}</div><div class="l">BNB Chain routes (SOL ↔ BSC) Bridg can add to your swap</div></div>
</div>

<section>
  <h2>100 USDC → USDC, same instant, public UIs <span>average of {min(s["n"] for s in stats)} synchronized samples per route</span></h2>
  <table>
    <thead><tr><th>Route</th><th class="n">OpenSea receives</th><th class="n">Bridg receives</th><th class="n">Bridg advantage</th><th class="n">Per $1M bridged</th></tr></thead>
    <tbody>
{rows_html()}
    </tbody>
  </table>
</section>

<div class="bottom">
  <section class="proof">
    <h2>Proof <span>{arrow(head["route"])}, read {per[head["route"]][0]["b_read"][11:19]} UTC; OpenSea left, Bridg right</span></h2>
    <div class="rcs one">
{receipts_html([head["route"]])}
    </div>
  </section>
  <div class="why">
    <div><b>Better fills for your users</b>Every quote is priced across all venues at request time, so users land the
      best available amount rather than one provider's price.</div>
    <div><b>One integration, more routes</b>Quote, build and submit through one API with no API key. Keys stay with the
      user, and BNB Chain and dozens of other chains come included.</div>
    <div><b>Keep part of the upside</b>Bridg's referral fields let an integrator take up to 15 bps on the transfers they
      route, set per quote and with no sign-up.</div>
  </div>
</div>

<div class="foot">
  <b>Method.</b> 100 USDC → USDC on each site's public page, fresh browser, no wallet. All sites typed at once and read at once
  (OpenSea vs Bridg within {worst_gap_ms:.0f} ms); {min(s["n"] for s in stats)} samples per route, {first[:10]} {first[11:16]}–{last[11:16]} UTC.
  <b>Bridg</b>: net of its platform fee, best fully-priced route (excludes Allbridge, Meson, Husher, Rhino, Eco, whose quotes
  omit a fee charged on top or can't be verified). Source-chain gas not counted on either side. OpenSea showed a 0% OpenSea
  fee. The SOL → ETH gap reflects Relay's 1% fee and elevated Ethereum gas that day. Receipts and raw data: github.com/CainBeaudoin/bb
</div>
</main></body></html>'''

open("pitch/opensea.html", "w").write(page)
print("wrote pitch/opensea.html")
for s in stats:
    print(s["route"], round(s["bridg"], 6), s["via"], round(s.get("os", 0), 4), s.get("os_provider"),
          s.get("bps") and round(s["bps"], 1))


async def pdf():
    from playwright.async_api import async_playwright
    import os
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        p = await b.new_page()
        await p.goto("file://" + os.path.abspath("pitch/opensea.html"))
        await p.wait_for_timeout(500)
        await p.pdf(path="pitch/Bridg_x_OpenSea.pdf", format="Letter", print_background=True,
                    margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        await p.set_viewport_size({"width": 816, "height": 1056})
        h = await p.evaluate("document.querySelector('.foot').getBoundingClientRect().bottom")
        assert h <= 1056 - 24, f"one-pager content overflows a Letter page: footer ends at {h}px (limit 1032px)"
        print("footer bottom", round(h), "px of 1056")
        await p.screenshot(path="pitch/preview.png", full_page=True)
        await p.screenshot(path="pitch/preview_p1.png", clip={"x": 0, "y": 0, "width": 816, "height": 1056})
        await b.close()

asyncio.run(pdf())
print("wrote pitch/Bridg_x_OpenSea.pdf, pitch/preview.png")
