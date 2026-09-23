"""Normalize raw JSONL into Bridg-vs-direct rows and a per-route/venue summary.

gap_bps = (Bridg's listed quote for venue − venue's own UI quote) / 100 × 10,000.
Positive = Bridg's listing shows more than the venue's own site.
"""
import csv, json, statistics, sys
from collections import defaultdict

from sites import ADAPTERS
VENUE_IDS = {n: a.bridg_id for n, a in ADAPTERS.items() if getattr(a, "bridg_id", None)}

def load_runs(raw):
    runs = defaultdict(list)
    for line in open(raw):
        r = json.loads(line)
        runs[r["run_id"]].append(r)
    return runs


def build_rows(runs):
  rows = []
  for run_id, recs in runs.items():
      by = {r["site"]: r for r in recs}
      b = by.get("bridg")
      if not b or b.get("status") != "OK":
          continue
      bq = b["quote"]
      listed = {v["venue_id"]: v for v in bq["venues"]}
      bridg_fees = {}
      for d in (bq, b.get("fastest_detail") or {}):
          if d.get("detail_route"):
              fee = dict(d.get("detail_fees") or []).get("Bridg fee", 0.0)
              bridg_fees[d["detail_route"].lower().replace(" ", "")] = fee
      for site, vid in VENUE_IDS.items():
          v = by.get(site)
          if not v:
              continue
          row = {"run_id": run_id, "route": b["route"], "sample": b["sample"], "venue": site,
                 "bridg_requestStart": b.get("requestStart"), "bridg_quoteVisible": b.get("quoteVisible"),
                 "venue_requestStart": v.get("requestStart"), "venue_quoteVisible": v.get("quoteVisible"),
                 "gap_s": v.get("gap_vs_bridg_s"), "venue_status": v.get("status")}
          lv = listed.get(vid)
          row["bridg_listed"] = lv["out"] if lv else None
          row["bridg_compare_only"] = lv["compare_only"] if lv else None
          row["bridg_fee_observed"] = bridg_fees.get(vid, dict(bq.get("detail_fees") or []).get("Bridg fee"))
          q = v.get("quote") or {}
          row["direct_out"] = q.get("out")
          row["direct_note"] = ""
          fee_top, fee_tok = q.get("fixed_fee_on_top"), q.get("fixed_fee_token")
          if fee_top:
              row["direct_fixed_fee"] = fee_top
              if fee_tok == "USDC":
                  row["direct_out_fee_adj"] = round(q["out"] - fee_top, 6)
                  row["direct_note"] = f"+{fee_top} USDC charged on top of 100 input (subtracted)"
              else:
                  row["direct_note"] = f"+{fee_top} {fee_tok} charged on top of 100 input (not converted)"
          if site == "lifi":
              row["direct_note"] = f"Jumper Best Return via {q.get('best_return_venue')}; max route {q.get('max_out')}"
          if site == "mayan":
              row["direct_note"] = f"{q.get('mode')}; UI shows {q.get('display_decimals')} dp"
          if site == "cctp":
              row["direct_note"] = f"via Portal ({q.get('route_type') or q.get('route') or 'CCTP'}); executor fee hidden until wallet connect"
          if site == "simpleswap":
              row["direct_note"] = f"selected card: {q.get('selected_card')}; best card {q.get('best_card_out')}"
          cmp_direct = row.get("direct_out_fee_adj") or row["direct_out"]
          # a direct quote above the input by >2% is a display anomaly on that site: log it, don't average it
          if cmp_direct is not None and cmp_direct > 102:
              row["direct_note"] += f" | ANOMALY: site displayed {cmp_direct} out for 100 in (excluded)"
              cmp_direct = None
          row["direct_cmp"] = cmp_direct
          if row["bridg_listed"] is not None and cmp_direct is not None:
              row["gap_bps"] = round((row["bridg_listed"] - cmp_direct) / 100 * 1e4, 2)
              fee = row["bridg_fee_observed"]
              row["gap_ex_bridg_fee_bps"] = round(row["gap_bps"] + fee / 100 * 1e4, 2) if fee is not None else None
          rows.append(row)
  return rows


cols = ["route", "sample", "venue", "bridg_listed", "bridg_compare_only", "direct_out", "direct_fixed_fee",
        "direct_out_fee_adj", "direct_cmp", "gap_bps", "bridg_fee_observed", "gap_ex_bridg_fee_bps", "gap_s",
        "venue_status", "direct_note", "bridg_requestStart", "bridg_quoteVisible", "venue_requestStart",
        "venue_quoteVisible", "run_id"]


