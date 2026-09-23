"""Package raw quotes + normalized comparison + receipts into dashboard/data.json for index.html."""
import json, os
from datetime import datetime, timezone
from compare import load_runs, build_rows, summarize, write_csv, build_competitor_rows, summarize_competitors
from sites import ADAPTERS, BLOCKED

RAW = "data/raw_quotes.jsonl"
SITE_LABEL = {"bridg": "BRDG", "relay": "Relay", "across": "Across", "mayan": "Mayan",
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

# per route: BRDG's best vs the best any other site showed directly (averaged per site across samples)
winners = []
for route in ["SOL->ETH", "ETH->SOL", "SOL->BSC", "BSC->SOL", "SOL->Base", "Base->SOL"]:
    cs = [c for c in csum if c["route"] == route]
    if not cs:
        continue
    top = max(cs, key=lambda c: c["other_avg"])
    # BRDG best averaged once per synchronized run (not weighted by how many sites quoted in that run)
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
sync_runs = []
for run_id, recs in runs.items():
    if recs and recs[0].get("run_sync"):
        b0 = next((x for x in recs if x["site"] == "bridg"), recs[0])
        sync_runs.append({"run_id": run_id, "route": b0["route"], "sample": b0["sample"],
                          "typedAt": b0.get("requestStart"), "valueReadAt": b0.get("valueReadAt"), **recs[0]["run_sync"]})
    for r in recs:
        for k in ("requestStart", "quoteVisible", "valueReadAt", "screenshotAt"):
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
                         "valueReadAt": r.get("valueReadAt"), "settledAt": r.get("settledAt"),
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
    {"severity": "warning", "title": "Relay ~20 bps below relay.link into Solana — explained: new USDC account cost",
     "detail": "ETH→SOL, BSC→SOL, Base→SOL: −19.9 to −20.0 bps in every sample after adding back BRDG's 5 bps. Verified "
               "via BRDG's API (indicative quotes, 14:45:35 UTC, saved in data/api/): for a recipient that already holds USDC, BRDG prices Relay "
               "at 99.945676 — identical to relay.link. For a fresh Solana address, Relay's 'destination fill gas' rises from "
               "0.004 to 0.205 USDC (+20.1 bps): the cost of creating the recipient's USDC token account. BRDG's no-wallet "
               "page prices that case; relay.link's no-wallet page assumes the account exists. Mayan and NEAR Intents shift "
               "the same way. SOL→ETH was −25 bps this campaign (Ethereum gas elevated)."},
    {"severity": "serious", "title": "LI.FI and SimpleSwap rows are far below their own sites",
     "detail": "LI.FI: 15–96 bps below jumper.exchange's Best Return on every route. BRDG's API shows a 'LIFI Fixed Fee' "
               "of 0.25 USDC (25 bps) on its LI.FI row that Jumper doesn't charge, plus the ~0.20 new-account cost into "
               "Solana — together ~45 bps; the rest is unexplained (likely a different route). SimpleSwap: 48–272 bps below "
               "simpleswap.io's default floating 'Best rate'; BRDG's API lists no fee breakdown for it."},
    {"severity": "serious", "title": "Meson and Husher rows are flat fee formulas, not live quotes (confirmed)",
     "detail": "BRDG's API fee breakdown: Meson = a fixed 'Meson LP fee' of 0.50 USDC; Husher = fixed 0.20 exchange fee + "
               "0.30 delivery fee; Allbridge = fixed 0.10 CCTP service fee. So BRDG shows exactly 99.5/99.9 minus its own fee "
               "(99.45025 / 99.85005; 99.75015 on SOL→ETH at the 15 bps tier). When Ethereum gas rose, Meson's own site dropped "
               "to 98.56 on SOL→ETH while BRDG still showed 99.75 (+134 bps). Husher's own site charges 0.35% (not 0.20), so "
               "it's 15–25 bps lower than BRDG's row. Allbridge matches because its site also shows a flat 99.90."},
    {"severity": "serious", "title": "BRDG lists venues whose own site can't quote these routes",
     "detail": "Rhino.fi (BRDG's best price on SOL→BSC) — retail app shut down Aug 2026. Eco — its portal has no "
               "Solana or BNB Chain, yet BRDG lists Eco on SOL↔ETH/Base. NEAR Intents — public app moved behind a login."},
    {"severity": "serious", "title": "Across missing from BRDG on 4 of 6 routes",
     "detail": "Not listed on ETH→SOL, BSC→SOL, Base→SOL or SOL→BSC although across.to quotes 99.98–99.99. Where "
               "listed (SOL→ETH, SOL→Base) it matches exactly net of BRDG's fee and is BRDG's best price."},
    {"severity": "info", "title": "Competitor platforms: BRDG beats OpenSea; the rest can't be quoted",
     "detail": "OpenSea swap (Relay; LI.FI on SOL→Base; 0% OpenSea fee promo) pays 89 bps less than BRDG's best on "
               "SOL→ETH, ~10 bps less on ETH→SOL and Base→SOL, ~1 bp less on SOL→Base; no BNB Chain. Signed in (by the "
               "user) and re-checked: Axiom has a cross-chain Convert, but the amount is capped at the wallet balance, so "
               "100 USDC can't be priced unfunded (deposit fees shown only at its $2–3 minimum). GMGN's Convert needs 2FA "
               "plus a 3-hour lock; its deposits are Solana-only. Pump.fun's web deposit is Solana-only. FOMO pools "
               "deposits from 7 chains into one USD balance with no quote."},
    {"severity": "warning", "title": "Layerswap 3–13.5 bps below layerswap.io",
     "detail": "Identical across samples: −13.4/−13.5 bps on Solana-source routes, −3.2 to −7.9 bps into Solana."},
    {"severity": "warning", "title": "CCTP gap is Portal hiding a fee, not a BRDG error",
     "detail": "Circle's own bridge has no Solana, so CCTP is read from Portal (Wormhole), which hides its relayer fee until "
               "a wallet connects. BRDG's API itemises it: 'Circle Forwarding Service fee and destination gas' = 0.16 USDC "
               "on ETH→SOL, which is the −14 to −15 bps gap into Solana. On SOL→ETH (−332 bps this campaign) the same line "
               "carries Ethereum destination gas, which was elevated."},
    {"severity": "warning", "title": "BRDG's fee isn't applied to every venue; deBridge's fixed fee jumps around",
     "detail": "deBridge, Symbiosis and Mayan (ETH→SOL) match their own sites before adding back BRDG's 5 bps — BRDG "
               "appears not to take its fee on those rows. deBridge's own site adds a fixed fee on top of the input that "
               "changed a lot between loads (it's compared as out − fee), so some deBridge gaps swing widely."},
    {"severity": "info", "title": "Matches",
     "detail": "Across where listed (0.0), Allbridge Core (0.0), Skip Go (+1.2 to +1.6; volatile on SOL→ETH), Mayan on "
               "most routes, and Relay on SOL→BSC/SOL→Base match their own sites net of BRDG's fee."},
    {"severity": "info", "title": "Timing: one campaign, values read within 10 ms",
     "detail": "Everything on this page comes from one campaign (14:18:34–14:30:59 UTC). In each run all sites got '100' "
               "typed at the same instant and read the compared value at the same instant (second barrier): worst spread "
               "10 ms. Earlier sessions (kept in the raw file) compared values read up to 5.8 s apart and are excluded."},
    {"severity": "info", "title": "Display quirks",
     "detail": "Mayan, Meson and Husher show only 1–4 decimals. Allbridge charges a relayer fee on top in SOL/ETH (not "
               "converted). SimpleSwap returned no quote in 2 runs. In an earlier session Jumper once displayed 120.36 USDC "
               "out for 100 in. BSC 'USDC' is Binance-Peg USDC (18 dp, bridged) on every site."},
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
    "campaign": next((x.get("campaign") for recs in runs.values() for x in recs if x.get("campaign")), None),
    "sync_runs": sorted(sync_runs, key=lambda x: x["typedAt"] or ""),
    "sync": {"max_value_read_spread_s": max((x["value_read_spread_s"] for x in sync_runs), default=None),
             "max_typed_spread_s": max((x["typed_spread_s"] for x in sync_runs), default=None),
             "max_screenshot_spread_s": max((x["screenshot_spread_s"] for x in sync_runs), default=None)},
    "summary": summary, "samples": rows, "boards": boards, "receipts": receipts,
    "failures": failures, "issues": issues,
    "n_runs": len(runs), "n_records": sum(len(v) for v in runs.values()),
}
os.makedirs("dashboard", exist_ok=True)
json.dump(data, open("dashboard/data.json", "w"), separators=(",", ":"))
print(f"dashboard/data.json: {len(summary)} summary rows, {len(rows)} samples, {len(receipts)} receipts, "
      f"{len(failures)} failures, {os.path.getsize('dashboard/data.json')//1024} KB")
