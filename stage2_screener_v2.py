"""
Stage 2 Screener v2 - BACKTEST-TUNED variant. Runs ALONGSIDE the original.
==========================================================================
This is a SEPARATE screener. `stage2_screener.py` is untouched and keeps running
exactly as before, writing its own files. Nothing here overwrites it.

    stage2_screener.py     ->  output/stage2_screener_<MARKET>_results.csv
    stage2_screener_v2.py  ->  output/v2/stage2_screener_v2_<MARKET>_results.csv

Run both, compare the lists, and decide for yourself whether the extra filters
are worth the much smaller output before trusting either one.

WHAT IS DIFFERENT - four changes, all from the 9-year backtest (3,116 signals,
within-year confound control + split-half validation; see output/backtest/
ANSWER.md and RECIPE.md):

  1. STOCK MUST HAVE BEEN QUIET - prior 1-year return <= 0%. The strongest
     stock-level rule found, and the most consistent (+11.9 pts in the first half
     of the window, +8.9 in the second). Stocks down >20% beforehand doubled
     17.3% of the time; ones already up 40-80% managed 3.8%.
  2. MARKET REGIME GATE - the index's own trailing 1-year return must be <= 10%.
     The strongest single factor in the study. Defaults to WARN, not block.
  3. MAXIMUM MARKET CAP - Rs 15,000cr. The original has a floor but no ceiling.
  4. RS_TURN_LOOKBACK_WEEKS 1 -> 2, matching what every validated result used.

Plus a `recent_ipo` column (1-2 year old listings doubled at 17.2% vs a 7.9%
baseline) - reported only, never used to filter.

EXPECT FAR FEWER SIGNALS. The quiet-stock rule alone cut the backtest sample from
3,116 to 883. With the market-cap ceiling on top, expect roughly a fifth of what
the original produces - and close to nothing when the regime gate is shut. That is
the intended behaviour, not a bug.

Setup:
    pip3 install --upgrade yfinance pandas requests

Run:
    python3 stage2_screener_v2.py

Output:
    output/v2/stage2_screener_v2_<MARKET>_results.csv

IMPORTANT: checking stocks one-by-one takes time. India now scans the FULL
NSE-listed universe (~2000 stocks, not just the Nifty 500), so expect longer
than before - likely 45-90+ min depending on how many survive the market cap
filter. US remains the biggest, at 1-2+ hours. That's expected; one-at-a-time
fetching is what avoids the curl/database crash errors we hit before with
multi-threaded batch downloads. The market cap check runs first and is cheaper
than the full weekly-history fetch, so it saves real time by skipping small
caps early rather than downloading years of data for stocks you don't want anyway.
"""

import os
import json
import time
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
import pandas as pd
import yfinance as yf

# ============================================================
#  MARKET SWITCH - reads from the MARKET environment variable
#  if set (so a GitHub Actions workflow can run both markets
#  automatically), otherwise defaults to "IN" for local runs.
#  Local use is unchanged: just edit the default below, same as before.
# ============================================================
MARKET = os.environ.get("MARKET", "IN")     # "IN" = NSE India, "US" = US (NASDAQ + NYSE)
# ============================================================

CR = 1e7   # 1 crore = 1,00,00,000 - used to convert crore inputs to plain INR

MARKET_CONFIG = {
    "IN": {
        "benchmark": "^NSEI",
        "suffix": ".NS",
        "universe_mode": "ALL_NSE",   # "ALL_NSE" = every NSE-listed equity (~2000), "NIFTY500" = just the Nifty 500 index
        "local_symbol_csv": None,     # set to your own CSV path (needs a "Symbol" column) if the NSE URL below ever fails
        "min_price": 20,              # INR - liquidity filter floor
        "min_avg_volume": 50000,      # shares/week - liquidity filter floor
        "min_market_cap": 2000 * CR,  # 2000 crore, expressed in plain INR
        "max_market_cap": 15000 * CR, # [v2] large caps rarely produced the big moves.
                                      # Small but consistent edge in BOTH halves (+2.2/+3.9 pts).
        "regime_max_1y_return": 10.0, # [v2] index 1yr return limit. Nifty up <4.6% -> 31.5%
                                      # hit rate; up >25.5% -> 10.2%. Monotonic, 8/9 years.
    },
    "US": {
        "benchmark": "^GSPC",
        "suffix": "",
        "universe_mode": None,        # not used for US
        "local_symbol_csv": None,     # set to your own CSV path (needs a "Symbol" column) if the NASDAQ URLs below ever fail
        "min_price": 5,               # USD - liquidity filter floor
        "min_avg_volume": 200000,     # shares/week - liquidity filter floor
        "min_market_cap": 2_000_000_000,  # $2B - a rough equivalent floor; adjust to taste
        "max_market_cap": 15_000_000_000, # [v2] mirrors India. NOTE: the v2 filters were
                                          # derived from INDIAN data only and are UNTESTED
                                          # on US stocks. Treat as a guess there.
        "regime_max_1y_return": 10.0,     # [v2] same caveat - India-derived, untested on S&P.
    },
}

