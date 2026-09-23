"""Build Bridg_Competitive_Benchmark.xlsx from the raw JSONL + adapter registry.

Sheets: Dashboard, Competitor Matrix, Venue Analysis, Receipts, Platform Registry, Raw Quotes, Issues,
One-Pager Export. Per-sample tables hold inputs (blue); gaps, savings, averages and verdicts are formulas.
"""
import json
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.formatting.rule import CellIsRule
from compare import load_runs, build_rows, build_competitor_rows
from sites import ADAPTERS, BLOCKED

RAW = "data/raw_quotes.jsonl"
OUT = "Bridg_Competitive_Benchmark.xlsx"
GH = "https://raw.githubusercontent.com/CainBeaudoin/bb/main/"
D = json.load(open("dashboard/data.json"))
S = D["sites"]
ROUTES = D["routes"]
VENUES = D["venues"]
PLATFORMS = D.get("platforms", [])
runs = load_runs(RAW)
vrows = build_rows(runs)
crows = build_competitor_rows(runs)

F = "Arial"
H1 = Font(name=F, size=16, bold=True)
H2 = Font(name=F, size=12, bold=True)
HDR = Font(name=F, size=10, bold=True, color="FFFFFF")
BODY = Font(name=F, size=10)
INPUT = Font(name=F, size=10, color="0000FF")      # hardcoded observations
LINK = Font(name=F, size=10, color="008000")       # cross-sheet links
MUTED = Font(name=F, size=9, italic=True, color="666666")
HFILL = PatternFill("solid", fgColor="1F2937")
BAND = PatternFill("solid", fgColor="F3F4F6")
THIN = Border(bottom=Side(style="thin", color="D1D5DB"))
RED = PatternFill("solid", fgColor="F6CDCC")
BLUE = PatternFill("solid", fgColor="CDE2FB")
GRAY = PatternFill("solid", fgColor="E5E7EB")
BPS = '+0.0;-0.0;0.0'
USDC = '0.000000'

wb = Workbook()
wb.calculation.fullCalcOnLoad = True  # formulas are written without cached values


def arrow(r):
    return r.replace("->", " → ")


def header(ws, row, cols, widths=None):
    for i, c in enumerate(cols, 1):
        cell = ws.cell(row=row, column=i, value=c)
        cell.font, cell.fill = HDR, HFILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = 30
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[L(i)].width = w
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def put(ws, r, c, v, font=BODY, fmt=None):
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = font
    if fmt:
        cell.number_format = fmt
    return cell


def diverging(ws, rng):
    ws.conditional_formatting.add(rng, CellIsRule(operator="lessThan", formula=["-2"], fill=RED))
    ws.conditional_formatting.add(rng, CellIsRule(operator="greaterThan", formula=["2"], fill=BLUE))


# ------------------------------------------------------------------ Raw Quotes (immutable record, one row per site)
raw = wb.active
raw.title = "Raw Quotes"
cols = ["Run ID", "Route", "Sample", "Site", "Kind", "Status", "requestStart (UTC)", "quoteVisible (UTC)",
        "screenshotAt (UTC)", "Δ vs Bridg (s)", "Out (USDC)", "Fee on top", "Fee token", "Detail", "Page URL"]
header(raw, 1, cols, [14, 11, 8, 16, 9, 12, 25, 25, 25, 11, 13, 11, 10, 60, 50])
r = 2
for run_id, recs in runs.items():
    for x in recs:
        q = x.get("quote") or {}
        out = q.get("out", q.get("best_out"))
        detail = ""
        if x["site"] == "bridg" and q:
            detail = f"best via {q.get('detail_route')}; {q.get('priced')} venues priced; fees {q.get('detail_fees')}"
        elif q:
            detail = "; ".join(f"{k}={v}" for k, v in q.items()
                               if k not in ("out", "routes", "route_cards", "venues", "amount_in") and v not in (None, "", []))[:300]
        vals = [run_id, x["route"], x["sample"], S.get(x["site"], x["site"]),
                getattr(ADAPTERS.get(x["site"]), "kind", "venue") if x["site"] != "bridg" else "bridg",
                x.get("status"), x.get("requestStart"), x.get("quoteVisible"), x.get("screenshotAt"),
                x.get("gap_vs_bridg_s"), out, q.get("fixed_fee_on_top"), q.get("fixed_fee_token"),
                detail or (x.get("error") or "")[:200], x.get("url")]
        for c, v in enumerate(vals, 1):
            put(raw, r, c, v, INPUT if c in (10, 11, 12) else BODY, USDC if c == 11 else None)
        r += 1
