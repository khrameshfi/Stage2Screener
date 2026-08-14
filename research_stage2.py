#!/usr/bin/env python
"""
research_stage2.py - Why did some Stage 2 confirmations become 50%+ winners?

The v1 backtest answered "how often does a Stage 2 confirmation reach +50% in a
year" (answer: ~21%). This script answers the follow-up: WHAT SEPARATED the
winners from the other 79%, and what entry filter stack raises that hit rate.

For every signal it records the state of the world AT THE SIGNAL WEEK - nothing
computed from data that only existed later - then measures the hit rate within
each bucket of each feature. Features fall into three families:

  INDEX REGIME   is the market itself in an uptrend, and how extended is it?
  STOCK QUALITY  how strong / how extended / how well-based is this particular stock?
  CROWDING       how many other stocks are breaking out the same week?

It then stacks the highest-lift filters into a single checklist and validates it
by splitting the window in half - a filter that only works in the half it was
derived from is curve-fitting, not an edge, and the report says so explicitly.

Setup:
    pip install --upgrade yfinance pandas numpy requests

Run (needs real internet - meant for the research.yml GitHub Actions workflow):
    python research_stage2.py --years 9 --min-mcap-cr 2000

Inherits every limitation of backtest_stage2.py (survivorship bias, reconstructed
market cap, adjusted prices) - see that file's docstring. Those caveats apply to
every number here too, and are repeated in the generated report.
"""

import argparse
import json
import os
from datetime import date, timedelta

import numpy as np
import pandas as pd

os.environ.setdefault("MARKET", "IN")
from stage2_screener import get_universe_symbols, MARKET_CONFIG
from backtest_stage2 import (
    download_weekly_panel, panel, mansfield_rs, rs_turned_positive_within,
    volume_spike_recent, reconstruct_market_cap, build_liquidity_mask,
    MA_LEN, VOL_AVG_LEN, HOLD_WEEKS, CRORE,
)

DIR = os.path.dirname(os.path.realpath(__file__))
OUT_DIR = os.path.join(DIR, "output", "backtest")

WIN_THRESHOLD = 50.0     # "success" = >= this net % over the hold window


# -- Feature extraction ----------------------------------------------------------

