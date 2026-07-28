"""
Stage 2 / Mansfield RS Screener - India (NSE) + US, combined
--------------------------------------------------------------
Screens stocks using Mansfield Relative Strength + Weinstein Stage 2 logic,
with every condition individually switchable so you can screen loosely
("just RS turning green, don't care about anything else") or strictly
("everything must line up") without touching the core logic.

Setup:
    pip3 install --upgrade yfinance pandas requests

Run:
    python3 stage2_screener.py

Output:
    stage2_screener_<MARKET>_results.csv

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
import time
import io
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
    },
    "US": {
        "benchmark": "^GSPC",
        "suffix": "",
        "universe_mode": None,        # not used for US
        "local_symbol_csv": None,     # set to your own CSV path (needs a "Symbol" column) if the NASDAQ URLs below ever fail
        "min_price": 5,               # USD - liquidity filter floor
        "min_avg_volume": 200000,     # shares/week - liquidity filter floor
        "min_market_cap": 2_000_000_000,  # $2B - a rough equivalent floor; adjust to taste
    },
}

# ---------------- STRATEGY TOGGLES (flip these freely, no code changes needed elsewhere) ----------------
REQUIRE_RS_JUST_TURNED  = True   # only stocks where Mansfield RS crossed from negative to positive recently
RS_TURN_LOOKBACK_WEEKS  = 1      # 0 = crossed this week, 1 = crossed this week OR last week, 2 = up to 2 weeks ago, etc.

REQUIRE_ABOVE_30MA      = True   # require price currently above the 30-week MA

REQUIRE_MA_NOT_FALLING  = False  # True = 30W MA must be flat or rising; False = don't check its slope at all
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

# ---------------- CORE TECHNICAL SETTINGS (rarely need changing) ----------------
MRS_LEN                = 52      # Mansfield RS smoothing length (standard weekly)
MA_LEN                 = 30      # the trend MA itself
HISTORY_PERIOD         = "3y"
PAUSE_BETWEEN_REQUESTS = 1.0     # seconds between each stock - keep this to avoid rate-limit/crash issues
RETRIES_PER_TICKER     = 2
PROGRESS_EVERY         = 25
# ----------------------------------------------------------------------------------

OUTPUT_CSV = f"output/stage2_screener_{MARKET}_results.csv"

SYMBOL_EXCHANGE = {}   # populated for US during get_universe_symbols(); symbol -> "NASDAQ"/"NYSE"/etc.


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
    """Fetch weekly Close/Volume history for ONE ticker at a time, with retries."""
    for _ in range(RETRIES_PER_TICKER):
        try:
            df = yf.Ticker(ticker).history(period=HISTORY_PERIOD, interval="1wk", auto_adjust=True)
            if df is not None and not df.empty and "Close" in df.columns:
                return df[["Close", "Volume"]].dropna()
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
    """0 = RS crossed positive this week, 1 = last week, etc. None if not currently positive."""
    if pd.isna(mrs_series.iloc[-1]) or mrs_series.iloc[-1] <= 0:
        return None
    count_positive = 0
    for i in range(1, min(max_lookback, len(mrs_series)) + 1):
        val = mrs_series.iloc[-i]
        if pd.notna(val) and val > 0:
            count_positive += 1
        else:
            break
    return count_positive - 1


def compute_metrics(stock_df, bench_close):
    """Returns a dict of every underlying metric for one stock, or None if there's not enough history."""
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

    return {
        "mrs": round(float(mrs.iloc[-1]), 2),
        "weeks_since_rs_cross": weeks_since_rs_cross(mrs),
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
    if REQUIRE_LIQUIDITY_MIN:
        if metrics["last_close"] is None or metrics["last_close"] < cfg["min_price"]:
            return False
        if metrics["avg_volume"] is None or metrics["avg_volume"] < cfg["min_avg_volume"]:
            return False
    return True


def write_tv_watchlist(out_df, market):
    """Writes a ready-to-import TradingView watchlist .txt (format: EXCHANGE:TICKER,...).
    India always uses NSE. US uses the actual NASDAQ/NYSE/AMEX/etc. exchange looked up
    per ticker (best-effort mapping from NASDAQ Trader's data - see get_universe_symbols)."""
    if out_df.empty:
        return
    if market == "IN":
        symbols = out_df["Ticker"].str.replace(".NS", "", regex=False)
        tv_symbols = ["NSE:" + s for s in symbols]
    else:
        tv_symbols = [f"{SYMBOL_EXCHANGE.get(t, 'NASDAQ')}:{t}" for t in out_df["Ticker"]]
    path = f"output/stage2_watchlist_{market}.txt"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(",".join(tv_symbols))


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

    tickers = [f"{s}{cfg['suffix']}" for s in symbols]
    total = len(tickers)
    results = []
    skipped_no_data = 0
    skipped_market_cap = 0

    print(f"\nChecking {total} stocks one at a time - this will take a while.\n")

    for idx, ticker in enumerate(tickers, start=1):
        if idx == 1 or idx % PROGRESS_EVERY == 0:
            print(f"  ...{idx}/{total} checked ({len(results)} matches so far)")

        market_cap = None
        if REQUIRE_MIN_MARKET_CAP:
            market_cap = get_market_cap(ticker)
            if market_cap is None or market_cap < cfg["min_market_cap"]:
                skipped_market_cap += 1
                time.sleep(PAUSE_BETWEEN_REQUESTS)
                continue

        stock_df = fetch_weekly(ticker)
        if stock_df is None:
            skipped_no_data += 1
            time.sleep(PAUSE_BETWEEN_REQUESTS)
            continue

        metrics = compute_metrics(stock_df, bench_close)
        if metrics is None:
            time.sleep(PAUSE_BETWEEN_REQUESTS)
            continue

        if passes_toggles(metrics, cfg):
            results.append({"Ticker": ticker, "market_cap": market_cap, **metrics})

        time.sleep(PAUSE_BETWEEN_REQUESTS)

    out = pd.DataFrame(results)
    if not out.empty:
        out = out.sort_values("mrs", ascending=False)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False)

    if MARKET == "IN":
        write_tv_watchlist(out, "IN")
        print("Also wrote output/stage2_watchlist_IN.txt (ready to import into TradingView)")
    else:
        write_tv_watchlist(out, "US")
        print("Also wrote output/stage2_watchlist_US.txt (ready to import into TradingView)")

    print(f"\nDone. Checked {total}.")
    print(f"  Skipped (below market cap floor): {skipped_market_cap}")
    print(f"  Skipped (no data/delisted): {skipped_no_data}")
    print(f"{len(out)} stocks matched your current toggle settings. Saved to {OUTPUT_CSV}")
    if not out.empty:
        print(out.to_string(index=False))


if __name__ == "__main__":
    main()