raw.auto_filter.ref = f"A1:{L(len(cols))}{r - 1}"
put(raw, r + 1, 1, "Append-only record from runner.py (data/raw_quotes.jsonl). Blue = observed values read from each site's UI. "
    "Times are UTC with milliseconds; Δ = |quoteVisible − Bridg quoteVisible| in the same synchronized run.", MUTED)

# ------------------------------------------------------------------ Venue Analysis
va = wb.create_sheet("Venue Analysis", 0)
put(va, 1, 1, "Venue Analysis — is Bridg's listed quote for each venue the same as the venue's own site?", H1)
put(va, 2, 1, "Gap (bps) = (Bridg listed − venue direct) / 100 × 10,000. Ex-fee adds Bridg's platform fee back. "
    "Direct = venue out − any USDC fee charged on top of the 100 input. Blue = observed inputs; black = formulas.", MUTED)
# per-sample table starts at row 5 in columns A..M; summary block to the right
cols = ["Route", "Sample", "Venue", "Bridg listed", "Compare only", "Venue out", "USDC fee on top", "Direct (cmp)",
        "Gap bps", "Bridg fee (USDC)", "Gap ex-fee bps", "Δt (s)", "Note"]
header(va, 4, cols, [11, 8, 16, 13, 9, 13, 11, 13, 10, 11, 11, 8, 48])
r0 = 5
rows_sorted = sorted(vrows, key=lambda x: (ROUTES.index(x["route"]), VENUES.index(x["venue"]) if x["venue"] in VENUES else 99, x["sample"]))
for i, x in enumerate(rows_sorted):
    r = r0 + i
    put(va, r, 1, arrow(x["route"])); put(va, r, 2, x["sample"]); put(va, r, 3, S.get(x["venue"], x["venue"]))
    put(va, r, 4, x["bridg_listed"] if x["bridg_listed"] is not None else "not listed", INPUT, USDC)
    put(va, r, 5, "yes" if x.get("bridg_compare_only") else "")
    anomaly = "ANOMALY" in (x.get("direct_note") or "")
    put(va, r, 6, x["direct_out"], INPUT, USDC)
    usdc_fee = x.get("direct_fixed_fee") if x.get("direct_out_fee_adj") is not None else None
    put(va, r, 7, usdc_fee, INPUT, USDC)
    put(va, r, 8, "excluded" if anomaly else f'=IF(ISNUMBER(F{r}),F{r}-N(G{r}),"")', BODY, USDC)
    put(va, r, 9, f'=IF(AND(ISNUMBER(D{r}),ISNUMBER(H{r})),(D{r}-H{r})/100*10000,"")', BODY, BPS)
    put(va, r, 10, x.get("bridg_fee_observed"), INPUT, USDC)
    put(va, r, 11, f'=IF(ISNUMBER(I{r}),I{r}+N(J{r})/100*10000,"")', BODY, BPS)
    put(va, r, 12, x.get("gap_s"), INPUT, "0.00")
    put(va, r, 13, x.get("direct_note") or "")
rN = r0 + len(rows_sorted) - 1
diverging(va, f"K{r0}:K{rN}")
va.auto_filter.ref = f"A4:M{rN}"
# summary block: columns O..X
sc = 15
scols = ["Route", "Venue", "Samples", "Listed on Bridg", "Bridg avg", "Direct avg", "Gap bps (avg)", "Ex-fee bps (avg)",
         "Tolerance bps", "Verdict"]
for i, c in enumerate(scols):
    cell = va.cell(row=4, column=sc + i, value=c)
    cell.font, cell.fill = HDR, HFILL
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
for i, w in enumerate([11, 16, 8, 9, 12, 12, 11, 11, 9, 30]):
    va.column_dimensions[L(sc + i)].width = w
