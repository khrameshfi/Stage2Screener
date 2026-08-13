#!/usr/bin/env python
"""
backtest_stage2.py - Weekly Stan Weinstein Stage 2 backtest, Indian market.

Question being tested: of the stocks that confirmed a weekly Stage 2 signal
(Mansfield RS turning positive + price above the 30-week MA, market cap > a
floor), what fraction went on to gain >=50% over the following 52 weeks - and
separately, what would a trader following Weinstein's own exit rule (sell on a
weekly close below the 30-week MA) actually have captured, versus just holding
blind for a year?

Two signal-strictness configs are tested side by side:
  Loose  - RS turned positive within the last 2 weeks + price above the 30-week MA
  Strict - RS turned positive within the last week + price above the 30-week MA
           + a volume spike (>=1.5x its 20-week average) within the last 5 weeks
           (this matches the live screener's current default toggles)

And two outcomes are reported for the SAME set of entries:
  Fixed 52-week hold - the actual answer to "did it reach +50% in a year"
  Weinstein MA exit  - sell at the next open after the first weekly close below
                        the 30-week MA, capped at the same 52-week horizon

Adapted from RSind's backtest.py (same discipline: enter at the NEXT bar's open
after a confirmed signal, so nothing here trades on a bar's own close), rebuilt
for weekly bars, Mansfield RS instead of IBD RS, and Weinstein-style exits
instead of EMA exits. Signal maths (Mansfield RS formula, 30-week MA, volume
spike definition, liquidity floors) is kept identical to stage2_screener.py so
this backtest is actually testing what the live screener signals.

Setup:
    pip install --upgrade yfinance pandas numpy requests

Run (this needs real internet access - Yahoo Finance - so it's meant to run via
the backtest.yml GitHub Actions workflow, not in a sandboxed environment):
    python backtest_stage2.py --years 9 --min-mcap-cr 2000 --capital 10000

Known limitations - read before trusting the numbers
------------------------------------------------------
  * Survivorship bias, and a direct mechanism for it: the universe is NSE's
    CURRENT equity list. A stock that got delisted, merged, or suspended
    partway through its holding period has no future price data, so its trade
    is dropped entirely (not scored as a loss) - see "dropped, no future data"
    in the report. Those are disproportionately losers. Every number here is
    optimistic relative to what a trader in 2016 could actually have captured.
  * Market cap is reconstructed as (today's implied share count, i.e. current
    market cap / current price) x each week's historical close - not true
    point-in-time market cap. Issuance and buybacks are not modelled.
  * Prices are split/dividend adjusted, so entry prices are not what would
    have actually been on screen at the time; returns are correct, price
    levels are not.
  * Costs are a flat percentage. Real impact cost on an illiquid smallcap
    breakout, especially with other traders chasing the same signal, is worse.
  * Signals within the last ~52 weeks of the data can't be scored yet (no
    forward-looking data exists) - excluded from hit-rate stats and reported
    separately as "too recent to score," not silently dropped.
"""

import argparse
import json
import os
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

os.environ.setdefault("MARKET", "IN")   # stage2_screener reads this at import time
from stage2_screener import get_universe_symbols, MARKET_CONFIG, get_market_cap

DIR = os.path.dirname(os.path.realpath(__file__))
OUT_DIR = os.path.join(DIR, "output", "backtest")
CRORE = 1e7

MRS_LEN = 52           # Mansfield RS smoothing, weeks - matches stage2_screener.py
MA_LEN = 30             # weeks
VOL_AVG_LEN = 20        # weeks
VOL_LOOKBACK_WEEKS = 5
VOL_MULT = 1.5
HOLD_WEEKS = 52          # the "1 year" horizon being tested
BUCKET_LABELS = ["<-25%", "-25% to 0%", "0-25%", "25-50%", "50-100%", ">100%"]


# -- Data -----------------------------------------------------------------------

