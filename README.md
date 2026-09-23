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

## Repository map

| Path | What it is |
|---|---|
| `docs/PLATFORMS.md` | How every venue/platform was reached, click paths for the signed-in platform checks (Axiom, GMGN, Pump.fun, FOMO), OpenSea, URL patterns, API diagnostics |
| `sites.py` | Route/chain/USDC config + adapters for Bridg, Relay, deBridge, LI.FI (Jumper), Across, Mayan; loads `adapters/` |
| `adapters/*.py` | One adapter per additional venue/platform; blocked ones hold a `BLOCKED` dict (reason, URL, check time) |
| `runner.py` | Synchronized runs (typed barrier + value-read barrier), screenshots + SHA-256 → `data/raw_quotes.jsonl`, `evidence/` |
| `compare.py` | Bridg-vs-venue gaps and Bridg-vs-direct savings (latest campaign, flagged records dropped) |
| `build_dashboard.py` | `dashboard/data.json` + findings text for `index.html` |
| `build_xlsx.py` | `Bridg_Competitive_Benchmark.xlsx` |
| `index.html` | Static dashboard (Vercel) |
| `data/raw_quotes.jsonl` | Append-only raw records (all sessions) |
| `data/normalized.csv` | Per-sample comparison rows (latest campaign) |
| `data/api/` | Bridg API indicative quotes used to explain gaps |
| `evidence/<UTC>/` | Full-page + cropped screenshots and page text per site/route/sample |
| `tools/login.py` | Opens an isolated headed browser for the owner to sign in themselves (session kept in ignored `profiles/`) |
| `tools/dbg.py`, `tools/probe.py`, `tools/dom*.py` | Adapter debugging helpers |

No credentials, account emails, wallet/deposit addresses or session data are stored in this repo.
