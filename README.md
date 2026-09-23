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
Deploy on Vercel as a plain static project (Framework preset: Other, no build command, output dir = repo root).

After a new run:

    .venv/bin/python runner.py --samples 3
    .venv/bin/python build_dashboard.py   # rewrites data/normalized.csv + dashboard/data.json
    git add -A && git commit -m "New benchmark run" && git push

Findings text lives in `build_dashboard.py` (`issues`) — update it when the numbers change.
Local preview: `python3 -m http.server 8765` then open http://localhost:8765.
