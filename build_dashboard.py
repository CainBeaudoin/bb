"""Package raw quotes + normalized comparison + receipts into dashboard/data.json for index.html."""
import json, os
from datetime import datetime, timezone
from compare import load_runs, build_rows, summarize, write_csv, build_competitor_rows, summarize_competitors
from sites import ADAPTERS, BLOCKED

RAW = "data/raw_quotes.jsonl"
SITE_LABEL = {"bridg": "Bridg", "relay": "Relay", "across": "Across", "mayan": "Mayan",
              "lifi": "LI.FI (Jumper)", "debridge": "deBridge", "layerswap": "Layerswap", "rhino": "Rhino.fi",
              "husher": "Husher", "simpleswap": "SimpleSwap", "meson": "Meson", "symbiosis": "Symbiosis",
              "near-intents": "NEAR Intents", "skip-go": "Skip Go", "eco": "Eco",
              "allbridge-core": "Allbridge Core", "allbridge": "Allbridge Core", "cctp": "CCTP (via Portal)",
              "opensea": "OpenSea", "axiom": "Axiom", "gmgn": "GMGN", "fomo": "FOMO", "pumpfun": "Pump.fun"}
SITE_URL = {"bridg": "https://bridg.now/swap/", "relay": "https://relay.link", "across": "https://app.across.to",
            "mayan": "https://swap.mayan.finance", "lifi": "https://jumper.exchange",
            "debridge": "https://app.debridge.finance"}
for n, a in ADAPTERS.items():
    SITE_LABEL[n] = getattr(a, "label", None) or SITE_LABEL.get(n, n.replace("-", " ").title())
    if getattr(a, "label_url", None):
        SITE_URL[n] = a.label_url
ROUTE_ORDER = ["SOL->ETH", "ETH->SOL", "SOL->BSC", "BSC->SOL", "SOL->Base", "Base->SOL"]

runs = load_runs(RAW)
rows = build_rows(runs)
write_csv(rows)
summary = summarize(rows)
crows = build_competitor_rows(runs)
csum = summarize_competitors(crows)

# per route: Bridg's best vs the best any other site showed directly (averaged per site across samples)
winners = []
for route in ["SOL->ETH", "ETH->SOL", "SOL->BSC", "BSC->SOL", "SOL->Base", "Base->SOL"]:
    cs = [c for c in csum if c["route"] == route]
    if not cs:
        continue
    top = max(cs, key=lambda c: c["other_avg"])
    # Bridg best averaged once per synchronized run (not weighted by how many sites quoted in that run)
    bb = [r["quote"]["best_out"] for recs in runs.values() for r in recs
          if r["site"] == "bridg" and r["route"] == route and r.get("status") == "OK" and r["quote"].get("best_out")]
    best = sum(bb) / len(bb)
    per_site = {}
    for c in crows:
        if c["route"] == route:
            per_site.setdefault(c["site"], []).append(c["savings_bps"])
    means = [sum(v) / len(v) for v in per_site.values()]
    winners.append({"route": route, "bridg_best": round(best, 6), "top_site": top["site"],
                    "top_out": top["other_avg"], "savings_bps": round((best - top["other_avg"]) * 100, 1),
                    "beats": sum(1 for m in means if m > 2), "loses": sum(1 for m in means if m < -2),
                    "n_sites": len(cs)})