RA, RC = f"$A${r0}:$A${rN}", f"$C${r0}:$C${rN}"
sr = 5
summary_rows = {}
for route in ROUTES:
    for v in VENUES:
        if not any(x["route"] == route and x["venue"] == v for x in vrows):
            continue
        rt, vn = arrow(route), S.get(v, v)
        c = lambda k: L(sc + k)
        put(va, sr, sc, rt); put(va, sr, sc + 1, vn)
        crit = f'{RA},{c(0)}{sr},{RC},{c(1)}{sr}'
        put(va, sr, sc + 2, f"=COUNTIFS({crit})")
        put(va, sr, sc + 3, f"=COUNTIFS({crit},$D${r0}:$D${rN},\">0\")")
        put(va, sr, sc + 4, f'=IFERROR(AVERAGEIFS($D${r0}:$D${rN},{crit}),"—")', BODY, USDC)
        put(va, sr, sc + 5, f'=IFERROR(AVERAGEIFS($H${r0}:$H${rN},{crit}),"—")', BODY, USDC)
        put(va, sr, sc + 6, f'=IFERROR(AVERAGEIFS($I${r0}:$I${rN},{crit}),"—")', BODY, BPS)
        put(va, sr, sc + 7, f'=IFERROR(AVERAGEIFS($K${r0}:$K${rN},{crit}),"—")', BODY, BPS)
        put(va, sr, sc + 8, 4 if v == "mayan" else 2, INPUT)
        g, raw_, tol, n = f"{c(7)}{sr}", f"{c(6)}{sr}", f"{c(8)}{sr}", f"{c(3)}{sr}"
        put(va, sr, sc + 9, f'=IF({n}=0,"NOT LISTED on Bridg",IF(NOT(ISNUMBER({g})),"No direct quote",'
                            f'IF(ABS({g})<={tol},"Match (net of Bridg fee)",IF(ABS({raw_})<={tol},"Match (Bridg fee not applied)",'
                            f'IF({g}<0,"Bridg LOWER than venue","Bridg HIGHER than venue")))))')
        summary_rows[(route, v)] = sr
        sr += 1
diverging(va, f"{L(sc + 7)}5:{L(sc + 7)}{sr - 1}")
put(va, sr + 1, sc, "Tolerance: ±2 bps (±4 for Mayan: Dutch-auction pricing and 2–4 dp display). Assumption set by the analyst.", MUTED)
VA_SUM = (5, sr - 1, sc)

# ------------------------------------------------------------------ Competitor Matrix
cm = wb.create_sheet("Competitor Matrix", 0)
put(cm, 1, 1, "Competitor Matrix — does a user get more on Bridg, or by going direct?", H1)
put(cm, 2, 1, "Savings (bps) = (Bridg best − other) / 100 × 10,000. Positive = Bridg pays more. Bridg best = what Bridg's "
    "own page says you receive on its best-price route. Source-chain gas paid separately is not counted on either side.", MUTED)
# per-sample table, rows from 30 down; matrix at the top
MAT_TOP = 4
sites_order = PLATFORMS + VENUES
first_sample_row = MAT_TOP + len(sites_order) + len(BLOCKED) + 12
cols = ["Route", "Sample", "Site", "Kind", "Bridg best", "Bridg best via", "Other out (cmp)", "Savings bps", "Fee on top in SOL/ETH (not counted)"]
for i, c in enumerate(cols, 1):
    cell = cm.cell(row=first_sample_row - 1, column=i, value=c)
    cell.font, cell.fill = HDR, HFILL
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
put(cm, first_sample_row - 2, 1, "Per-sample observations", H2)
cs = sorted(crows, key=lambda x: (ROUTES.index(x["route"]), sites_order.index(x["site"]) if x["site"] in sites_order else 99, x["sample"]))
for i, x in enumerate(cs):
    r = first_sample_row + i
    put(cm, r, 1, arrow(x["route"])); put(cm, r, 2, x["sample"]); put(cm, r, 3, S.get(x["site"], x["site"])); put(cm, r, 4, x["kind"])
    put(cm, r, 5, x["bridg_best"], INPUT, USDC); put(cm, r, 6, x["bridg_best_route"])
    put(cm, r, 7, x["other_out"], INPUT, USDC)
    put(cm, r, 8, f"=(E{r}-G{r})/100*10000", BODY, BPS)
    put(cm, r, 9, "yes" if x["fee_on_top_not_converted"] else "")