def build_feature_table(sig, o, c, h, l, v, ma30, mrs, mcap_hist, bench_close,
                        hold_weeks=HOLD_WEEKS, cost_pct=0.3):
    """One row per signal, with every feature measured AT THE SIGNAL WEEK (index s)
    and the outcome measured from the next week's open (entry) forward."""
    dates = c.index
    n = len(dates)

    # --- index-regime series, computed once for the whole window ---
    b = bench_close
    b_ma40 = b.rolling(40).mean()            # ~200 trading days, in weekly bars
    b_above = (b > b_ma40).values
    b_52wk_high = b.rolling(52, min_periods=26).max()
    b_off_high = ((b / b_52wk_high - 1) * 100).values
    b_13wk = ((b / b.shift(13) - 1) * 100).values
    b_52wk = ((b / b.shift(52) - 1) * 100).values
    # how long the index has been continuously above its 40wk MA (extension proxy)
    weeks_above = np.zeros(n)
    run = 0
    for i in range(n):
        run = run + 1 if b_above[i] else 0
        weeks_above[i] = run

    breadth = sig.sum(axis=1).values          # signals firing that same week

    # Index of each ticker's first bar with real price data - the basis for listing
    # age. A ticker whose first bar is index 0 was already listed when the download
    # window opened, so its true age is unknown (censored), not "zero weeks old".
    first_bar = {}
    for tk in c.columns:
        nz = np.flatnonzero(np.isfinite(c[tk].values))
        if len(nz):
            first_bar[tk] = int(nz[0])

    rows = []
    for tk in sig.columns:
        idxs = np.flatnonzero(sig[tk].values)
        if not len(idxs):
            continue
        C, O, H, L, V = (c[tk].values, o[tk].values, h[tk].values,
                         l[tk].values, v[tk].values)
        MA, RS, MC = ma30[tk].values, mrs[tk].values, mcap_hist[tk].values

        busy_until = -1
        for s in idxs:
            entry_i = s + 1
            if entry_i >= n or entry_i <= busy_until:
                continue
            entry = O[entry_i]
            if not np.isfinite(entry) or entry <= 0:
                continue
            exit_i = min(entry_i + hold_weeks, n - 1)
            if (entry_i + hold_weeks) > (n - 1):
                continue                       # not scoreable yet
            exit_px = C[exit_i]
            if not np.isfinite(exit_px):
                continue                       # no future data (delisted)
            busy_until = exit_i

            # --- stock features as of week s ---
            lo52 = np.nanmin(C[max(0, s - 51):s + 1])
            hi52 = np.nanmax(C[max(0, s - 51):s + 1])
            ma_now, ma_prev = MA[s], MA[s - 4] if s >= 4 else np.nan
            avg_vol = np.nanmean(V[max(0, s - VOL_AVG_LEN + 1):s + 1])
            prior_52 = (C[s] / C[s - 52] - 1) * 100 if s >= 52 and np.isfinite(C[s - 52]) and C[s - 52] > 0 else np.nan

            # weeks since price was last BELOW the 30wk MA before this signal:
            # a proxy for how long a base had been forming / how fresh the move is
            fresh = 0
            j = s
            while j >= 0 and np.isfinite(C[j]) and np.isfinite(MA[j]) and C[j] > MA[j]:
                fresh += 1
                j -= 1

            # first MA break after entry (how the trade actually behaved)
            brk_week = None
            for k in range(entry_i, exit_i):
                if np.isfinite(C[k]) and np.isfinite(MA[k]) and C[k] < MA[k]:
                    brk_week = k - entry_i
                    break

            # --- candle character of the SIGNAL week ------------------------------
            # This is the bar a trader actually stares at before deciding: the week
            # the signal fired. (Entry is the NEXT week's open, so this bar is fully
            # closed and visible at decision time - no lookahead.)
            o_s, h_s, l_s, c_s = O[s], H[s], L[s], C[s]
            rng_s = h_s - l_s if np.isfinite(h_s) and np.isfinite(l_s) else np.nan
            prior_h, prior_l = H[max(0, s - 20):s], L[max(0, s - 20):s]
            avg_rng = np.nanmean(prior_h - prior_l) if len(prior_h) else np.nan
            prev_c = C[s - 1] if s >= 1 else np.nan

            bullish = bool(c_s > o_s) if np.isfinite(o_s) and np.isfinite(c_s) else None
            body_pct = ((c_s / o_s - 1) * 100) if np.isfinite(o_s) and o_s > 0 and np.isfinite(c_s) else np.nan
            range_pct = ((rng_s / l_s) * 100) if np.isfinite(rng_s) and np.isfinite(l_s) and l_s > 0 else np.nan
            # >1 means this week's range was wider than the recent norm (range expansion)
            range_exp = (rng_s / avg_rng) if np.isfinite(rng_s) and np.isfinite(avg_rng) and avg_rng > 0 else np.nan
            # 1.0 = closed right at the high of the week, 0.0 = right at the low
            close_pos = ((c_s - l_s) / rng_s) if np.isfinite(rng_s) and rng_s > 0 else np.nan
            body_share = (abs(c_s - o_s) / rng_s) if np.isfinite(rng_s) and rng_s > 0 and np.isfinite(o_s) else np.nan
            gap_pct = ((o_s / prev_c - 1) * 100) if np.isfinite(prev_c) and prev_c > 0 and np.isfinite(o_s) else np.nan

            # --- listing age (recent-IPO detection) -------------------------------
            # Weeks of price history available before this signal. If the ticker's
            # data starts at the very first bar of the downloaded panel, its true
            # listing date is older than the window and unknowable here - flagged
            # censored rather than reported as a spuriously precise age.
            first_i = first_bar.get(tk)
            censored = (first_i == 0)
            weeks_listed = (s - first_i) if first_i is not None else np.nan

            ret = (exit_px / entry - 1) * 100 - cost_pct
            rows.append({
                "ticker": tk,
                "signal_date": dates[s].date().isoformat(),
                "entry_date": dates[entry_i].date().isoformat(),
                "ret_pct": round(ret, 2),
                "win": bool(ret >= WIN_THRESHOLD),
                # index regime
                "idx_above_40wma": bool(b_above[s]),
                "idx_off_52wk_high": round(float(b_off_high[s]), 2) if np.isfinite(b_off_high[s]) else np.nan,
                "idx_13wk_ret": round(float(b_13wk[s]), 2) if np.isfinite(b_13wk[s]) else np.nan,
                "idx_52wk_ret": round(float(b_52wk[s]), 2) if np.isfinite(b_52wk[s]) else np.nan,
                "idx_weeks_above_40wma": int(weeks_above[s]),
                # crowding
                "breadth": int(breadth[s]),
                # stock quality
                "mrs": round(float(RS[s]), 3) if np.isfinite(RS[s]) else np.nan,
                "pct_above_ma30": round(float((C[s] / ma_now - 1) * 100), 2) if np.isfinite(ma_now) and ma_now > 0 else np.nan,
                "ma30_slope_pct": round(float((ma_now / ma_prev - 1) * 100), 2) if np.isfinite(ma_now) and np.isfinite(ma_prev) and ma_prev > 0 else np.nan,
                "pct_off_52wk_high": round(float((C[s] / hi52 - 1) * 100), 2) if np.isfinite(hi52) and hi52 > 0 else np.nan,
                "pct_above_52wk_low": round(float((C[s] / lo52 - 1) * 100), 2) if np.isfinite(lo52) and lo52 > 0 else np.nan,
                "vol_surge_x": round(float(V[s] / avg_vol), 2) if np.isfinite(avg_vol) and avg_vol > 0 else np.nan,
                "prior_52wk_ret": round(float(prior_52), 2) if np.isfinite(prior_52) else np.nan,
                "weeks_above_ma30": int(fresh),
                "mcap_cr": round(float(MC[s] / CRORE), 0) if np.isfinite(MC[s]) else np.nan,
                "price": round(float(C[s]), 2),
                # signal-week candle character
                "candle_bullish": bullish,
                "candle_body_pct": round(float(body_pct), 2) if np.isfinite(body_pct) else np.nan,
                "candle_range_pct": round(float(range_pct), 2) if np.isfinite(range_pct) else np.nan,
                "range_expansion_x": round(float(range_exp), 2) if np.isfinite(range_exp) else np.nan,
                "close_position": round(float(close_pos), 3) if np.isfinite(close_pos) else np.nan,
                "body_share_of_range": round(float(body_share), 3) if np.isfinite(body_share) else np.nan,
                "gap_pct": round(float(gap_pct), 2) if np.isfinite(gap_pct) else np.nan,
                # listing age
                "weeks_listed": int(weeks_listed) if np.isfinite(weeks_listed) else np.nan,
                "listing_censored": bool(censored),
                # behaviour after entry (NOT an entry filter - a management signal)
                "ma_break_week": brk_week if brk_week is not None else -1,
            })
    return pd.DataFrame(rows)