# ---------------- STRATEGY TOGGLES (flip these freely, no code changes needed elsewhere) ----------------
REQUIRE_RS_JUST_TURNED  = True   # only stocks where Mansfield RS crossed from negative to positive recently
RS_TURN_LOOKBACK_WEEKS  = 2      # [v2 CHANGED from 1] every validated backtest result used a
                                  # 2-week window. 1 vs 2 made no real difference to the hit
                                  # rate (21.6% vs 21.0%) but 2 yields ~21% more signals.

REQUIRE_ABOVE_30MA      = True   # require price currently above the 30-week MA

REQUIRE_MA_NOT_FALLING  = False  # [v2 - LEAVE FALSE] Weinstein's own "MA must be rising" rule
                                  # showed NO edge: -0.7 pts, positive in only 3 of 9 years.
                                  # Stocks that doubled had a median MA slope of +0.1% - FLAT.
                                  # A steeply rising 30-week MA means the move already happened.
MA_SLOPE_LOOKBACK_WEEKS = 4      # how far back to compare the MA to judge its slope
MA_FLAT_THRESHOLD_PCT   = 0.1    # a slope within +/- this % over the lookback counts as "flat" rather than up/down

REQUIRE_VOLUME_SPIKE    = True   # require a volume spike within the recent window below
VOL_LOOKBACK_WEEKS      = 5
VOL_AVG_LEN             = 20     # weeks used to compute the "average" volume being compared against
VOL_MULT                = 1.5    # what counts as a "spike" (1.5x its own average)

REQUIRE_LIQUIDITY_MIN   = True   # filter out illiquid/junk names using min_price / min_avg_volume above
EXCLUDE_ETFS            = True   # US universe only - drop ETFs from the NASDAQ/NYSE listing files

REQUIRE_MIN_MARKET_CAP  = True   # filter out small/micro caps using min_market_cap in MARKET_CONFIG above
                                  # checked BEFORE the slow weekly-history fetch, to save time on tiny stocks

# ---------------- [v2] BACKTEST-DERIVED ADDITIONS - the only new filters ----------------
REQUIRE_MAX_MARKET_CAP  = True   # cap the upper end too - see max_market_cap above

REQUIRE_STOCK_QUIET     = True   # THE BIG ONE. Only take stocks that went NOWHERE or DOWN
STOCK_MAX_PRIOR_1Y_RET  = 0.0     # over the past year. Most consistent rule in the study.
                                  # This is the Stage 1 base Weinstein actually describes.
                                  # Set False to see how much it is really costing you.

REGIME_GATE_MODE        = "warn"  # "warn"  = list signals, tag them, print a loud banner
                                   # "block" = report nothing while the gate is shut
                                   # "off"   = ignore the regime entirely
                                   # Blocking silently looks like a broken scan, so the
                                   # default keeps visibility and leaves the call to you.

FLAG_RECENT_IPO         = True   # reported as a column, NEVER used to exclude - the sample
IPO_MAX_WEEKS_LISTED    = 104     # is small (122) and survivorship bias hits IPOs hardest.

# ---------------- [v2] TESTED AND REJECTED - do not add these back ----------------
#   * "price near its 52-week high"      -3.6 pts, positive in only 2 of 9 years
#   * "not over-extended above the MA"   -4.2 pts - and BACKWARDS: more extended did better
#   * "index near its own 52-week high"  -2.8 pts, 3 of 9 years
#   * entry-candle shape / range expansion / closing at the high - predicted NOTHING
#   * "too many signals this week" - the edge vanished once each year was checked on its
#     own. It was measuring the calendar, not crowding.

# ---------------- CORE TECHNICAL SETTINGS (rarely need changing) ----------------
MRS_LEN                = 52      # Mansfield RS smoothing length (standard weekly)
MA_LEN                 = 30      # the trend MA itself
HISTORY_PERIOD         = "3y"
PAUSE_BETWEEN_REQUESTS = 1.0     # seconds between each stock - keep this to avoid rate-limit/crash issues
RETRIES_PER_TICKER     = 2
PROGRESS_EVERY         = 25
# ----------------------------------------------------------------------------------