cN = first_sample_row + len(cs) - 1
diverging(cm, f"H{first_sample_row}:H{cN}")
CA, CC = f"$A${first_sample_row}:$A${cN}", f"$C${first_sample_row}:$C${cN}"
# matrix: sites × routes of average savings
put(cm, MAT_TOP - 0, 1, "Average savings (bps) by site and route", H2)
hr = MAT_TOP + 1
for i, c in enumerate(["Site", "Kind"] + [arrow(x) for x in ROUTES], 1):
    cell = cm.cell(row=hr, column=i, value=c)
    cell.font, cell.fill = HDR, HFILL
    cell.alignment = Alignment(horizontal="center", vertical="center")
widths = [16, 10] + [12] * len(ROUTES) + [40]
for i, w in enumerate(widths, 1):
    cm.column_dimensions[L(i)].width = max(cm.column_dimensions[L(i)].width or 0, w)
mr = hr + 1
for s in sites_order:
    put(cm, mr, 1, S.get(s, s)); put(cm, mr, 2, getattr(ADAPTERS[s], "kind", "venue"))
    for j, route in enumerate(ROUTES):
        col = 3 + j
        put(cm, mr, col, f'=IFERROR(AVERAGEIFS($H${first_sample_row}:$H${cN},{CA},"{arrow(route)}",{CC},$A{mr}),"n/a")', BODY, BPS)
    mr += 1
for k, b in BLOCKED.items():
    if b.get("kind") != "platform":
        continue
    put(cm, mr, 1, S.get(k, k)); put(cm, mr, 2, "platform")
    put(cm, mr, 3, "BLOCKED — " + b.get("reason", ""), MUTED)
    cm.merge_cells(start_row=mr, start_column=3, end_row=mr, end_column=2 + len(ROUTES))
    mr += 1
diverging(cm, f"C{hr + 1}:{L(2 + len(ROUTES))}{hr + len(sites_order)}")
MAT = (hr + 1, hr + len(sites_order))
# route winners under the matrix
wr = mr + 2
put(cm, wr, 1, "Route winners", H2)
for i, c in enumerate(["Route", "Bridg best (avg)", "Best elsewhere (avg out)", "Site", "Bridg vs best (bps)",
                       "Sites Bridg beats", "Sites beating Bridg"], 1):
    cell = cm.cell(row=wr + 1, column=i, value=c)
    cell.font, cell.fill = HDR, HFILL
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
cm.row_dimensions[wr + 1].height = 30
# helper: per-site average "other out" per route in hidden-ish columns to the right (K..)
hc = 12 + 1
put(cm, hr, hc, "Avg other out (helper)", MUTED)
for j, route in enumerate(ROUTES):
    put(cm, hr, hc + 1 + j, arrow(route), HDR).fill = HFILL
for i, s in enumerate(sites_order):
    rr = hr + 1 + i
    put(cm, rr, hc, S.get(s, s))
    for j, route in enumerate(ROUTES):
        put(cm, rr, hc + 1 + j, f'=IFERROR(AVERAGEIFS($G${first_sample_row}:$G${cN},{CA},"{arrow(route)}",{CC},${L(hc)}{rr}),"")', BODY, USDC)
WIN = {}
for j, route in enumerate(ROUTES):
    r = wr + 2 + j
    oc = L(hc + 1 + j)
    rng = f"${oc}${hr + 1}:${oc}${hr + len(sites_order)}"
    mcol = L(3 + j)
    mrng = f"${mcol}${hr + 1}:${mcol}${hr + len(sites_order)}"
    put(cm, r, 1, arrow(route))
    # Bridg best averaged once per run, from Raw Quotes (Bridg rows carry its best "you receive")
    put(cm, r, 2, f"=IFERROR(AVERAGEIFS('Raw Quotes'!$K:$K,'Raw Quotes'!$B:$B,\"{route}\",'Raw Quotes'!$D:$D,\"Bridg\",'Raw Quotes'!$F:$F,\"OK\"),\"\")", LINK, USDC)
    put(cm, r, 3, f"=MAX({rng})", BODY, USDC)
    put(cm, r, 4, f"=INDEX(${L(hc)}${hr + 1}:${L(hc)}${hr + len(sites_order)},MATCH(C{r},{rng},0))")
    put(cm, r, 5, f"=(B{r}-C{r})/100*10000", BODY, BPS)
    put(cm, r, 6, f'=COUNTIF({mrng},">2")')
    put(cm, r, 7, f'=COUNTIF({mrng},"<-2")')
    put(cm, r, 8, "Bridg best is averaged per synchronized run (Raw Quotes); savings compare it with the best per-site average.", MUTED) if j == 0 else None
    WIN[route] = r