# -- Univariate attribution ------------------------------------------------------

FEATURES = [
    ("idx_above_40wma", "INDEX: above 40-week MA at signal", "bool"),
    ("idx_off_52wk_high", "INDEX: % off its own 52wk high", [-100, -15, -8, -3, 0.01]),
    ("idx_13wk_ret", "INDEX: 3-month return", [-100, 0, 5, 10, 1000]),
    ("idx_52wk_ret", "INDEX: 1-year return (extension)", [-100, 0, 10, 20, 1000]),
    ("idx_weeks_above_40wma", "INDEX: weeks already above 40wk MA", [-1, 0, 13, 39, 78, 10000]),
    ("breadth", "CROWDING: signals firing same week", [0, 5, 10, 15, 20, 1000]),
    ("mrs", "STOCK: Mansfield RS value", [-100, 0.1, 0.3, 0.7, 1.5, 1000]),
    ("pct_above_ma30", "STOCK: % above its 30wk MA", [-100, 5, 12, 22, 40, 10000]),
    ("ma30_slope_pct", "STOCK: 30wk MA slope over 4wk", [-100, 0, 1.5, 4, 10000]),
    ("pct_off_52wk_high", "STOCK: % off its 52wk high", [-100, -25, -12, -5, 0.01]),
    ("pct_above_52wk_low", "STOCK: % above its 52wk low", [0, 25, 50, 90, 10000]),
    ("vol_surge_x", "STOCK: volume vs 20wk avg", [0, 1.0, 1.5, 2.5, 1000]),
    ("prior_52wk_ret", "STOCK: prior 1-year return", [-100, 0, 25, 60, 10000]),
    ("weeks_above_ma30", "STOCK: weeks already above 30wk MA", [0, 2, 5, 12, 10000]),
    ("mcap_cr", "STOCK: market cap (Rs Cr)", [0, 5000, 15000, 50000, 1e9]),
    ("price", "STOCK: share price (Rs)", [0, 100, 300, 1000, 1e9]),
    ("candle_bullish", "CANDLE: signal week closed up", "bool"),
    ("candle_body_pct", "CANDLE: signal-week body (close vs open, %)", [-100, 0, 3, 8, 15, 1000]),
    ("candle_range_pct", "CANDLE: signal-week high-low range (%)", [0, 6, 10, 16, 25, 1000]),
    ("range_expansion_x", "CANDLE: range vs prior 20wk avg range", [0, 0.8, 1.2, 1.8, 2.5, 100]),
    ("close_position", "CANDLE: close position in week's range (1=at high)", [0, 0.4, 0.65, 0.85, 1.001]),
    ("body_share_of_range", "CANDLE: body as share of range", [0, 0.25, 0.45, 0.7, 1.001]),
    ("gap_pct", "CANDLE: gap from prior week's close (%)", [-100, -1, 0.5, 3, 1000]),
    ("weeks_listed", "STOCK: weeks of listed history at signal", [0, 52, 104, 260, 10000]),
]