OUTPUT_CSV = f"output/v2/stage2_screener_v2_{MARKET}_results.csv"   # [v2] separate dir

SYMBOL_EXCHANGE = {}   # populated for US during get_universe_symbols(); symbol -> "NASDAQ"/"NYSE"/etc.

# ---------------- PARTIAL vs CLOSED WEEK DETECTION ----------------
# Yahoo stamps each weekly bar with its week-START Monday. We compare that against
# the current week's Monday in MARKET-LOCAL time to decide whether the newest bar
# is a finished week ("closed") or the still-forming current week ("partial").
MARKET_TZ = {"IN": "Asia/Kolkata", "US": "America/New_York"}
# Local wall-clock time the week's final session ends (Friday).
MARKET_WEEK_CLOSE = {"IN": (15, 30), "US": (16, 0)}   # (hour, minute)


def market_now():
    """Current time in the selected market's local timezone."""
    return datetime.now(ZoneInfo(MARKET_TZ[MARKET]))


def current_week_monday():
    """The Monday (date) of the week we're currently in, market-local."""
    now = market_now()
    return (now - timedelta(days=now.weekday())).date()


def week_has_closed(week_monday):
    """True once that week's final session (Friday close) has passed, market-local.

    Deliberately conservative: we only call a week closed after its Friday close
    time has elapsed. On an early-closure holiday week this may briefly still say
    'partial' for an already-finished week - erring toward under-claiming
    confirmation rather than over-claiming it."""
    hh, mm = MARKET_WEEK_CLOSE[MARKET]
    friday = week_monday + timedelta(days=4)
    close_dt = datetime(friday.year, friday.month, friday.day, hh, mm,
                        tzinfo=ZoneInfo(MARKET_TZ[MARKET]))
    return market_now() >= close_dt


def classify_last_bar(df):
    """Given a weekly-indexed DataFrame, returns (last_bar_week_date, 'closed'|'partial').

    'partial' means the newest bar is the current week and that week hasn't finished
    trading yet - so its close, volume, and therefore every metric derived from it
    can still change before the week ends."""
    if df is None or df.empty:
        return None, None
    last_week = pd.Timestamp(df.index[-1]).date()
    if last_week >= current_week_monday() and not week_has_closed(last_week):
        return last_week, "partial"
    return last_week, "closed"
# ------------------------------------------------------------------


def nse_session():
    """A requests Session that's visited NSE's homepage first to pick up cookies.
    NSE's site has bot protection that otherwise blocks requests coming from
    GitHub Actions runners - this warm-up step is the fix already proven in RSind."""
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        s.get("https://www.nseindia.com", timeout=15)
    except Exception:
        pass  # if the warm-up itself fails, still try the real request - it may work anyway
    return s


def get_universe_symbols(cfg):
    """Fetch the list of tickers to scan for the selected MARKET."""
    if cfg.get("local_symbol_csv"):
        df = pd.read_csv(cfg["local_symbol_csv"])
        return df["Symbol"].dropna().unique().tolist()

    headers = {"User-Agent": "Mozilla/5.0"}

    if MARKET == "IN":
        mode = cfg.get("universe_mode", "NIFTY500")
        if mode == "ALL_NSE":
            url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
        else:
            url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
        try:
            resp = nse_session().get(url, timeout=15)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            # NSE's full-list file uses uppercase "SYMBOL"; the index-list file uses "Symbol".
            col = next((c for c in df.columns if c.strip().upper() == "SYMBOL"), None)
            if col is None:
                raise RuntimeError("Could not find a Symbol column - NSE may have changed the file format.")
            return df[col].dropna().unique().tolist()
        except Exception as e:
            raise RuntimeError(
                f"Could not download the NSE symbol list ({e}). "
                "Set MARKET_CONFIG['IN']['local_symbol_csv'] to your own CSV (needs a 'Symbol' column) and re-run."
            )

    if MARKET == "US":
        urls = [
            ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "NASDAQ"),
            ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", None),  # exchange varies per row
        ]
        # Best-effort mapping from NASDAQ Trader's single-letter exchange codes to
        # TradingView's exchange prefixes. Covers the common cases; anything unmapped
        # falls back to "NYSE" since that's the majority case in otherlisted.txt.
        EXCHANGE_CODE_MAP = {"N": "NYSE", "A": "AMEX", "P": "ARCA", "Z": "BATS", "V": "IEXG"}
        try:
            symbols = []
            for url, fixed_exchange in urls:
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                lines = [
                    l for l in resp.text.strip().split("\n")
                    if l and not l.startswith("File Creation Time")
                ]
                df = pd.read_csv(io.StringIO("\n".join(lines)), sep="|")
                sym_col = "Symbol" if "Symbol" in df.columns else "ACT Symbol"
                if "Test Issue" in df.columns:
                    df = df[df["Test Issue"] == "N"]
                if EXCLUDE_ETFS and "ETF" in df.columns:
                    df = df[df["ETF"] == "N"]
                for _, row in df.iterrows():
                    sym = row.get(sym_col)
                    if not isinstance(sym, str):
                        continue
                    exch = fixed_exchange or EXCHANGE_CODE_MAP.get(row.get("Exchange"), "NYSE")
                    SYMBOL_EXCHANGE[sym] = exch
                symbols.extend(df[sym_col].dropna().unique().tolist())
            # Keep plain alphabetic tickers only - this drops a small number of
            # special-class/warrant/unit tickers (e.g. "BRK.A" style symbols).
            # Fine for a broad screen; tell me if you specifically need those included.
            clean = sorted(set(s for s in symbols if isinstance(s, str) and s.isalpha()))
            return clean
        except Exception as e:
            raise RuntimeError(
                f"Could not download the US listed-securities files ({e}). "
                "Set MARKET_CONFIG['US']['local_symbol_csv'] to your own CSV (needs a 'Symbol' column) and re-run."
            )

    raise ValueError(f"Unknown MARKET '{MARKET}' - use 'IN' or 'US'.")