def download_weekly_panel(symbols, start_date, end_date, batch_size=100):
    """Weekly OHLCV for every symbol, split/dividend adjusted, batched via yfinance.
    Explicit start/end dates rather than a period string - yfinance's period
    shorthand is only reliably valid for a small enumerated set of values, and
    this needs arbitrary multi-year windows."""
    frames = {}
    total = (len(symbols) + batch_size - 1) // batch_size
    for b in range(total):
        chunk = symbols[b * batch_size:(b + 1) * batch_size]
        df = None
        for attempt in range(3):
            try:
                df = yf.download(chunk, start=start_date, end=end_date, interval="1wk",
                                 auto_adjust=True, progress=False,
                                 group_by="ticker", threads=True)
                break
            except Exception as e:
                print(f"  batch {b + 1}/{total} attempt {attempt + 1} failed: {e}")
                time.sleep(5)
        if df is None or df.empty:
            print(f"  batch {b + 1}/{total}: no data, skipped.")
            continue
        if isinstance(df.columns, pd.MultiIndex):
            for t in chunk:
                if t not in df.columns.get_level_values(0):
                    continue
                sub = df[t].dropna(subset=["Close"])
                if len(sub):
                    frames[t] = sub
        else:
            sub = df.dropna(subset=["Close"])
            if len(sub):
                frames[chunk[0]] = sub
        print(f"  batch {b + 1}/{total}: {len(frames)} series so far", flush=True)
        time.sleep(1)
    return frames


def panel(frames, field):
    return pd.DataFrame({t: d[field] for t, d in frames.items()}).sort_index()


# -- Indicators -------------------------------------------------------------------

def mansfield_rs(close, bench_close):
    """Identical formula to stage2_screener.py's compute_metrics(): ((c/bc)/SMA(ratio,52)-1)*10."""
    rsr = close.div(bench_close, axis=0)
    rsr_ma = rsr.rolling(MRS_LEN).mean()
    return (rsr / rsr_ma - 1) * 10


def rs_turned_positive_within(mrs, lookback_weeks):
    """True where Mansfield RS is currently positive AND crossed from <=0 to >0
    within the last `lookback_weeks` bars - vectorized equivalent of
    stage2_screener.py's weeks_since_rs_cross() applied across the whole panel."""
    # NOTE: pos.shift(1).fillna(False) silently upcasts a bool frame to object
    # dtype (shift introduces NaN, which bool can't hold), and `~` on an object
    # array of Python bools does bitwise-NOT on the underlying ints (~True ==
    # -2, ~False == -1) instead of logical negation - both truthy, so it would
    # flag nearly every week as "just turned." shift(fill_value=False) keeps
    # proper bool dtype throughout and avoids that trap.
    pos = mrs > 0
    just_turned = pos & ~pos.shift(1, fill_value=False)
    within = just_turned.copy()
    for k in range(1, lookback_weeks + 1):
        within = within | just_turned.shift(k, fill_value=False)
    return within & pos


def volume_spike_recent(volume, avg_len=VOL_AVG_LEN, lookback=VOL_LOOKBACK_WEEKS, mult=VOL_MULT):
    avg_vol = volume.rolling(avg_len).mean()
    spike_bar = volume > mult * avg_vol
    return spike_bar.rolling(lookback).max().fillna(0).astype(bool)


# -- Market cap (one-time fetch, reconstructed backward) -------------------------

def reconstruct_market_cap(close, tickers):
    """One-time current-market-cap fetch per ticker (same call the live screener
    uses), then implied-shares x each week's close gives a historical estimate.
    True point-in-time market cap isn't available without a paid data source."""
    print(f"Fetching current market cap for {len(tickers)} tickers (one-time, "
          "used to imply a share count for the historical reconstruction)...")
    mcap_now = {}
    for i, t in enumerate(tickers, 1):
        if i == 1 or i % 100 == 0:
            print(f"  ...{i}/{len(tickers)}")
        mc = get_market_cap(t)
        if mc:
            mcap_now[t] = mc
        time.sleep(0.3)
    mcap_now = pd.Series(mcap_now, dtype="float64").reindex(close.columns)
    last_close = close.ffill().iloc[-1]
    shares = (mcap_now / last_close).replace([np.inf, -np.inf], np.nan)
    return close.mul(shares, axis=1), mcap_now