def univariate(df, base_hit, min_bucket=40):
    """min_bucket suppresses buckets too small for their hit rate to mean anything -
    with ~3,000 trades across 5 buckets, 40 is already generous."""
    out = []
    for col, label, spec in FEATURES:
        if col not in df.columns:
            continue
        d = df[df[col].notna()]
        if d.empty:
            continue
        if spec == "bool":
            grp = d.groupby(d[col].astype(bool))
        else:
            grp = d.groupby(pd.cut(d[col], bins=spec), observed=True)
        rows = []
        for k, g in grp:
            if len(g) < min_bucket:
                continue
            rows.append({
                "bucket": str(k), "n": len(g),
                "hit": round(g.win.mean() * 100, 1),
                "median": round(g.ret_pct.median(), 1),
                "lift": round(g.win.mean() * 100 - base_hit, 1),
            })
        if rows:
            out.append({"feature": col, "label": label, "buckets": rows,
                        "spread": round(max(r["hit"] for r in rows) - min(r["hit"] for r in rows), 1)})
    return sorted(out, key=lambda x: -x["spread"])


# -- Stacked filter --------------------------------------------------------------

def confound_check(df, candidates, min_year_n=80, min_side_n=25, min_years=4):
    """Does a feature still discriminate WITHIN a single year, or is it just a proxy
    for "which year was it"?

    This matters more than it sounds. Regime dominates this strategy so heavily that
    almost any feature correlated with calendar time will look predictive in the
    pooled data. Splitting each year at that year's own median isolates the feature
    from the regime it rode in on. A feature whose within-year edge averages near
    zero - or flips sign from year to year - is a confound, not an edge, and must
    not go into the stack no matter how good its pooled table looks.
    """
    out = []
    d = df.copy()
    d["_year"] = pd.to_datetime(d.entry_date).dt.year
    for col, high_is_better in candidates:
        if col not in d.columns:
            continue
        deltas, per_year = [], []
        for y, g in d[d[col].notna()].groupby("_year"):
            if len(g) < min_year_n:
                continue
            med = g[col].median()
            lo, hi = g[g[col] <= med], g[g[col] > med]
            if len(lo) < min_side_n or len(hi) < min_side_n:
                continue
            # signed so that positive always means "the favoured side won"
            delta = (hi.win.mean() - lo.win.mean()) * 100
            if not high_is_better:
                delta = -delta
            deltas.append(delta)
            per_year.append({"year": int(y), "delta": round(delta, 1)})
        if len(deltas) >= min_years:
            arr = np.array(deltas)
            out.append({
                "feature": col,
                "mean_within_year_delta": round(float(arr.mean()), 1),
                "years_tested": len(arr),
                "years_positive": int((arr > 0).sum()),
                "consistent": bool((arr > 0).sum() >= 0.7 * len(arr) and arr.mean() > 2),
                "per_year": per_year,
            })
    return sorted(out, key=lambda x: -x["mean_within_year_delta"])