def fetch_weekly(ticker):
    """Fetch weekly OHLCV history for ONE ticker at a time, with retries.

    Keeps Open/High/Low alongside Close/Volume (not just Close/Volume as before) so the
    same fetch can also feed the dashboard's hover-chart candles - no extra API calls
    needed, since every candidate ticker already goes through this function once."""
    for _ in range(RETRIES_PER_TICKER):
        try:
            df = yf.Ticker(ticker).history(period=HISTORY_PERIOD, interval="1wk", auto_adjust=True)
            if df is not None and not df.empty and "Close" in df.columns:
                cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
                return df[cols].dropna(subset=["Close", "Volume"])
        except Exception:
            pass
        time.sleep(2)
    return None


def get_market_cap(ticker):
    """Lightweight market cap lookup (cheaper than fetching full weekly history), with retries.
    Handles a couple of different yfinance versions' fast_info interfaces defensively."""
    for _ in range(RETRIES_PER_TICKER):
        try:
            fi = yf.Ticker(ticker).fast_info
            for key in ("market_cap", "marketCap"):
                try:
                    mc = fi[key]
                    if mc:
                        return float(mc)
                except Exception:
                    pass
                try:
                    mc = getattr(fi, key)
                    if mc:
                        return float(mc)
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(1)
    return None


def classify_slope(ma_series):
    """Returns 'up', 'flat', or 'down' based on the MA's change over MA_SLOPE_LOOKBACK_WEEKS."""
    if len(ma_series) < MA_SLOPE_LOOKBACK_WEEKS + 1:
        return None
    now, then = ma_series.iloc[-1], ma_series.iloc[-1 - MA_SLOPE_LOOKBACK_WEEKS]
    if pd.isna(now) or pd.isna(then) or then == 0:
        return None
    pct_change = (now / then - 1) * 100
    if pct_change > MA_FLAT_THRESHOLD_PCT:
        return "up"
    if pct_change < -MA_FLAT_THRESHOLD_PCT:
        return "down"
    return "flat"


def weeks_since_rs_cross(mrs_series, max_lookback=26):
    """Returns (weeks_since_cross, cross_week_date).
    weeks_since_cross: 0 = crossed on the newest bar, 1 = one bar before it, etc.
    None if MRS isn't currently positive. cross_week_date is the actual week-start
    date of the bar where it went positive - reported so labels can use real dates
    rather than ambiguous relative wording."""
    if pd.isna(mrs_series.iloc[-1]) or mrs_series.iloc[-1] <= 0:
        return None, None
    count_positive = 0
    for i in range(1, min(max_lookback, len(mrs_series)) + 1):
        val = mrs_series.iloc[-i]
        if pd.notna(val) and val > 0:
            count_positive += 1
        else:
            break
    weeks = count_positive - 1
    cross_idx = len(mrs_series) - count_positive
    cross_date = pd.Timestamp(mrs_series.index[cross_idx]).date() if cross_idx >= 0 else None
    return weeks, cross_date