def write_csv(rows, path="data/normalized.csv"):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def verdict(venue, gaps, listed_n, n, raw=None):
    if listed_n == 0:
        return "NOT LISTED on Bridg"
    if not gaps:
        return "No direct quote"
    m = statistics.mean(gaps)
    tol = 4 if venue == "mayan" else 2  # Mayan: Dutch-auction drift + 2-4 dp display rounding
    if abs(m) <= tol:
        return "Match (net of Bridg fee)"
    if raw and abs(statistics.mean(raw)) <= tol:
        return "Match (Bridg fee not applied)"
    return "Bridg LOWER than venue" if m < 0 else "Bridg HIGHER than venue"


def summarize(rows):
    summ = defaultdict(list)
    for r in rows:
        summ[(r["route"], r["venue"])].append(r)
    out = []
    for (route, venue), rs in summ.items():
        gaps = [r["gap_ex_bridg_fee_bps"] for r in rs if r.get("gap_ex_bridg_fee_bps") is not None]
        raw = [r["gap_bps"] for r in rs if r.get("gap_bps") is not None]
        bl = [r["bridg_listed"] for r in rs if r["bridg_listed"] is not None]
        dl = [r["direct_cmp"] for r in rs if r["direct_cmp"] is not None]
        mean = lambda xs: round(statistics.mean(xs), 6) if xs else None
        out.append({"route": route, "venue": venue, "n": len(rs), "n_listed": len(bl), "n_direct": len(dl),
                    "bridg_avg": mean(bl), "direct_avg": mean(dl),
                    "gap_ex_fee_bps": round(statistics.mean(gaps), 1) if gaps else None,
                    "gap_raw_bps": round(statistics.mean(raw), 1) if raw else None,
                    "gap_min": min(gaps) if gaps else None, "gap_max": max(gaps) if gaps else None,
                    "compare_only": any(r["bridg_compare_only"] for r in rs),
                    "verdict": verdict(venue, gaps, len(bl), len(rs), raw)})
    return out


if __name__ == "__main__":
    rows = build_rows(load_runs(sys.argv[1] if len(sys.argv) > 1 else "data/raw_quotes.jsonl"))
    write_csv(rows)
    print(f"{'route':10} {'venue':9} {'n':>2} {'listed':>6} {'bridg avg':>10} {'direct avg':>10} {'ex-fee bps':>10} {'range':>13}  verdict")
    for s in summarize(rows):
        f = lambda x: f"{x:.6f}" if x is not None else "—"
        rng = f"{s['gap_min']:+.1f}..{s['gap_max']:+.1f}" if s["gap_min"] is not None else "—"
        g = f"{s['gap_ex_fee_bps']:+.1f}" if s["gap_ex_fee_bps"] is not None else "—"
        print(f"{s['route']:10} {s['venue']:9} {s['n']:>2} {s['n_listed']:>6} {f(s['bridg_avg']):>10} "
              f"{f(s['direct_avg']):>10} {g:>10} {rng:>13}  {s['verdict']}")


def build_competitor_rows(runs):
    """Bridg's best executable output vs what each other site (venue or platform) shows directly.
    savings_bps = (Bridg best − other) / 100 × 10,000; positive = user gets more on Bridg."""
    out = []
    for run_id, recs in runs.items():
        by = {r["site"]: r for r in recs}
        b = by.get("bridg")
        if not b or b.get("status") != "OK" or not b["quote"].get("best_out"):
            continue
        best = b["quote"]["best_out"]
        for site, r in by.items():
            if site == "bridg" or r.get("status") != "OK":
                continue
            q = r["quote"] or {}
            other = q.get("out")
            if q.get("fixed_fee_on_top") and q.get("fixed_fee_token") == "USDC":
                other = other - q["fixed_fee_on_top"]
            if other is None or other > 102:  # display anomaly, logged elsewhere
                continue
            out.append({"route": b["route"], "sample": b["sample"], "site": site, "run_id": run_id,
                        "kind": getattr(ADAPTERS.get(site), "kind", "venue"),
                        "bridg_best": best, "bridg_best_route": b["quote"].get("detail_route"),
                        "other_out": round(other, 6),
                        "savings_bps": round((best - other) / 100 * 1e4, 2),
                        "fee_on_top_not_converted": bool(q.get("fixed_fee_on_top") and q.get("fixed_fee_token") != "USDC")})
    return out


def summarize_competitors(crows):
    g = defaultdict(list)
    for r in crows:
        g[(r["route"], r["site"])].append(r)
    res = []
    for (route, site), rs in g.items():
        s = [r["savings_bps"] for r in rs]
        res.append({"route": route, "site": site, "kind": rs[0]["kind"], "n": len(rs),
                    "bridg_best_avg": round(statistics.mean(r["bridg_best"] for r in rs), 6),
                    "other_avg": round(statistics.mean(r["other_out"] for r in rs), 6),
                    "savings_bps": round(statistics.mean(s), 1), "min": min(s), "max": max(s),
                    "fee_on_top_not_converted": any(r["fee_on_top_not_converted"] for r in rs)})
    return res