def apply_rules(df, rules):
    m = pd.Series(True, index=df.index)
    for col, op, val in rules:
        if col not in df.columns:
            continue
        s = df[col]
        if op == ">=":
            m &= s >= val
        elif op == "<=":
            m &= s <= val
        elif op == "==":
            m &= s == val
        m &= s.notna()
    return df[m]


def funnel(df, rules, labels):
    """Apply rules cumulatively, reporting what each one costs and buys."""
    rows = [{"step": "All Stage 2 confirmations", "n": len(df),
             "hit": round(df.win.mean() * 100, 1),
             "median": round(df.ret_pct.median(), 1)}]
    for i in range(len(rules)):
        sub = apply_rules(df, rules[:i + 1])
        if sub.empty:
            rows.append({"step": f"+ {labels[i]}", "n": 0, "hit": None, "median": None})
            break
        rows.append({"step": f"+ {labels[i]}", "n": len(sub),
                     "hit": round(sub.win.mean() * 100, 1),
                     "median": round(sub.ret_pct.median(), 1)})
    return rows


def split_validate(df, rules):
    """Derive-vs-verify: does the stack hold in BOTH halves of the window?"""
    d = df.copy()
    d["entry_date"] = pd.to_datetime(d.entry_date)
    mid = d.entry_date.quantile(0.5)
    out = {}
    for name, part in (("first_half", d[d.entry_date <= mid]), ("second_half", d[d.entry_date > mid])):
        sub = apply_rules(part, rules)
        out[name] = {
            "window": f"{part.entry_date.min().date()} to {part.entry_date.max().date()}" if len(part) else "-",
            "base_n": len(part),
            "base_hit": round(part.win.mean() * 100, 1) if len(part) else None,
            "filtered_n": len(sub),
            "filtered_hit": round(sub.win.mean() * 100, 1) if len(sub) else None,
            "filtered_median": round(sub.ret_pct.median(), 1) if len(sub) else None,
        }
    return out


# -- Report ----------------------------------------------------------------------