def compute_metrics(stock_df, bench_close):
    """Returns a dict of every underlying metric, computed on the LAST bar of whatever
    DataFrame it's handed. Caller decides whether that df includes a partial week -
    this function makes no assumption about it. None if there's not enough history."""
    df = stock_df.copy().join(bench_close.rename("BenchClose"), how="inner")
    min_len = MRS_LEN + VOL_AVG_LEN + max(VOL_LOOKBACK_WEEKS, MA_SLOPE_LOOKBACK_WEEKS) + 5
    if len(df) < min_len:
        return None

    rsr = df["Close"] / df["BenchClose"]
    rsr_ma = rsr.rolling(MRS_LEN).mean()
    mrs = (rsr / rsr_ma - 1) * 10   # same formula/scaling as the original Pine script

    ma30 = df["Close"].rolling(MA_LEN).mean()
    avg_vol = df["Volume"].rolling(VOL_AVG_LEN).mean()

    latest_close = df["Close"].iloc[-1]
    latest_ma30 = ma30.iloc[-1]
    latest_avg_vol = avg_vol.iloc[-1]

    recent_vol = df["Volume"].iloc[-VOL_LOOKBACK_WEEKS:]
    recent_avg = avg_vol.iloc[-VOL_LOOKBACK_WEEKS:]

    weeks, cross_date = weeks_since_rs_cross(mrs)

    # [v2] the stock's own 1-year return as of this bar - the "has it been ignored?" test
    prior_1y = None
    if len(df) >= 53:
        then = df["Close"].iloc[-53]
        if pd.notna(then) and then > 0:
            prior_1y = round(float((latest_close / then - 1) * 100), 2)

    return {
        "prior_1y_return": prior_1y,
        "mrs": round(float(mrs.iloc[-1]), 2),
        "weeks_since_rs_cross": weeks,
        "cross_week": cross_date.isoformat() if cross_date else None,
        "bar_week": pd.Timestamp(df.index[-1]).date().isoformat(),
        "above_30ma": bool(latest_close > latest_ma30) if pd.notna(latest_ma30) else None,
        "ma_slope": classify_slope(ma30),
        "vol_spike_recent": bool((recent_vol > VOL_MULT * recent_avg).any()),
        "last_close": round(float(latest_close), 2),
        "avg_volume": int(latest_avg_vol) if pd.notna(latest_avg_vol) else None,
    }


def passes_toggles(metrics, cfg):
    if REQUIRE_RS_JUST_TURNED:
        w = metrics["weeks_since_rs_cross"]
        if w is None or w > RS_TURN_LOOKBACK_WEEKS:
            return False
    if REQUIRE_ABOVE_30MA and not metrics["above_30ma"]:
        return False
    if REQUIRE_MA_NOT_FALLING and metrics["ma_slope"] == "down":
        return False
    if REQUIRE_VOLUME_SPIKE and not metrics["vol_spike_recent"]:
        return False
    if REQUIRE_STOCK_QUIET:
        # [v2] Unknown prior-year return is EXCLUDED, not waved through. A stock with
        # under a year of history cannot demonstrate it was ignored, by definition.
        p_ = metrics.get("prior_1y_return")
        if p_ is None or p_ > STOCK_MAX_PRIOR_1Y_RET:
            return False
    if REQUIRE_LIQUIDITY_MIN:
        if metrics["last_close"] is None or metrics["last_close"] < cfg["min_price"]:
            return False
        if metrics["avg_volume"] is None or metrics["avg_volume"] < cfg["min_avg_volume"]:
            return False
    return True


def market_regime(bench_close, cfg):
    """[v2] The index's own trailing 1-year return, and whether the gate is open.
    A property of the market, not of any stock, so it applies to the whole scan."""
    if len(bench_close) < 53:
        return None, True, "not enough benchmark history to judge - gate treated as OPEN"
    now, then = bench_close.iloc[-1], bench_close.iloc[-53]
    if pd.isna(now) or pd.isna(then) or then <= 0:
        return None, True, "benchmark data unusable - gate treated as OPEN"
    ret = (now / then - 1) * 100
    limit = cfg.get("regime_max_1y_return", 10.0)
    if ret <= limit:
        return round(float(ret), 2), True, f"index 1-year return {ret:+.1f}% (<= {limit:.0f}%) - favourable"
    return round(float(ret), 2), False, (
        f"index 1-year return {ret:+.1f}% is ABOVE the {limit:.0f}% limit - the market has already "
        f"run. Historically the worst entries: 10.2% hit rate when the index was up >25%, "
        f"versus 31.5% when it was up <5%.")