diverging(cm, f"E{wr + 2}:E{wr + 1 + len(ROUTES)}")

# ------------------------------------------------------------------ Receipts
rc = wb.create_sheet("Receipts")
cols = ["Route", "Sample", "Site", "requestStart (UTC)", "quoteVisible (UTC)", "screenshotAt (UTC)", "Δ vs Bridg (s)",
        "Out (USDC)", "Crop screenshot", "Crop SHA-256", "Full-page screenshot", "Full SHA-256"]
header(rc, 1, cols, [11, 8, 16, 25, 25, 25, 11, 13, 16, 66, 16, 66])
order = ["bridg"] + sites_order
recs = sorted(D["receipts"], key=lambda x: (ROUTES.index(x["route"]), x["sample"], order.index(x["site"]) if x["site"] in order else 99))
for i, x in enumerate(recs):
    r = 2 + i
    vals = [arrow(x["route"]), x["sample"], S.get(x["site"], x["site"]), x["requestStart"], x["quoteVisible"],
            x["screenshotAt"], x.get("gap_s"), x.get("out")]
    for c, v in enumerate(vals, 1):
        put(rc, r, c, v, INPUT if c in (7, 8) else BODY, USDC if c == 8 else None)
    for c, key in ((9, "crop"), (11, "full")):
        cell = put(rc, r, c, "open", Font(name=F, size=10, color="1D4ED8", underline="single"))
        cell.hyperlink = GH + x[key]["path"]
        put(rc, r, c + 1, x[key]["sha256"], Font(name="Courier New", size=9))
rc.auto_filter.ref = f"A1:L{1 + len(recs)}"

# ------------------------------------------------------------------ Platform Registry
pr = wb.create_sheet("Platform Registry")
cols = ["Name", "Kind", "Status", "Routes quoted (own UI)", "Bridg venue id", "URL / method", "Reason / notes", "Checked"]
header(pr, 1, cols, [18, 10, 12, 44, 15, 50, 80, 22])
r = 2
urls = D.get("site_urls", {})
put(pr, r, 1, "Bridg"); put(pr, r, 2, "subject"); put(pr, r, 3, "WORKING"); put(pr, r, 4, "all 6")
put(pr, r, 6, "https://bridg.now/swap/"); put(pr, r, 7, "Per-venue live-quote board + best/fastest fee breakdown; no wallet needed"); r += 1
for n, a in ADAPTERS.items():
    if n == "bridg":
        continue
    rts = getattr(a, "routes", None)
    status = "WORKING" if not rts or len(rts) == 6 else "PARTIAL"
    put(pr, r, 1, S.get(n, n)); put(pr, r, 2, getattr(a, "kind", "venue")); put(pr, r, 3, status)
    put(pr, r, 4, "all 6" if not rts or len(rts) == 6 else ", ".join(arrow("->".join(x)) for x in rts))
    put(pr, r, 5, getattr(a, "bridg_id", None)); put(pr, r, 6, urls.get(n) or getattr(a, "label_url", None) or "")
    note = (a.__doc__ or "").strip().split("\n")[0][:300] if a.__doc__ else ""
    put(pr, r, 7, note)
    r += 1
for k, b in BLOCKED.items():
    put(pr, r, 1, S.get(k, k)); put(pr, r, 2, b.get("kind", "venue")); put(pr, r, 3, "BLOCKED")
    put(pr, r, 4, "none"); put(pr, r, 5, k if b.get("kind", "venue") == "venue" else None)
    put(pr, r, 6, b.get("url", "")); put(pr, r, 7, b.get("reason", "")); put(pr, r, 8, b.get("checked", ""))
    r += 1
for rr in range(2, r):
    pr.cell(row=rr, column=7).alignment = Alignment(wrap_text=True, vertical="top")
pr.conditional_formatting.add(f"C2:C{r - 1}", CellIsRule(operator="equal", formula=['"BLOCKED"'], fill=GRAY))