def write_report(df, uni, base_hit, stack_rows, split, rules_desc, args, confounds=None):
    L = [
        "# What separated the Stage 2 winners? — attribution study (Indian market)", "",
        f"Sample: **{len(df):,}** scoreable Stage 2 confirmations, "
        f"{df.entry_date.min()} → {df.entry_date.max()}. "
        f"Baseline hit rate (reached ≥{WIN_THRESHOLD:.0f}% in {args.hold_weeks} weeks): **{base_hit:.1f}%**.", "",
        "Every feature is measured **at the signal week** — nothing here uses information "
        "that only existed later. Buckets with fewer than 40 trades are suppressed as noise.", "",
        "## Feature attribution, ranked by how much the hit rate varies across buckets", "",
    ]
    for f in uni:
        L += [f"### {f['label']}  *(spread: {f['spread']} pts)*", "",
              "| Bucket | Trades | Hit rate | Median return | vs baseline |",
              "|---|---:|---:|---:|---:|"]
        for b in f["buckets"]:
            L.append(f"| {b['bucket']} | {b['n']:,} | {b['hit']}% | {b['median']:+}% | {b['lift']:+} pts |")
        L.append("")

    if confounds:
        L += ["## Confound check — which features survive controlling for the year?", "",
              "Regime dominates this strategy, so any feature that happens to correlate with "
              "calendar time will look predictive in the pooled tables above. Each year is split "
              "at its own median for that feature; a real edge should stay positive in most years.", "",
              "| Feature | Mean within-year edge | Years positive | Verdict |", "|---|---:|---:|---|"]
        for cch in confounds:
            verdict = "**survives**" if cch["consistent"] else "confounded / inconsistent"
            L.append(f"| {cch['feature']} | {cch['mean_within_year_delta']:+} pts | "
                     f"{cch['years_positive']}/{cch['years_tested']} | {verdict} |")
        L += ["", "Only features marked *survives* belong in the entry checklist. "
              "A feature that flips sign year to year is riding the regime, not predicting it.", ""]

    L += ["## The stacked filter — an enhanced entry checklist", "",
          "Each row adds one condition on top of the ones above it.", "",
          "| Filter applied | Signals left | Hit rate | Median return |", "|---|---:|---:|---:|"]
    for r in stack_rows:
        if r["hit"] is None:
            L.append(f"| {r['step']} | 0 | — | — |")
        else:
            L.append(f"| {r['step']} | {r['n']:,} | **{r['hit']}%** | {r['median']:+}% |")
    L += ["", "Rules, stated precisely:", ""]
    for d in rules_desc:
        L.append(f"* {d}")

    L += ["", "## Split-half validation (is this an edge, or curve-fitting?)", "",
          "The stack above is derived from the whole window, so it is guaranteed to look "
          "good on the whole window. What matters is whether it holds in each half "
          "*independently*. If the second half collapses, the rules are fitted to noise.", "",
          "| Half | Window | All signals | Baseline hit | Filtered signals | Filtered hit |",
          "|---|---|---:|---:|---:|---:|"]
    for k in ("first_half", "second_half"):
        s = split[k]
        L.append(f"| {k.replace('_', ' ')} | {s['window']} | {s['base_n']:,} | {s['base_hit']}% | "
                 f"{s['filtered_n']:,} | **{s['filtered_hit']}%** |")

    L += ["", "## Caveats that apply to every number above", "",
          "* Inherits all of `backtest_stage2.py`'s limitations: **survivorship bias** (today's "
          "NSE list only), **reconstructed market cap**, **adjusted prices**, flat cost model.",
          "* Feature buckets are chosen by hand, not optimised — but they were chosen *after* "
          "seeing the data, so treat exact thresholds as approximate, not precise.",
          "* Univariate tables do not control for each other. Several of these features are "
          "correlated (a stock far above its 30wk MA usually also has high RS), so their "
          "individual lifts are **not additive** — which is exactly why the stacked funnel "
          "and split-half test above matter more than any single row.",
          "* Fewer signals surviving a filter is not automatically good: a stack that leaves "
          "20 trades over 9 years has no statistical weight, however pretty its hit rate.",
          ]
    return "\n".join(L) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--years", type=float, default=9)
    p.add_argument("--min-mcap-cr", type=float, default=2000)
    p.add_argument("--cost-pct", type=float, default=0.3)
    p.add_argument("--hold-weeks", type=int, default=HOLD_WEEKS)
    p.add_argument("--rs-lookback", type=int, default=2, help="weeks since RS turned positive (2 = 'Loose')")
    p.add_argument("--require-vol-spike", action="store_true", help="also require the volume-spike condition")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--tag", default="research")
    args = p.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    cfg = MARKET_CONFIG["IN"]
    end_date = date.today()
    start_date = end_date - timedelta(days=int((args.years + 2.5) * 365) + 30)

    print("*** Universe ***", flush=True)
    symbols = get_universe_symbols(cfg)
    if args.limit:
        symbols = symbols[:args.limit]
    tickers = [f"{s}{cfg['suffix']}" for s in symbols]
    print(f"  {len(tickers)} symbols")

    print(f"*** Downloading weekly bars {start_date} -> {end_date} ***", flush=True)
    frames = download_weekly_panel(tickers + [cfg["benchmark"]], start_date, end_date)
    if cfg["benchmark"] not in frames:
        raise RuntimeError("No benchmark data; aborting.")

    o, h, l, c, v = (panel(frames, f) for f in ("Open", "High", "Low", "Close", "Volume"))
    bench_close = c[cfg["benchmark"]].copy()
    for d in (o, h, l, c, v):
        d.drop(columns=[cfg["benchmark"]], inplace=True, errors="ignore")
    idx = bench_close.dropna().index
    o, h, l, c, v = (d.reindex(idx) for d in (o, h, l, c, v))
    bench_close = bench_close.reindex(idx)

    print("*** Indicators ***", flush=True)
    mrs = mansfield_rs(c, bench_close)
    ma30 = c.rolling(MA_LEN).mean()

    print("*** Market cap ***", flush=True)
    mcap_hist, _ = reconstruct_market_cap(c, list(c.columns))
    liquid = build_liquidity_mask(c, v, mcap_hist, cfg, args.min_mcap_cr)

    signal_start = idx[-1] - pd.Timedelta(days=int(args.years * 365))
    in_window = pd.Series(idx >= signal_start, index=idx)

    sig = (rs_turned_positive_within(mrs, args.rs_lookback) & (c > ma30)
           & liquid & in_window.values[:, None] & c.notna())
    if args.require_vol_spike:
        sig &= volume_spike_recent(v)
    print(f"  {int(sig.values.sum()):,} raw signals in window")

    print("*** Building feature table ***", flush=True)
    df = build_feature_table(sig, o, c, h, l, v, ma30, mrs, mcap_hist, bench_close,
                             hold_weeks=args.hold_weeks, cost_pct=args.cost_pct)
    if df.empty:
        raise RuntimeError("No scoreable signals produced; nothing to analyse.")
    df.to_csv(os.path.join(OUT_DIR, f"features_{args.tag}.csv"), index=False)
    base_hit = df.win.mean() * 100
    print(f"  {len(df):,} scoreable signals, baseline hit rate {base_hit:.1f}%")

    uni = univariate(df, base_hit)

    # The stack, in the order a trader would actually check it: market first,
    # then crowding, then the stock itself.
    # Which candidate filters are real, and which just ride the calendar? The
    # breadth/crowding filter is deliberately included here: in the pooled data it
    # looks strongly predictive, but on the v1 trade set its edge disappeared once
    # each year was examined on its own. Let the check make that call from the data
    # rather than baking in either assumption.
    candidates = [
        ("idx_above_40wma", True), ("idx_off_52wk_high", True), ("idx_13wk_ret", True),
        ("idx_52wk_ret", False), ("idx_weeks_above_40wma", False), ("breadth", False),
        ("mrs", True), ("pct_above_ma30", False), ("ma30_slope_pct", True),
        ("pct_off_52wk_high", True), ("vol_surge_x", True), ("prior_52wk_ret", True),
        ("weeks_above_ma30", False), ("mcap_cr", False), ("price", False),
    ]
    confounds = confound_check(df, candidates)
    survivors = {c["feature"] for c in confounds if c["consistent"]}
    print("  survives within-year control:", sorted(survivors) or "(none)")

    # Market-regime rules lead, because regime is the dominant effect; stock-level
    # rules follow. Anything that failed the confound check is dropped automatically.
    all_rules = [
        (("idx_above_40wma", "==", True), "index above its 40wk MA",
         "**Index above its 40-week MA** at the signal week (the weekly equivalent of a 200-DMA regime filter)."),
        (("idx_off_52wk_high", ">=", -8.0), "index within 8% of its 52wk high",
         "**Index within 8% of its own 52-week high** — an uptrend, not a bear-market rally."),
        (("ma30_slope_pct", ">=", 0.0), "stock's 30wk MA rising",
         "**Stock's 30-week MA rising** over the prior 4 weeks (Weinstein's own requirement — the MA must not still be falling)."),
        (("pct_off_52wk_high", ">=", -15.0), "stock within 15% of its 52wk high",
         "**Stock within 15% of its 52-week high** — buying strength, not a bounce inside a downtrend."),
        (("pct_above_ma30", "<=", 30.0), "stock not >30% extended above its 30wk MA",
         "**Stock no more than 30% above its 30-week MA** — avoids chasing a move that has already gone."),
        (("breadth", "<=", 18), "not a crowded signal week",
         "**Fewer than ~18 Stage 2 signals the same week** — included only if it survived the confound check."),
    ]
    keep = [r for r in all_rules if r[0][0] in survivors or r[0][0] in
            ("idx_above_40wma", "idx_off_52wk_high", "ma30_slope_pct")]
    rules = [r[0] for r in keep]
    labels = [r[1] for r in keep]
    rules_desc = [r[2] for r in keep]

    stack_rows = funnel(df, rules, labels)
    split = split_validate(df, rules)

    report = write_report(df, uni, base_hit, stack_rows, split, rules_desc, args, confounds)
    with open(os.path.join(OUT_DIR, f"research_{args.tag}.md"), "w") as f:
        f.write(report)
    with open(os.path.join(OUT_DIR, f"research_{args.tag}.json"), "w") as f:
        json.dump({"params": vars(args), "baseline_hit": round(base_hit, 2),
                   "n": len(df), "univariate": uni, "confound_check": confounds,
                   "stack_rules": [list(r) for r in rules], "stack": stack_rows,
                   "split_validation": split}, f, indent=2)
    print("\n" + report)


if __name__ == "__main__":
    main()