def build_liquidity_mask(close, volume, mcap_hist, cfg, min_mcap_cr):
    price_ok = close >= cfg["min_price"]
    vol_ok = volume.rolling(VOL_AVG_LEN, min_periods=10).mean() >= cfg["min_avg_volume"]
    mcap_ok = mcap_hist >= min_mcap_cr * CRORE
    return price_ok & vol_ok & mcap_ok & close.notna()


# -- Signal construction ----------------------------------------------------------

def build_signals(close, volume, ma30, mrs, liquid, in_window):
    above_ma = close > ma30
    vol_spike = volume_spike_recent(volume)

    loose = rs_turned_positive_within(mrs, 2) & above_ma
    strict = rs_turned_positive_within(mrs, 1) & above_ma & vol_spike

    win = in_window.values[:, None]
    return {
        "Loose": loose & liquid & win & close.notna(),
        "Strict": strict & liquid & win & close.notna(),
    }


# -- Trade engine -------------------------------------------------------------------

def simulate(signals, o, c, ma30, hold_weeks=HOLD_WEEKS, cost_pct=0.0):
    """
    Walks each ticker independently. Entry is the OPEN of the week after a
    confirmed signal (the signal is only known once that week's bar has
    closed, so trading on its own close would be lookahead bias).

    For each entry, two parallel outcomes are computed on the SAME entry price:
      - fixed 52-week hold: exit at the close `hold_weeks` after entry (the
        answer to "did it reach +50% in a year")
      - Weinstein MA exit: exit at the open of the week AFTER the first weekly
        close back below the 30-week MA, capped at the same 52-week horizon

    A ticker can't take a new signal while a previous trade - measured by the
    longer of the two exits, i.e. the fixed-hold horizon - is still open, so
    trades on the same name never overlap.

    Returns (trades_df, dropped_missing_future) - the second is the count of
    otherwise-valid entries dropped because price data ran out before the
    52-week mark (almost always delisting/suspension - see module docstring).
    """
    trades = []
    dropped_missing_future = 0
    dates = c.index
    n = len(dates)

    for tk in signals.columns:
        sig = np.flatnonzero(signals[tk].values)
        if not len(sig):
            continue

        O, C, MA = o[tk].values, c[tk].values, ma30[tk].values
        busy_until = -1

        for s in sig:
            entry_i = s + 1
            if entry_i >= n or entry_i <= busy_until:
                continue
            entry = O[entry_i]
            if not np.isfinite(entry) or entry <= 0:
                continue

            fixed_exit_i = min(entry_i + hold_weeks, n - 1)
            scoreable = (entry_i + hold_weeks) <= (n - 1)

            # Reserve this ticker's "busy" slot now, before checking whether the
            # future data actually exists. Otherwise a single breakout that (per
            # the strictness config's lookback) fires signals on 2-3 consecutive
            # weeks would, on a missing-future-data drop, immediately re-attempt
            # on the very next signal week too - triple-counting one underlying
            # missed trade instead of counting it once.
            busy_until = fixed_exit_i

            fixed_px = C[fixed_exit_i]
            if not np.isfinite(fixed_px):
                dropped_missing_future += 1
                continue

            # Weinstein MA exit: first CONFIRMED (closed) weekly close below the
            # 30-week MA, exit at next week's open, capped at fixed_exit_i.
            ma_exit_i, ma_exit_px, ma_reason = fixed_exit_i, fixed_px, "52w_cap"
            for j in range(entry_i, fixed_exit_i):
                if np.isfinite(C[j]) and np.isfinite(MA[j]) and C[j] < MA[j]:
                    exit_j = min(j + 1, fixed_exit_i)
                    if np.isfinite(O[exit_j]):
                        ma_exit_i, ma_exit_px, ma_reason = exit_j, O[exit_j], "ma_break"
                    break

            fixed_ret = (fixed_px / entry - 1) * 100
            ma_ret = (ma_exit_px / entry - 1) * 100

            trades.append({
                "ticker": tk,
                "signal_date": dates[s].date().isoformat(),
                "entry_date": dates[entry_i].date().isoformat(),
                "entry": round(float(entry), 2),
                "scoreable": bool(scoreable),
                "fixed_exit_date": dates[fixed_exit_i].date().isoformat(),
                "fixed_ret_pct": round(fixed_ret, 2),
                "fixed_net_pct": round(fixed_ret - cost_pct, 2),
                "ma_exit_date": dates[ma_exit_i].date().isoformat(),
                "ma_exit_reason": ma_reason,
                "ma_weeks_held": int(ma_exit_i - entry_i),
                "ma_ret_pct": round(ma_ret, 2),
                "ma_net_pct": round(ma_ret - cost_pct, 2),
            })

    return pd.DataFrame(trades), dropped_missing_future