# ------------------------------------------------------------------ Issues
iss = wb.create_sheet("Issues")
header(iss, 1, ["#", "Severity", "Finding", "Detail"], [5, 11, 55, 120])
for i, x in enumerate(D["issues"], 1):
    put(iss, i + 1, 1, i); put(iss, i + 1, 2, x["severity"]); put(iss, i + 1, 3, x["title"]).font = Font(name=F, size=10, bold=True)
    put(iss, i + 1, 4, x["detail"]).alignment = Alignment(wrap_text=True, vertical="top")
    iss.cell(row=i + 1, column=3).alignment = Alignment(wrap_text=True, vertical="top")
fail_r = len(D["issues"]) + 4
put(iss, fail_r, 1, "Runs where a site returned no quote (kept in Raw Quotes)", H2)
for i, f in enumerate(D["failures"]):
    put(iss, fail_r + 1 + i, 2, f["status"]); put(iss, fail_r + 1 + i, 3, f"{S.get(f['site'], f['site'])} · {arrow(f['route'])} · sample {f['sample']}")
    put(iss, fail_r + 1 + i, 4, f["error"].split("\\n")[0][:200])

# ------------------------------------------------------------------ Dashboard
db = wb.create_sheet("Dashboard", 0)
db.column_dimensions["A"].width = 44
for c in "BCDEFGH":
    db.column_dimensions[c].width = 16
put(db, 1, 1, "Bridg Competitive Benchmark", H1)
put(db, 2, 1, f"100 USDC → USDC · 6 routes · quotes read from each site's own web UI, no wallet connected · "
    f"collected {D['window']['first'][:16].replace('T', ' ')} – {D['window']['last'][11:16]} UTC", MUTED)
vs0, vs1, vsc = VA_SUM
verd = f"'Venue Analysis'!${L(vsc + 9)}${vs0}:${L(vsc + 9)}${vs1}"
kpis = [
    ("Routes where Bridg's best beat every direct quote", f"=COUNTIF('Competitor Matrix'!$E${WIN[ROUTES[0]]}:$E${WIN[ROUTES[-1]]},\">=-2\")&\" / {len(ROUTES)}\""),
    ("Venue pairs where Bridg's listing matches the venue's site", f"=COUNTIF({verd},\"Match*\")&\" / \"&COUNTA({verd})"),
    ("… Bridg lists LESS than the venue's own site", f"=COUNTIF({verd},\"Bridg LOWER*\")"),
    ("… Bridg lists MORE than the venue's own site", f"=COUNTIF({verd},\"Bridg HIGHER*\")"),
    ("… venue quotes on its site but is missing from Bridg", f"=COUNTIF({verd},\"NOT LISTED*\")"),
    ("Worst venue-accuracy gap (bps, ex-Bridg fee)", f"=MIN('Venue Analysis'!${L(vsc + 7)}${vs0}:${L(vsc + 7)}${vs1})"),
    ("Venues / platforms compared", f"{len(VENUES)} venues + {len(PLATFORMS)} platforms"),
    ("Blocked (no public quote)", f"{sum(1 for b in BLOCKED.values() if b.get('kind', 'venue') == 'venue')} venues + "
                                  f"{sum(1 for b in BLOCKED.values() if b.get('kind') == 'platform')} platforms"),
]
put(db, 4, 1, "Headline", H2)
for i, (k, f) in enumerate(kpis):
    put(db, 5 + i, 1, k)
    put(db, 5 + i, 2, f, LINK if f.startswith("=") else BODY, BPS if "bps" in k else None).font = Font(name=F, size=11, bold=True,
                                                                                                      color="008000" if f.startswith("=") else "000000")
t = 5 + len(kpis) + 2
put(db, t, 1, "Route winners (Bridg best vs best direct quote)", H2)
for i, c in enumerate(["Route", "Bridg best", "Best elsewhere", "Site", "Bridg vs best (bps)", "Sites Bridg beats", "Sites beating Bridg"], 1):
    cell = db.cell(row=t + 1, column=i, value=c)
    cell.font, cell.fill = HDR, HFILL
    cell.alignment = Alignment(horizontal="center", wrap_text=True)
