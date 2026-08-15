#!/usr/bin/env python
"""
exit_study.py - How should a Stage 2 trade be exited?

The earlier work fixed the hold at 52 weeks, which is arbitrary: it caps the big
winners and forces you to sit through dead trades. This tests letting the trade
run until the trend actually breaks, and compares several ways of defining that
break.

Exit variants tested on the SAME set of entries:
  fixed_52w     hold exactly 52 weeks (the old baseline, for comparison)
  ma_break      first weekly close below the 30-week MA -> exit next open, NO time cap
  ma_2closes    same, but requires TWO consecutive closes below (whipsaw filter)
  ma_buffer3    same, but the close must be 3% below the MA (noise filter)
  ma_grace8     same as ma_break, but the rule is only armed from week 8 onward,
                giving a young breakout room to shake out
  ma_hardstop   ma_break, plus a hard -20% stop from entry, whichever comes first

Why per-trade % return alone is not enough
------------------------------------------
If one rule returns +40% in 20 weeks and another +50% in 80 weeks, the first is
far better - it freed the capital to work again. So this reports three things:

  mean/median return      the raw per-trade result
  weeks held              how long the money was tied up
  return on deployed      total P&L divided by total capital-time actually used,
    capital (annualised)  expressed per year. THIS is the number to compare rules on.

Trades still open when the data ends are reported separately and excluded from
the completed-trade statistics, rather than being silently closed at the last
price (which would flatter any rule that holds for a long time).

Run (needs internet - meant for the exit_study.yml workflow):
    python exit_study.py --years 9 --min-mcap-cr 2000

Inherits every limitation of backtest_stage2.py - survivorship bias, reconstructed
market cap, adjusted prices, flat cost model. See that file's docstring.
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
    MA_LEN, CRORE,
)

DIR = os.path.dirname(os.path.realpath(__file__))
OUT_DIR = os.path.join(DIR, "output", "backtest")

VARIANTS = ["fixed_52w", "ma_break", "ma_2closes", "ma_buffer3", "ma_grace8", "ma_hardstop"]
WIN_THRESHOLD = 50.0
HARD_STOP_PCT = -20.0
BUFFER_PCT = 0.03
GRACE_WEEKS = 8
MAX_HOLD_CAP = 520          # 10 years - a backstop so a permanently-trending name terminates


def find_exit(variant, C, MA, O, entry_i, n):
    """Returns (exit_index, exit_price, reason). exit_index is the bar the position
    is closed on. Every MA rule exits at the OPEN of the week AFTER the triggering
    close, since that close is only known once the week has finished."""
    if variant == "fixed_52w":
        j = min(entry_i + 52, n - 1)
        return j, C[j], ("closed_52w" if entry_i + 52 <= n - 1 else "data_end")

    entry_px = O[entry_i]
    hard_stop_level = entry_px * (1 + HARD_STOP_PCT / 100.0)
    below_run = 0
    limit = min(entry_i + MAX_HOLD_CAP, n - 1)

    for j in range(entry_i, limit):
        c, ma = C[j], MA[j]
        if not np.isfinite(c):
            continue

        if variant == "ma_hardstop" and c <= hard_stop_level:
            k = min(j + 1, n - 1)
            if np.isfinite(O[k]):
                return k, O[k], "hard_stop"

        if not np.isfinite(ma):
            continue

        if variant == "ma_buffer3":
            triggered = c < ma * (1 - BUFFER_PCT)
        else:
            triggered = c < ma

        if variant == "ma_grace8" and (j - entry_i) < GRACE_WEEKS:
            triggered = False

        if variant == "ma_2closes":
            below_run = below_run + 1 if c < ma else 0
            triggered = below_run >= 2

        if triggered:
            k = min(j + 1, n - 1)
            if np.isfinite(O[k]):
                return k, O[k], "ma_break" if variant != "ma_hardstop" else "ma_break"

    # never triggered inside the data we have
    return limit, C[limit], "still_open"


def simulate(sig, o, c, ma30, cost_pct=0.3):
    dates = c.index
    n = len(dates)
    rows = []

    for tk in sig.columns:
        idxs = np.flatnonzero(sig[tk].values)
        if not len(idxs):
            continue
        C, O, MA = c[tk].values, o[tk].values, ma30[tk].values

        # One "busy" tracker per variant: a stock can't be re-entered while that
        # variant still holds it, and different variants exit at different times.
        busy = {v: -1 for v in VARIANTS}

        for s in idxs:
            entry_i = s + 1
            if entry_i >= n:
                continue
            entry = O[entry_i]
            if not np.isfinite(entry) or entry <= 0:
                continue

            for v in VARIANTS:
                if entry_i <= busy[v]:
                    continue
                ex_i, ex_px, reason = find_exit(v, C, MA, O, entry_i, n)
                if not np.isfinite(ex_px) or ex_px <= 0:
                    continue
                busy[v] = ex_i
                weeks = int(ex_i - entry_i)
                ret = (ex_px / entry - 1) * 100 - cost_pct
                rows.append({
                    "variant": v,
                    "ticker": tk,
                    "entry_date": dates[entry_i].date().isoformat(),
                    "exit_date": dates[ex_i].date().isoformat(),
                    "weeks_held": weeks,
                    "ret_pct": round(ret, 2),
                    "reason": reason,
                    "completed": reason != "still_open" and reason != "data_end",
                })
    return pd.DataFrame(rows)


def stats(df, capital=10000.0):
    """Completed trades only. Annualised figures use capital-time, not a naive
    average of per-trade CAGRs (which explodes on short trades)."""
    comp = df[df.completed & (df.weeks_held > 0)]
    if comp.empty:
        return {"trades": 0}

    pnl = comp.ret_pct / 100.0 * capital
    capital_years = (comp.weeks_held / 52.0).sum()
    ann_on_deployed = (pnl.sum() / (capital_years * capital) * 100) if capital_years > 0 else np.nan

    # per-trade annualised, reported as a MEDIAN because the mean is meaningless
    # once a 3-week +40% trade annualises into the thousands
    per_trade_cagr = ((1 + comp.ret_pct / 100.0).clip(lower=0.01) ** (52.0 / comp.weeks_held) - 1) * 100

    return {
        "trades": int(len(comp)),
        "still_open_or_truncated": int((~df.completed).sum()),
        "mean_ret_pct": round(float(comp.ret_pct.mean()), 1),
        "median_ret_pct": round(float(comp.ret_pct.median()), 1),
        "hit_rate_50pct": round(float((comp.ret_pct >= WIN_THRESHOLD).mean() * 100), 1),
        "monster_rate_100pct": round(float((comp.ret_pct >= 100).mean() * 100), 1),
        "win_rate_positive": round(float((comp.ret_pct > 0).mean() * 100), 1),
        "mean_weeks": round(float(comp.weeks_held.mean()), 1),
        "median_weeks": round(float(comp.weeks_held.median()), 1),
        "pct_held_over_52w": round(float((comp.weeks_held > 52).mean() * 100), 1),
        "median_per_trade_cagr": round(float(per_trade_cagr.median()), 1),
        "annual_return_on_deployed_capital": round(float(ann_on_deployed), 1),
        "total_pnl_rs": round(float(pnl.sum()), 0),
        "capital_years_used": round(float(capital_years), 1),
        "worst_ret": round(float(comp.ret_pct.min()), 1),
        "best_ret": round(float(comp.ret_pct.max()), 1),
        "pct_exit_ma": round(float((comp.reason == "ma_break").mean() * 100), 1),
        "pct_exit_hardstop": round(float((comp.reason == "hard_stop").mean() * 100), 1),
    }


def write_report(all_stats, filt_stats, args):
    def block(title, st, note):
        L = [f"## {title}", "", note, "",
             "| Metric | " + " | ".join(VARIANTS) + " |",
             "|---" * (len(VARIANTS) + 1) + "|"]
        rows = [
            ("Trades", "trades", "{:,}"),
            ("Still open / truncated", "still_open_or_truncated", "{:,}"),
            ("**Mean return**", "mean_ret_pct", "**{:+}%**"),
            ("Median return", "median_ret_pct", "{:+}%"),
            ("Win rate (any profit)", "win_rate_positive", "{}%"),
            ("Hit rate (≥50%)", "hit_rate_50pct", "{}%"),
            ("Monster rate (≥100%)", "monster_rate_100pct", "{}%"),
            ("**Mean weeks held**", "mean_weeks", "**{}**"),
            ("Median weeks held", "median_weeks", "{}"),
            ("% held beyond 52 weeks", "pct_held_over_52w", "{}%"),
            ("Median per-trade annualised", "median_per_trade_cagr", "{:+}%"),
            ("**Annual return on deployed capital**", "annual_return_on_deployed_capital", "**{:+}%**"),
            ("Total P&L (Rs)", "total_pnl_rs", "Rs {:,.0f}"),
            ("Capital-years used", "capital_years_used", "{}"),
            ("Worst trade", "worst_ret", "{:+}%"),
            ("Best trade", "best_ret", "{:+}%"),
        ]
        for label, key, fmt in rows:
            cells = []
            for v in VARIANTS:
                val = st.get(v, {}).get(key)
                cells.append(fmt.format(val) if val is not None else "—")
            L.append(f"| {label} | " + " | ".join(cells) + " |")
        return L

    L = ["# Exit-rule study — how long should a Stage 2 trade be held?", "",
         f"Window: last {args.years:g} years · market cap ≥ Rs {args.min_mcap_cr:,.0f} Cr · "
         f"Rs {args.capital:,.0f} per trade · {args.cost_pct}% round-trip cost.", "",
         "**The number to compare rules on is _annual return on deployed capital_** — total "
         "P&L divided by the capital-time actually used. A rule that makes +40% in 20 weeks "
         "beats one making +50% in 80 weeks, because it hands the money back sooner.", ""]

    L += block("All Stage 2 signals", all_stats,
               "Every confirmed signal, no entry filter.")
    L += [""]
    L += block("Signals passing the recipe filters", filt_stats,
               "Nifty 1-yr return ≤ +10%, stock's prior 1-yr return ≤ 0%, "
               "volume ≥1.5× its 20-week average, market cap ≤ Rs 15,000 Cr.")

    L += ["", "## Exit rules tested", "",
          "* **fixed_52w** — hold exactly 52 weeks regardless (the old baseline)",
          "* **ma_break** — first weekly close below the 30-week MA, exit next open, no time cap",
          "* **ma_2closes** — needs two consecutive weekly closes below the MA",
          f"* **ma_buffer3** — the close must be {BUFFER_PCT*100:.0f}% below the MA, not merely under it",
          f"* **ma_grace8** — as ma_break, but the rule is only armed from week {GRACE_WEEKS}",
          f"* **ma_hardstop** — ma_break plus a hard {HARD_STOP_PCT:.0f}% stop from entry",
          "",
          "## Caveats", "",
          "* Trades still running when the data ends are **excluded** from the completed-trade "
          "stats and counted separately. Including them at the last price would flatter the "
          "long-holding rules, since an open trade in an uptrend books an unrealised gain.",
          "* Exits use the weekly open after the triggering close — no intra-week fills, and "
          "no assumption you could sell at the exact MA touch.",
          "* Per-trade annualised is a **median**, not a mean: a +40% trade closed in 3 weeks "
          "annualises to an absurd number and would distort any average.",
          "* All the standing limitations apply — survivorship bias, reconstructed market cap, "
          "adjusted prices, flat costs. Figures are optimistic.",
          ]
    return "\n".join(L) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--years", type=float, default=9)
    p.add_argument("--min-mcap-cr", type=float, default=2000)
    p.add_argument("--cost-pct", type=float, default=0.3)
    p.add_argument("--capital", type=float, default=10000)
    p.add_argument("--rs-lookback", type=int, default=2)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--tag", default="exits")
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
    for d_ in (o, h, l, c, v):
        d_.drop(columns=[cfg["benchmark"]], inplace=True, errors="ignore")
    idx = bench_close.dropna().index
    o, h, l, c, v = (d_.reindex(idx) for d_ in (o, h, l, c, v))
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
    print(f"  {int(sig.values.sum()):,} raw signals")

    # recipe filters, evaluated at the signal week
    idx_52 = ((bench_close / bench_close.shift(52) - 1) * 100)
    prior_52 = ((c / c.shift(52) - 1) * 100)
    vol_surge = v / v.rolling(20).mean()
    recipe = (sig
              & (idx_52 <= 10).values[:, None]
              & (prior_52 <= 0)
              & (vol_surge >= 1.5)
              & (mcap_hist <= 15000 * CRORE))
    print(f"  {int(recipe.values.sum()):,} signals pass the recipe filters")

    print("*** Simulating exits (all signals) ***", flush=True)
    tr_all = simulate(sig, o, c, ma30, cost_pct=args.cost_pct)
    print("*** Simulating exits (recipe-filtered) ***", flush=True)
    tr_filt = simulate(recipe, o, c, ma30, cost_pct=args.cost_pct)

    tr_all.to_csv(os.path.join(OUT_DIR, f"exits_{args.tag}_all.csv"), index=False)
    tr_filt.to_csv(os.path.join(OUT_DIR, f"exits_{args.tag}_recipe.csv"), index=False)

    all_stats = {v_: stats(tr_all[tr_all.variant == v_], args.capital) for v_ in VARIANTS}
    filt_stats = {v_: stats(tr_filt[tr_filt.variant == v_], args.capital) for v_ in VARIANTS}

    for v_ in VARIANTS:
        s = all_stats[v_]
        print(f"  {v_:<12} n={s.get('trades',0):>5} mean={s.get('mean_ret_pct')}% "
              f"wks={s.get('median_weeks')} annual_on_capital={s.get('annual_return_on_deployed_capital')}%")

    report = write_report(all_stats, filt_stats, args)
    with open(os.path.join(OUT_DIR, f"exits_{args.tag}.md"), "w") as f:
        f.write(report)
    with open(os.path.join(OUT_DIR, f"exits_{args.tag}.json"), "w") as f:
        json.dump({"params": vars(args), "all_signals": all_stats,
                   "recipe_filtered": filt_stats}, f, indent=2)
    print("\n" + report)


if __name__ == "__main__":
    main()