def write_tv_watchlist(out_df, market):
    """Writes a ready-to-import TradingView watchlist .txt containing CONFIRMED signals
    only (i.e. BOTH or CONFIRMED - excludes provisional/partial-week-only matches),
    since that's the trustworthy list. The dashboard builds filter-aware watchlists
    client-side if you want the provisional ones too."""
    if out_df.empty:
        return
    conf = out_df[out_df["signal"].isin(["BOTH", "CONFIRMED"])]
    if conf.empty:
        tv_symbols = []
    elif market == "IN":
        tv_symbols = ["NSE:" + s.replace(".NS", "") for s in conf["Ticker"]]
    else:
        tv_symbols = [f"{SYMBOL_EXCHANGE.get(t, 'NASDAQ')}:{t}" for t in conf["Ticker"]]
    path = f"output/v2/stage2_watchlist_v2_{market}.txt"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(",".join(tv_symbols))


# ---------------- HOVER-CHART PRICE HISTORY (weekly OHLC, per-market shards) ----------------
# Powers the dashboard's hover-preview chart, same idea as RSind's rs_ranking.py:
# a compact per-letter JSON so the browser only ever downloads the shard for the ticker
# being hovered, instead of one huge file. Adapted here for WEEKLY bars (this screener
# works in weekly bars throughout, not daily), and split into output/history_IN/ and
# output/history_US/ so a scan for one market never touches the other market's shards.
HISTORY_MIN_BARS = 35   # need a bit more than the 30-week MA length to be worth charting
HISTORY_DIR = f"output/v2/history_{MARKET}"


def _round_price(v):
    """Precision scaled to price size - keeps candle bodies visible while shrinking files."""
    if v >= 1000:
        return round(v)
    if v >= 100:
        return round(v, 1)
    return round(v, 2)


def _shard_of(ticker):
    """First letter of the ticker (as written in the results CSV, e.g. 'RELIANCE.NS' or
    'AAPL'). Tickers starting with a digit/symbol go to '_'."""
    c = ticker[0].upper()
    return c if "A" <= c <= "Z" else "_"


def _series_from(df, pos, n):
    """Lay a ticker's weekly OHLC onto the benchmark's weekly calendar (`pos`: date -> index).
    Returns (start_index, o, h, l, c) or None if there's nothing usable."""
    o = [None] * n
    h = [None] * n
    l = [None] * n
    c = [None] * n
    has_ohl = "Open" in df.columns and "High" in df.columns and "Low" in df.columns
    for ts, row in df.iterrows():
        i = pos.get(pd.Timestamp(ts).date())
        if i is None or pd.isna(row.get("Close")):
            continue
        close = _round_price(float(row["Close"]))
        c[i] = close
        o[i] = _round_price(float(row["Open"])) if has_ohl and pd.notna(row.get("Open")) else close
        h[i] = _round_price(float(row["High"])) if has_ohl and pd.notna(row.get("High")) else close
        l[i] = _round_price(float(row["Low"])) if has_ohl and pd.notna(row.get("Low")) else close

    first = None
    for i in range(n):
        if c[i] is not None:
            first = i
            break
    if first is None:
        return None
    return first, o[first:], h[first:], l[first:], c[first:]


def build_history(price_history, bench_close):
    """price_history: {ticker -> weekly OHLCV DataFrame}. bench_close: the benchmark's
    weekly Close series (same one used for the Mansfield RS calc). Returns
    (shards_by_letter, tickers_written, weeks_in_calendar)."""
    ref_dates = [pd.Timestamp(ts).date() for ts in bench_close.index]
    pos = {d: i for i, d in enumerate(ref_dates)}
    n = len(ref_dates)
    ref_epoch = [int(datetime(d.year, d.month, d.day, tzinfo=ZoneInfo("UTC")).timestamp()) for d in ref_dates]

    ref_closes = [None] * n
    for ts, val in bench_close.items():
        i = pos.get(pd.Timestamp(ts).date())
        if i is not None and pd.notna(val):
            ref_closes[i] = _round_price(float(val))
    ref_first = next((i for i, v in enumerate(ref_closes) if v is not None), None)
    ref_block = {"s": ref_first, "c": ref_closes[ref_first:]} if ref_first is not None else None

    shards = {}
    total = 0
    for ticker, df in price_history.items():
        if df is None or df.empty:
            continue
        built = _series_from(df, pos, n)
        if built is None or len(built[4]) < HISTORY_MIN_BARS:
            continue
        first, o, h, l, c = built
        shards.setdefault(_shard_of(ticker), {})[ticker] = {"s": first, "o": o, "h": h, "l": l, "c": c}
        total += 1

    files = {
        key: {"dates": ref_epoch, "refc": ref_block, "series": series}
        for key, series in shards.items()
    }
    return files, total, n