for j, route in enumerate(ROUTES):
    r = t + 2 + j
    for c in range(1, 8):
        put(db, r, c, f"='Competitor Matrix'!{L(c)}{WIN[route]}", LINK, [None, USDC, USDC, None, BPS, None, None][c - 1])
diverging(db, f"E{t + 2}:E{t + 1 + len(ROUTES)}")
t2 = t + 2 + len(ROUTES) + 1
put(db, t2, 1, "Venue accuracy (avg gap ex-Bridg fee, bps) — Bridg listed vs venue's own site", H2)
for i, c in enumerate(["Venue"] + [arrow(x) for x in ROUTES], 1):
    cell = db.cell(row=t2 + 1, column=i, value=c)
    cell.font, cell.fill = HDR, HFILL
    cell.alignment = Alignment(horizontal="center")
for i, v in enumerate(VENUES):
    r = t2 + 2 + i
    put(db, r, 1, S.get(v, v))
    for j, route in enumerate(ROUTES):
        sr_ = summary_rows.get((route, v))
        if sr_ is None:
            put(db, r, 2 + j, "n/a", MUTED)
        else:
            put(db, r, 2 + j, f"=IF('Venue Analysis'!{L(vsc + 3)}{sr_}=0,\"not listed\",'Venue Analysis'!{L(vsc + 7)}{sr_})", LINK, BPS)
diverging(db, f"B{t2 + 2}:{L(1 + len(ROUTES))}{t2 + 1 + len(VENUES)}")
put(db, t2 + 3 + len(VENUES), 1, "Green = linked from other sheets. Red cells: Bridg lower / going direct pays more; blue: Bridg higher / Bridg pays more. "
    "Hypotheses in Issues are unverified.", MUTED)

# ------------------------------------------------------------------ One-Pager Export
op = wb.create_sheet("One-Pager Export")
op.column_dimensions["A"].width = 30
for c in "BCDEFG":
    op.column_dimensions[c].width = 15
put(op, 1, 1, "Bridg Competitive Benchmark — one-pager", H1)
put(op, 2, 1, "=Dashboard!A2", MUTED)
put(op, 4, 1, "Headline", H2)
for i in range(len(kpis)):
    put(op, 5 + i, 1, f"=Dashboard!A{5 + i}", LINK)
    put(op, 5 + i, 2, f"=Dashboard!B{5 + i}", Font(name=F, size=10, bold=True, color="008000"), BPS if "bps" in kpis[i][0] else None)
o = 5 + len(kpis) + 1
put(op, o, 1, "Route winners", H2)
for j in range(len(ROUTES) + 1):
    for c in range(1, 8):
        src = f"=Dashboard!{L(c)}{t + 1 + j}"
        cell = put(op, o + 1 + j, c, src, HDR if j == 0 else LINK, [None, USDC, USDC, None, BPS, None, None][c - 1] if j else None)
        if j == 0:
            cell.fill = HFILL
o2 = o + len(ROUTES) + 3
put(op, o2, 1, "Top findings", H2)
for i, x in enumerate([x for x in D["issues"] if x["severity"] == "serious"][:5]):
    put(op, o2 + 1 + i, 1, f"=Issues!C{D['issues'].index(x) + 2}", Font(name=F, size=10, bold=True, color="008000"))
    op.merge_cells(start_row=o2 + 1 + i, start_column=1, end_row=o2 + 1 + i, end_column=7)
put(op, o2 + 8, 1, "Method: fresh Playwright browser per site, no wallet; 100 typed into all pages at one barrier; quotes within ~1.5 s "
    "of Bridg's. Evidence: screenshots + SHA-256 in Receipts. Dashboard: see repo README.", MUTED)
op.merge_cells(start_row=o2 + 8, start_column=1, end_row=o2 + 8, end_column=7)
op.page_setup.orientation = "landscape"
op.page_setup.fitToWidth = 1
op.page_setup.fitToHeight = 1
op.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
op.print_area = f"A1:G{o2 + 8}"

# sheet order per spec
order = ["Dashboard", "Competitor Matrix", "Venue Analysis", "Receipts", "Platform Registry", "Raw Quotes", "Issues", "One-Pager Export"]
wb._sheets = [wb[n] for n in order]
wb.active = 0
wb.save(OUT)
print(OUT, "saved;", {n: wb[n].max_row for n in order})
