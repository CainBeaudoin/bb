"""Package raw quotes + normalized comparison + receipts into dashboard/data.json for index.html."""
import json, os
from datetime import datetime, timezone
from compare import load_runs, build_rows, summarize, write_csv
from sites import ADAPTERS, BLOCKED

RAW = "data/raw_quotes.jsonl"
SITE_LABEL = {"bridg": "Bridg", "relay": "Relay", "across": "Across", "mayan": "Mayan",
              "lifi": "LI.FI (Jumper)", "debridge": "deBridge", "layerswap": "Layerswap", "rhino": "Rhino.fi",
              "husher": "Husher", "simpleswap": "SimpleSwap", "meson": "Meson", "symbiosis": "Symbiosis",
              "near-intents": "NEAR Intents", "skip-go": "Skip Go", "eco": "Eco",
              "allbridge-core": "Allbridge Core", "cctp": "CCTP"}
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
    {"severity": "serious", "title": "Relay priced ~20.6 bps below relay.link on every EVM → Solana route",
     "detail": "Bridg's Relay row is 25.6 bps under relay.link on ETH→SOL, BSC→SOL and Base→SOL in every sample; "
               "5 bps is Bridg's own fee, leaving ~0.21 USDC more 'Relay fee'. Solana-source routes match. "
               "Hypothesis (unverified): Bridg's quote includes Solana USDC token-account rent that relay.link omits "
               "when no recipient wallet is set."},
    {"severity": "serious", "title": "Across missing from Bridg on 4 of 6 routes",
     "detail": "Not listed on ETH→SOL, BSC→SOL, Base→SOL or SOL→BSC although across.to quotes 99.98–99.99. "
               "Where listed (SOL→ETH, SOL→Base) it matches exactly net of Bridg's fee."},
    {"severity": "serious", "title": "LI.FI row 45–97 bps below jumper.exchange",
     "detail": "Bridg's 'Lifi' quote is below Jumper's Best Return on every route; one Bridg breakdown showed "
               "'Lifi fee 1.0167 USDC'. Jumper often routes via Relay or Polymer. Hypothesis (unverified): a different "
               "LI.FI route or an integrator fee in Bridg's LI.FI request."},
    {"severity": "warning", "title": "deBridge fixed fee is charged on top of the input on its own site",
     "detail": "app.debridge.finance adds a 1.05–2.58 USDC fee on top of the 100 input; Bridg deducts it from output. "
               "Compared on the same basis (direct out − fixed fee), deBridge matches — and Bridg appears not to "
               "take its 5 bps on deBridge."},
    {"severity": "warning", "title": "Jumper displayed 120.36 USDC out for 100 in (BSC→SOL, sample 2)",
     "detail": "Mayan (Swift) route on jumper.exchange; screenshot receipt kept, value excluded from averages."},
    {"severity": "warning", "title": "Across UI input stays disabled on BSC→SOL in ~half of loads",
     "detail": "Only 2 good samples for Across on BSC→SOL."},
    {"severity": "info", "title": "BSC 'USDC' is Binance-Peg USDC everywhere",
     "detail": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d, 18 decimals — bridged, not native Circle USDC. "
               "Every site including Bridg used this contract."},
    {"severity": "info", "title": "Mayan shows 2–4 decimal places and moves between quotes",
     "detail": "Dutch-auction (Swift) pricing; sub-bp comparisons on Mayan are not meaningful. "
               "Bridg tags Mayan as 'Compare only' (not executable via Bridg)."},
]

data = {
    "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    "window": {"first": min(stamps), "last": max(stamps)},
    "amount": 100, "routes": ROUTE_ORDER, "sites": SITE_LABEL, "site_urls": SITE_URL,
    "venues": [n for n in ADAPTERS if n != "bridg"],
    "venue_routes": {n: ["->".join(r) for r in a.routes] for n, a in ADAPTERS.items() if getattr(a, "routes", None)},
    "blocked": [{"venue": k, "label": SITE_LABEL.get(k, k), **v} for k, v in BLOCKED.items()],
    "bridg_only": sorted({v["venue_id"] for bd in boards for v in bd["venues"]}
                         - {getattr(a, "bridg_id", None) for a in ADAPTERS.values()} - set(BLOCKED)),
    "summary": summary, "samples": rows, "boards": boards, "receipts": receipts,
    "failures": failures, "issues": issues,
    "n_runs": len(runs), "n_records": sum(len(v) for v in runs.values()),
}
os.makedirs("dashboard", exist_ok=True)
json.dump(data, open("dashboard/data.json", "w"), separators=(",", ":"))
print(f"dashboard/data.json: {len(summary)} summary rows, {len(rows)} samples, {len(receipts)} receipts, "
      f"{len(failures)} failures, {os.path.getsize('dashboard/data.json')//1024} KB")