# -- Reporting ------------------------------------------------------------------

def metrics(tr, dropped_missing_future):
    if tr.empty:
        return {"trades": 0, "dropped_missing_future": dropped_missing_future}

    scored = tr[tr.scoreable]
    too_recent = len(tr) - len(scored)
    if scored.empty:
        return {"trades": 0, "too_recent_to_score": too_recent,
                "dropped_missing_future": dropped_missing_future}

    fixed = scored.fixed_net_pct
    hit = (fixed >= 50).mean() * 100

    ma_hit = (scored.ma_net_pct >= 50).mean() * 100

    # Of the eventual (fixed-hold) 1-year winners, what did the MA-exit rule
    # actually capture, and what fraction were stopped out before week 52
    # rather than ridden the whole way?
    winners = scored[scored.fixed_net_pct >= 50]
    capture_avg = winners.ma_net_pct.mean() if len(winners) else None
    early_exit_pct = (winners.ma_exit_reason == "ma_break").mean() * 100 if len(winners) else None

    buckets = pd.cut(fixed, bins=[-np.inf, -25, 0, 25, 50, 100, np.inf], labels=BUCKET_LABELS)
    dist = buckets.value_counts().reindex(BUCKET_LABELS).fillna(0).astype(int).to_dict()

    return {
        "trades": int(len(scored)),
        "too_recent_to_score": int(too_recent),
        "dropped_missing_future": int(dropped_missing_future),
        "hit_rate_50pct_fixed_1yr": round(float(hit), 1),
        "avg_ret_fixed_1yr": round(float(fixed.mean()), 1),
        "median_ret_fixed_1yr": round(float(fixed.median()), 1),
        "best_fixed_1yr": round(float(fixed.max()), 1),
        "worst_fixed_1yr": round(float(fixed.min()), 1),
        "distribution": {str(k): int(v) for k, v in dist.items()},
        "ma_exit_hit_rate_50pct": round(float(ma_hit), 1),
        "ma_exit_avg_ret": round(float(scored.ma_net_pct.mean()), 1),
        "ma_exit_median_weeks_held": int(scored.ma_weeks_held.median()),
        "ma_exit_pct_stopped_early": round(float((scored.ma_exit_reason == "ma_break").mean() * 100), 1),
        "among_1yr_winners_ma_capture_avg": round(float(capture_avg), 1) if capture_avg is not None else None,
        "among_1yr_winners_pct_exited_early": round(float(early_exit_pct), 1) if early_exit_pct is not None else None,
    }