boards, receipts, failures, stamps = [], [], [], []
for run_id, recs in runs.items():
    for r in recs:
        for k in ("requestStart", "quoteVisible", "screenshotAt"):
            if r.get(k):
                stamps.append(r[k])
        if r.get("status") != "OK":
            failures.append({"site": r["site"], "route": r["route"], "sample": r["sample"], "status": r.get("status"),
                             "error": (r.get("error") or (r.get("setup_errors") or [""])[-1])[:240]})
            continue
        q = r["quote"]
        receipts.append({"site": r["site"], "route": r["route"], "sample": r["sample"], "run_id": run_id,
                         "requestStart": r.get("requestStart"), "quoteVisible": r.get("quoteVisible"),
                         "screenshotAt": r.get("screenshotAt"), "gap_s": r.get("gap_vs_bridg_s"),
                         "out": q.get("out", q.get("best_out")), "url": r.get("url"),
                         "crop": r["screenshots"]["crop"], "full": r["screenshots"]["full"]})
        if r["site"] == "bridg":
            boards.append({"route": r["route"], "sample": r["sample"], "run_id": run_id,
                           "quoteVisible": r.get("quoteVisible"), "venues": q["venues"],
                           "best": {"route": q.get("detail_route"), "out": q.get("best_out"),
                                    "fees": q.get("detail_fees")},
                           "fastest": {k: v for k, v in (r.get("fastest_detail") or {}).items()
                                       if k in ("detail_route", "best_out", "detail_fees", "error")},
                           "picked": r.get("bridg_picked_rows")})
        elif r["site"] == "lifi":
            receipts[-1]["routes"] = q.get("routes")

issues = [
    {"severity": "info", "title": "Competitor platforms: Bridg beats OpenSea; the rest can't be quoted",
     "detail": "OpenSea swap (Relay; LI.FI on SOL→Base; 0% OpenSea fee promo) pays 11–13 bps less than Bridg's best on "
               "SOL→ETH, ETH→SOL and Base→SOL, and ~1 bp less on SOL→Base; OpenSea has no BNB Chain. Signed in (by the user) and "
               "re-checked: Axiom has a cross-chain Convert and auto-bridged deposits, but Convert caps the amount at the wallet "
               "balance, so 100 USDC can't be priced unfunded (deposit fees shown only at its $2–3 minimum: ETH→SOL ~$0.27 gas, "
               "BSC→SOL ~$0.21, Base→SOL ~$0.02). GMGN's Convert needs 2FA plus a 3-hour lock; its deposits are Solana-only. "
               "Pump.fun's web deposit is Solana-only. FOMO pools deposits from 7 chains into one USD balance with no quote."},
    {"severity": "serious", "title": "Relay priced ~20.6 bps below relay.link on every EVM → Solana route",
     "detail": "Bridg's Relay row is 25.6 bps under relay.link on ETH→SOL, BSC→SOL and Base→SOL in every sample; "
               "5 bps is Bridg's own fee, leaving ~0.21 USDC more 'Relay fee'. Solana-source routes match. "
               "Hypothesis (unverified): Bridg's quote includes Solana USDC token-account rent that relay.link omits "
               "when no recipient wallet is set."},
    {"severity": "serious", "title": "LI.FI and SimpleSwap rows are far below their own sites",
     "detail": "LI.FI: 45–97 bps below jumper.exchange on every route (one Bridg breakdown showed a 1.0167 USDC "
               "'Lifi fee'). SimpleSwap: 47–130 bps below simpleswap.io's default floating 'Best rate' card. "
               "Hypothesis (unverified): different route/rate type or an integrator fee in Bridg's requests."},
    {"severity": "serious", "title": "Bridg lists venues whose own site can't quote these routes",
     "detail": "Rhino.fi (Bridg's best price on SOL→BSC) — retail app shut down Aug 2026. Eco — its portal has no "
               "Solana or BNB Chain, yet Bridg lists Eco on SOL↔ETH/Base. NEAR Intents — public app moved behind "
               "a login. These rows can't be checked against a public UI."},
    {"severity": "serious", "title": "Across missing from Bridg on 4 of 6 routes",
     "detail": "Not listed on ETH→SOL, BSC→SOL, Base→SOL or SOL→BSC although across.to quotes 99.98–99.99. "
               "Where listed (SOL→ETH, SOL→Base) it matches exactly net of Bridg's fee."},
    {"severity": "warning", "title": "Meson, Husher and Allbridge look like flat estimates on Bridg",
     "detail": "Their Bridg rows are exactly 99.85005 (= 99.9 × 0.9995) or 99.45025 (= 99.5 × 0.9995): round "
               "outputs minus Bridg's 5 bps. Husher's own site is 0.10–0.20 USDC lower (Bridg +15 bps higher); "
               "Meson's is +4 to +40 bps lower or 10 bps higher depending on route. Allbridge happens to match "
               "(its site shows 99.90). Hypothesis: static fee models rather than live quotes."},
    {"severity": "warning", "title": "Layerswap 3–13.5 bps below layerswap.io",
     "detail": "Consistent across samples: −13.5 bps on Solana-source routes, −3 to −8 bps on routes into Solana, "
               "after adding back Bridg's fee."},
    {"severity": "warning", "title": "CCTP gap is a comparison limit, not a verdict",
     "detail": "Circle's own bridge has no Solana, so CCTP is read from Portal (Wormhole). Portal hides its executor "
               "fee until a wallet connects, so its 99.99 is before that fee; Bridg's 98.67 on SOL→ETH (−127 bps) "
               "likely includes Ethereum destination gas."},
    {"severity": "warning", "title": "Bridg's fee isn't applied to every venue",
     "detail": "deBridge and Symbiosis match their own sites before adding back Bridg's 5 bps — Bridg appears not to "
               "take its fee on those rows. deBridge's own site adds a 1.05–2.58 USDC fee on top of the input that "
               "varies between loads; compared as out − fee, so Solana-source deBridge gaps swing."},
    {"severity": "info", "title": "Matches",
     "detail": "Skip Go (+1 to +2 bps), Allbridge Core (0.0), Across where listed (0.0), Mayan on most routes, and "
               "Relay on Solana-source routes match their own sites net of Bridg's fee."},
    {"severity": "info", "title": "Display quirks and anomalies",
     "detail": "Jumper once showed 120.36 USDC out for 100 in (excluded). Mayan, Meson and Husher show only 1–4 "
               "decimals. Across's input sometimes stays disabled on BSC→SOL. Allbridge charges a relayer fee on "
               "top in SOL/ETH (not converted). BSC 'USDC' is Binance-Peg USDC (18 dp, bridged) on every site."},
]