def write_history(price_history, bench_close):
    try:
        files, total, n = build_history(price_history, bench_close)
    except Exception as e:
        print(f"Warning: could not build price history for the hover chart ({e}).")
        return

    os.makedirs(HISTORY_DIR, exist_ok=True)

    # Clear shards from a previous run whose tickers are all gone (e.g. dropped below
    # the market-cap floor), so nothing stale is served to the dashboard.
    for name in os.listdir(HISTORY_DIR):
        if name.endswith(".json") and name[:-5] not in files:
            os.remove(os.path.join(HISTORY_DIR, name))

    written = 0
    for key, payload in files.items():
        path = os.path.join(HISTORY_DIR, f"{key}.json")
        with open(path, "w") as f:
            json.dump(payload, f, separators=(",", ":"))
        written += os.path.getsize(path)

    print(f"Wrote {HISTORY_DIR}/: {total} tickers x up to {n} weeks across {len(files)} shards "
          f"({written / 1e6:.1f} MB total).")
# ----------------------------------------------------------------------------------


def main():
    cfg = MARKET_CONFIG[MARKET]
    print(f"Market: {MARKET}")
    print("Active toggles:")
    print(f"  RS just turned positive (<= {RS_TURN_LOOKBACK_WEEKS}wk ago): {REQUIRE_RS_JUST_TURNED}")
    print(f"  Above 30-week MA: {REQUIRE_ABOVE_30MA}")
    print(f"  30-week MA not falling: {REQUIRE_MA_NOT_FALLING}")
    print(f"  Volume spike (last {VOL_LOOKBACK_WEEKS}wk): {REQUIRE_VOLUME_SPIKE}")
    print(f"  Liquidity filter: {REQUIRE_LIQUIDITY_MIN}")
    print(f"  Min market cap filter: {REQUIRE_MIN_MARKET_CAP} (floor: {cfg['min_market_cap']:,.0f})\n")

    print("Fetching universe symbol list...")
    symbols = get_universe_symbols(cfg)
    print(f"Got {len(symbols)} symbols.")

    print(f"Downloading benchmark ({cfg['benchmark']}) weekly data...")
    bench_df = fetch_weekly(cfg["benchmark"])
    if bench_df is None:
        raise RuntimeError(
            "Could not download benchmark data after retries. "
            "Check your internet connection, or try again in a few minutes."
        )
    bench_close = bench_df["Close"]

    regime_ret, regime_open, regime_msg = market_regime(bench_close, cfg)
    print("\n" + "=" * 72)
    print(f"[v2] MARKET REGIME: {regime_msg}")
    if not regime_open:
        if REGIME_GATE_MODE == "block":
            print("REGIME_GATE_MODE='block' - no signals will be reported this run.")
        elif REGIME_GATE_MODE == "warn":
            print("REGIME_GATE_MODE='warn' - signals still listed but tagged regime_ok=False.")
            print("The backtest says these convert at roughly a third the rate. Size down.")
    print("=" * 72 + "\n")

    tickers = [f"{s}{cfg['suffix']}" for s in symbols]
    total = len(tickers)
    results = []
    price_history = {}   # ticker -> weekly OHLCV DataFrame, for the hover-chart shards
    skipped_no_data = 0
    skipped_market_cap = 0

    print(f"\nChecking {total} stocks one at a time - this will take a while.\n")

    for idx, ticker in enumerate(tickers, start=1):
        if idx == 1 or idx % PROGRESS_EVERY == 0:
            print(f"  ...{idx}/{total} checked ({len(results)} matches so far)")

        market_cap = None
        if REQUIRE_MIN_MARKET_CAP or REQUIRE_MAX_MARKET_CAP:
            market_cap = get_market_cap(ticker)
            too_small = REQUIRE_MIN_MARKET_CAP and (market_cap is None or market_cap < cfg["min_market_cap"])
            too_big = REQUIRE_MAX_MARKET_CAP and (market_cap is not None
                                                  and market_cap > cfg.get("max_market_cap", float("inf")))
            if market_cap is None or too_small or too_big:
                skipped_market_cap += 1
                time.sleep(PAUSE_BETWEEN_REQUESTS)
                continue

        stock_df = fetch_weekly(ticker)
        if stock_df is None:
            skipped_no_data += 1
            time.sleep(PAUSE_BETWEEN_REQUESTS)
            continue

        # Keep the weekly OHLCV for the hover-chart shards - this is free, since the
        # fetch above already happened regardless of whether this ticker ends up matching.
        price_history[ticker] = stock_df

        last_week, bar_status = classify_last_bar(stock_df)

        # LIVE reading: includes the current partial week (if there is one).
        live = compute_metrics(stock_df, bench_close)
        # CONFIRMED reading: the partial week is dropped entirely, so every metric -
        # RS, the 30-week MA, and the volume spike - is computed only on finished weeks.
        if bar_status == "partial" and len(stock_df) > 1:
            confirmed = compute_metrics(stock_df.iloc[:-1], bench_close)
        else:
            confirmed = live   # nothing partial to exclude; the two readings are identical

        if live is None and confirmed is None:
            time.sleep(PAUSE_BETWEEN_REQUESTS)
            continue

        pass_live = bool(live) and passes_toggles(live, cfg)
        pass_confirmed = bool(confirmed) and passes_toggles(confirmed, cfg)

        if pass_confirmed and pass_live:
            signal = "BOTH"
        elif pass_confirmed:
            signal = "CONFIRMED"
        elif pass_live:
            signal = "PROVISIONAL"
        else:
            signal = None

        if signal and REGIME_GATE_MODE == "block" and not regime_open:
            signal = None          # [v2] gate shut and set to block - drop it

        if signal:
            tv_symbol = ("NSE:" + ticker.replace(".NS", "")) if MARKET == "IN" \
                else f"{SYMBOL_EXCHANGE.get(ticker, 'NASDAQ')}:{ticker}"
            # [v2] Listing age proxy. HISTORY_PERIOD is 3y, so materially fewer bars
            # means it has not been listed the whole time. This measures DATA
            # availability, not the official listing date.
            weeks_of_data = len(stock_df)
            results.append({
                "Ticker": ticker,
                "tv_symbol": tv_symbol,
                "signal": signal,
                "regime_ok": regime_open,
                "index_1y_return": regime_ret,
                "prior_1y_return": (live or confirmed).get("prior_1y_return"),
                "weeks_of_data": weeks_of_data,
                "recent_ipo": bool(FLAG_RECENT_IPO and weeks_of_data <= IPO_MAX_WEEKS_LISTED),
                "bar_status": bar_status,
                "last_bar_week": last_week.isoformat() if last_week else None,
                "market_cap": market_cap,
                # confirmed (finished weeks only)
                "mrs_confirmed": confirmed["mrs"] if confirmed else None,
                "cross_week_confirmed": confirmed["cross_week"] if confirmed else None,
                "above_30ma_confirmed": confirmed["above_30ma"] if confirmed else None,
                "ma_slope_confirmed": confirmed["ma_slope"] if confirmed else None,
                "vol_spike_confirmed": confirmed["vol_spike_recent"] if confirmed else None,
                # live (includes the in-progress week)
                "mrs_live": live["mrs"] if live else None,
                "cross_week_live": live["cross_week"] if live else None,
                "above_30ma_live": live["above_30ma"] if live else None,
                "ma_slope_live": live["ma_slope"] if live else None,
                "vol_spike_live": live["vol_spike_recent"] if live else None,
                # shared
                "last_close": (live or confirmed)["last_close"],
                "avg_volume": (live or confirmed)["avg_volume"],
            })

        time.sleep(PAUSE_BETWEEN_REQUESTS)

    out = pd.DataFrame(results)
    if not out.empty:
        # Sort confirmed signals first, then by strength of the confirmed reading.
        order = {"BOTH": 0, "CONFIRMED": 1, "PROVISIONAL": 2}
        out["_ord"] = out["signal"].map(order).fillna(3)
        out = out.sort_values(["_ord", "mrs_confirmed", "mrs_live"],
                              ascending=[True, False, False]).drop(columns=["_ord"])
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False)

    write_tv_watchlist(out, MARKET)
    print(f"Also wrote output/v2/stage2_watchlist_v2_{MARKET}.txt (confirmed signals only)")

    write_history(price_history, bench_close)

    print(f"\nDone. Checked {total}.")
    print(f"  Skipped (below market cap floor): {skipped_market_cap}")
    print(f"  Skipped (no data/delisted): {skipped_no_data}")
    if not out.empty:
        counts = out["signal"].value_counts().to_dict()
        print(f"\n  BOTH (confirmed + still true live): {counts.get('BOTH', 0)}")
        print(f"  CONFIRMED only: {counts.get('CONFIRMED', 0)}")
        print(f"  PROVISIONAL only (partial week - can still reverse): {counts.get('PROVISIONAL', 0)}")
        statuses = out["bar_status"].value_counts().to_dict()
        print(f"\n  Newest bar status seen: {statuses}")
    print(f"\n{len(out)} stocks matched. Saved to {OUTPUT_CSV}")
    if not out.empty:
        print(out.to_string(index=False))


if __name__ == "__main__":
    main()