def write_report(results, bench_hit_rate, bench_avg, args, universe_n, start, end):
    lines = [
        "# Stage 2 backtest — weekly Mansfield RS + 30-week MA (Indian market)", "",
        f"Window **{start} → {end}** (signal window: last {args.years:g} years) — "
        f"universe **{universe_n}** NSE names, market cap floor Rs {args.min_mcap_cr:,.0f} Cr "
        "(reconstructed, see limitations below)", "",
        f"Position size: Rs {args.capital:,.0f} per trade, unlimited concurrent positions. "
        f"Round-trip cost: {args.cost_pct}%, deducted from every trade.", "",
        "## Did Stage 2 confirmations reach +50% within a year?", "",
        "| | Loose | Strict |", "|---|---:|---:|",
    ]
    rows = [
        ("Scoreable signals", "trades", "{:,}"),
        ("Too recent to score yet", "too_recent_to_score", "{:,}"),
        ("Dropped, no future data (likely delisted)", "dropped_missing_future", "{:,}"),
        ("**Hit rate: reached ≥50% in 52wk**", "hit_rate_50pct_fixed_1yr", "**{}%**"),
        ("Average 1yr return", "avg_ret_fixed_1yr", "{:+}%"),
        ("Median 1yr return", "median_ret_fixed_1yr", "{:+}%"),
        ("Best 1yr return", "best_fixed_1yr", "{:+}%"),
        ("Worst 1yr return", "worst_fixed_1yr", "{:+}%"),
    ]
    for label, key, fmt in rows:
        cells = []
        for n in ("Loose", "Strict"):
            v = results[n].get(key)
            cells.append(fmt.format(v) if v is not None else "-")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    lines.append("")
    if bench_hit_rate is not None:
        lines.append(
            f"For comparison — Nifty 50 itself, every rolling {args.hold_weeks}-week window "
            f"over the same period: hit rate {bench_hit_rate:.1f}% (avg {bench_avg:+.1f}%)"
        )
    lines += [
        "", "## Return distribution (fixed 1-year hold)", "",
        "| Bucket | Loose | Strict |", "|---|---:|---:|",
    ]
    for bucket in BUCKET_LABELS:
        cells = [str(results[n].get("distribution", {}).get(bucket, 0)) for n in ("Loose", "Strict")]
        lines.append(f"| {bucket} | " + " | ".join(cells) + " |")

    lines += [
        "", "## If you'd used Weinstein's own exit (sell on a weekly close below the 30-week MA)", "",
        "| | Loose | Strict |", "|---|---:|---:|",
    ]
    rows2 = [
        ("MA-exit hit rate (≥50%)", "ma_exit_hit_rate_50pct", "{}%"),
        ("MA-exit average return", "ma_exit_avg_ret", "{:+}%"),
        ("MA-exit median weeks held", "ma_exit_median_weeks_held", "{}"),
        ("% stopped out before week 52", "ma_exit_pct_stopped_early", "{}%"),
        ("Of the eventual 1yr winners — avg MA-exit capture", "among_1yr_winners_ma_capture_avg", "{:+}%"),
        ("Of the eventual 1yr winners — % exited early anyway", "among_1yr_winners_pct_exited_early", "{}%"),
    ]
    for label, key, fmt in rows2:
        cells = []
        for n in ("Loose", "Strict"):
            v = results[n].get(key)
            cells.append(fmt.format(v) if v is not None else "-")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    lines += [
        "", "## Read this before acting on the numbers", "",
        "* **Survivorship bias.** The universe is NSE's *current* equity list. A stock "
        "delisted, merged, or suspended during its holding period has no future price data, "
        "so its trade is dropped entirely (see \"dropped, no future data\" above) rather than "
        "scored as a loss. Every number here is optimistic relative to what a trader could "
        "actually have captured at the time.",
        "* **Market cap is reconstructed** from today's implied share count (current market "
        "cap / current price) x each week's historical close. Issuance and buybacks between "
        "then and now are not modelled.",
        "* **Adjusted prices.** Returns are correct; the absolute price levels are not what "
        "was actually on screen at the time.",
        f"* **Costs are a flat {args.cost_pct}% round trip.** Real impact cost on an illiquid "
        "smallcap breakout — especially with other traders chasing the same signal — is worse.",
        "* \"Too recent to score\" signals (inside the last year of data) are excluded from "
        "hit-rate stats since there's no forward-looking data yet to check them against — "
        "not dropped silently, just not counted.",
        "* A positive hit rate on one continuous window is not proof of an edge across market "
        "regimes. Worth checking whether it holds if you split the window in half.",
    ]
    return "\n".join(lines) + "\n"


