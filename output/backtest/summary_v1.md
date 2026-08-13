# Stage 2 backtest — weekly Mansfield RS + 30-week MA (Indian market)

Window **2015-01-12 → 2026-08-10** (signal window: last 9 years) — universe **2404** NSE names, market cap floor Rs 2,000 Cr (reconstructed, see limitations below)

Position size: Rs 10,000 per trade, unlimited concurrent positions. Round-trip cost: 0.3%, deducted from every trade.

## Did Stage 2 confirmations reach +50% within a year?

| | Loose | Strict |
|---|---:|---:|
| Scoreable signals | 3,119 | 2,571 |
| Too recent to score yet | 632 | 535 |
| Dropped, no future data (likely delisted) | 1 | 1 |
| **Hit rate: reached ≥50% in 52wk** | **21.0%** | **21.6%** |
| Average 1yr return | +19.6% | +19.6% |
| Median 1yr return | +6.6% | +7.1% |
| Best 1yr return | +726.4% | +689.2% |
| Worst 1yr return | -97.1% | -97.1% |

For comparison — Nifty 50 itself, every rolling 52-week window over the same period: hit rate 5.7% (avg +12.4%)

## Return distribution (fixed 1-year hold)

| Bucket | Loose | Strict |
|---|---:|---:|
| <-25% | 571 | 475 |
| -25% to 0% | 801 | 666 |
| 0-25% | 669 | 531 |
| 25-50% | 426 | 346 |
| 50-100% | 405 | 340 |
| >100% | 247 | 213 |

## If you'd used Weinstein's own exit (sell on a weekly close below the 30-week MA)

| | Loose | Strict |
|---|---:|---:|
| MA-exit hit rate (≥50%) | 9.7% | 10.8% |
| MA-exit average return | +9.4% | +10.6% |
| MA-exit median weeks held | 14 | 16 |
| % stopped out before week 52 | 92.6% | 91.9% |
| Of the eventual 1yr winners — avg MA-exit capture | +58.0% | +61.8% |
| Of the eventual 1yr winners — % exited early anyway | 68.2% | 66.5% |

## Read this before acting on the numbers

* **Survivorship bias.** The universe is NSE's *current* equity list. A stock delisted, merged, or suspended during its holding period has no future price data, so its trade is dropped entirely (see "dropped, no future data" above) rather than scored as a loss. Every number here is optimistic relative to what a trader could actually have captured at the time.
* **Market cap is reconstructed** from today's implied share count (current market cap / current price) x each week's historical close. Issuance and buybacks between then and now are not modelled.
* **Adjusted prices.** Returns are correct; the absolute price levels are not what was actually on screen at the time.
* **Costs are a flat 0.3% round trip.** Real impact cost on an illiquid smallcap breakout — especially with other traders chasing the same signal — is worse.
* "Too recent to score" signals (inside the last year of data) are excluded from hit-rate stats since there's no forward-looking data yet to check them against — not dropped silently, just not counted.
* A positive hit rate on one continuous window is not proof of an edge across market regimes. Worth checking whether it holds if you split the window in half.