data = {
    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    "window": {"first": min(stamps), "last": max(stamps)},
    "full_base": "https://raw.githubusercontent.com/CainBeaudoin/bb/main/",  # full-page PNGs stay out of the Vercel upload
    "amount": 100, "routes": ROUTE_ORDER, "sites": SITE_LABEL, "site_urls": SITE_URL,
    "venues": [n for n in ADAPTERS if n != "bridg" and getattr(ADAPTERS[n], "kind", "venue") == "venue"],
    "platforms": [n for n in ADAPTERS if getattr(ADAPTERS[n], "kind", "venue") == "platform"],
    "venue_routes": {n: ["->".join(r) for r in a.routes] for n, a in ADAPTERS.items() if getattr(a, "routes", None)},
    "blocked": [{"venue": k, "label": SITE_LABEL.get(k, k), **v} for k, v in BLOCKED.items() if v.get("kind", "venue") == "venue"],
    "blocked_platforms": [{"venue": k, "label": SITE_LABEL.get(k, k), **v} for k, v in BLOCKED.items() if v.get("kind") == "platform"],
    "bridg_only": sorted({v["venue_id"] for bd in boards for v in bd["venues"]}
                         - {getattr(a, "bridg_id", None) for a in ADAPTERS.values()} - set(BLOCKED)),
    "competitors": csum, "route_winners": winners,
    "summary": summary, "samples": rows, "boards": boards, "receipts": receipts,
    "failures": failures, "issues": issues,
    "n_runs": len(runs), "n_records": sum(len(v) for v in runs.values()),
}
os.makedirs("dashboard", exist_ok=True)
json.dump(data, open("dashboard/data.json", "w"), separators=(",", ":"))
print(f"dashboard/data.json: {len(summary)} summary rows, {len(rows)} samples, {len(receipts)} receipts, "
      f"{len(failures)} failures, {os.path.getsize('dashboard/data.json')//1024} KB")