# -- Main -------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--years", type=float, default=9,
                   help="signal window length in years (extra history is fetched underneath for warmup)")
    p.add_argument("--min-mcap-cr", type=float, default=2000)
    p.add_argument("--cost-pct", type=float, default=0.3, help="round-trip cost, %%, deducted from every trade")
    p.add_argument("--capital", type=float, default=10000)
    p.add_argument("--hold-weeks", type=int, default=HOLD_WEEKS)
    p.add_argument("--limit", type=int, default=0, help="cap universe size (for a quick test run)")
    p.add_argument("--tag", default="v1", help="suffix for output filenames")
    args = p.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    cfg = MARKET_CONFIG["IN"]

    buffer_years = 2.5   # extra history under the signal window, for 52wk RS / 30wk MA warmup
    end_date = date.today()
    start_date = end_date - timedelta(days=int((args.years + buffer_years) * 365) + 30)

    print("*** Universe ***", flush=True)
    symbols = get_universe_symbols(cfg)
    if args.limit:
        symbols = symbols[:args.limit]
    tickers = [f"{s}{cfg['suffix']}" for s in symbols]
    print(f"  {len(tickers)} NSE symbols")

    print(f"*** Downloading weekly bars, {start_date} -> {end_date} ***", flush=True)
    frames = download_weekly_panel(tickers + [cfg["benchmark"]], start_date, end_date)
    if cfg["benchmark"] not in frames:
        raise RuntimeError("No benchmark data downloaded; aborting.")
    print(f"  {len(frames)} series downloaded")

    o, h, l, c, v = (panel(frames, f) for f in ("Open", "High", "Low", "Close", "Volume"))
    bench_close = c[cfg["benchmark"]].copy()
    for df in (o, h, l, c, v):
        df.drop(columns=[cfg["benchmark"]], inplace=True, errors="ignore")

    idx = bench_close.dropna().index
    o, h, l, c, v = (d.reindex(idx) for d in (o, h, l, c, v))
    bench_close = bench_close.reindex(idx)

    print("*** Computing Mansfield RS / 30-week MA on every date ***", flush=True)
    mrs = mansfield_rs(c, bench_close)
    ma30 = c.rolling(MA_LEN).mean()

    print("*** Market cap (one-time fetch, reconstructed backward) ***", flush=True)
    mcap_hist, mcap_now = reconstruct_market_cap(c, list(c.columns))

    liquid = build_liquidity_mask(c, v, mcap_hist, cfg, args.min_mcap_cr)

    signal_start = idx[-1] - pd.Timedelta(days=int(args.years * 365))
    in_window = pd.Series(idx >= signal_start, index=idx)

    print("*** Building signals ***", flush=True)
    signals = build_signals(c, v, ma30, mrs, liquid, in_window)
    for name, sig in signals.items():
        print(f"  {name}: {int(sig.values.sum())} raw signals in window")

    results = {}
    for name, sig in signals.items():
        print(f"*** Simulating '{name}' config ***", flush=True)
        tr, dropped = simulate(sig, o, c, ma30, hold_weeks=args.hold_weeks, cost_pct=args.cost_pct)
        results[name] = metrics(tr, dropped)
        tr.to_csv(os.path.join(OUT_DIR, f"trades_{args.tag}_{name.lower()}.csv"), index=False)
        print(f"  {results[name].get('trades', 0)} scoreable trades, "
              f"hit-rate {results[name].get('hit_rate_50pct_fixed_1yr')}%, "
              f"{dropped} dropped (no future data)")

    # Same-length rolling-window comparison: for every week, what was the Nifty's
    # OWN forward hold_weeks-week return? Not a trade-for-trade match, just context.
    bench_fwd = (bench_close.shift(-args.hold_weeks) / bench_close - 1) * 100
    bench_in_window = bench_fwd[in_window.values].dropna()
    bench_hit_rate = float((bench_in_window >= 50).mean() * 100) if len(bench_in_window) else None
    bench_avg = float(bench_in_window.mean()) if len(bench_in_window) else None

    report = write_report(results, bench_hit_rate, bench_avg, args, len(tickers),
                          idx[0].date(), idx[-1].date())
    with open(os.path.join(OUT_DIR, f"summary_{args.tag}.md"), "w") as f:
        f.write(report)
    with open(os.path.join(OUT_DIR, f"summary_{args.tag}.json"), "w") as f:
        json.dump({
            "params": vars(args),
            "results": results,
            "benchmark_1yr_hit_rate": round(bench_hit_rate, 1) if bench_hit_rate is not None else None,
            "benchmark_1yr_avg_return": round(bench_avg, 1) if bench_avg is not None else None,
        }, f, indent=2)

    print("\n" + report)


if __name__ == "__main__":
    main()
