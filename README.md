# Bridg competitive benchmark — Bridg vs direct-venue UI cross-reference

Clean Playwright Chromium (fresh context per site, no wallet, never signs). 100 USDC → USDC.

- `sites.py`   per-site adapters (route selection, typing, quote parsing)
- `runner.py`  barrier-synchronised runs → `data/raw_quotes.jsonl` (append-only) + `evidence/<UTC>/` screenshots (full + crop, SHA-256 in JSONL)
- `compare.py` → `data/normalized.csv` + per-route/venue summary

    .venv/bin/python runner.py --samples 3
    .venv/bin/python compare.py

Notes: deBridge charges a fixed fee on top of the input; its direct quote is compared as `out − fixed fee`.
BSC "USDC" everywhere is Binance-Peg USDC 0x8AC7…580d (18 dp, bridged, not native Circle). Mayan UI rounds to 2–4 dp.

## Dashboard (Vercel)

`index.html` at the repo root is a static dashboard that reads `dashboard/data.json` and links the screenshots under `evidence/`.
Deploys on Vercel as a static site: `vercel.json` forces no framework/build, `.vercelignore` keeps the Python out. Install the runner deps with `pip install -r requirements-bench.txt`.

After a new run:

    .venv/bin/python runner.py --samples 3
    .venv/bin/python build_dashboard.py   # rewrites data/normalized.csv + dashboard/data.json
    git add -A && git commit -m "New benchmark run" && git push

Findings text lives in `build_dashboard.py` (`issues`) — update it when the numbers change.
Local preview: `python3 -m http.server 8765` then open http://localhost:8765.

## Workbook

    .venv/bin/python build_dashboard.py && .venv/bin/python build_xlsx.py

`Bridg_Competitive_Benchmark.xlsx`: Dashboard, Competitor Matrix, Venue Analysis, Receipts, Platform Registry,
Raw Quotes, Issues, One-Pager Export. Observations are blue inputs; gaps, savings, averages and verdicts are live
formulas (recalculated on open).

## Timing

Each run uses two barriers across all sites (fresh browser context each):
1. **typed** — "100" is typed into every page at the same instant (`requestStart`);
2. **values read** — once every site's quote has settled, all sites read the value that gets compared at the same
   instant (`valueReadAt`), then screenshot (`screenshotAt`). `quoteVisible` / `settledAt` are kept for reference.

Every record carries `campaign`, and each run records `run_sync` (typed / value-read / screenshot spreads). Sites whose
value was read >2 s from Bridg's are flagged, the route is retried, and flagged records are excluded. The dashboard and
workbook use the latest campaign only (`compare.load_runs(raw, campaign="latest")`); older sessions stay in the raw file.
