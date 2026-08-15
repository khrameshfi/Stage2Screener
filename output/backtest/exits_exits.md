# Exit-rule study — how long should a Stage 2 trade be held?

Window: last 9 years · market cap ≥ Rs 2,000 Cr · Rs 10,000 per trade · 0.3% round-trip cost.

**The number to compare rules on is _annual return on deployed capital_** — total P&L divided by the capital-time actually used. A rule that makes +40% in 20 weeks beats one making +50% in 80 weeks, because it hands the money back sooner.

## All Stage 2 signals

Every confirmed signal, no entry filter.

| Metric | fixed_52w | ma_break | ma_2closes | ma_buffer3 | ma_grace8 | ma_hardstop |
|---|---|---|---|---|---|---|
| Trades | 3,114 | 6,120 | 5,295 | 5,080 | 5,099 | 6,134 |
| Still open / truncated | 628 | 460 | 524 | 554 | 552 | 460 |
| **Mean return** | **+19.7%** | **+7.9%** | **+10.4%** | **+11.5%** | **+10.3%** | **+8.0%** |
| Median return | +6.6% | -4.7% | -5.7% | -6.5% | -4.6% | -4.8% |
| Win rate (any profit) | 56.2% | 30.0% | 32.2% | 31.8% | 37.4% | 29.9% |
| Hit rate (≥50%) | 21.1% | 7.6% | 9.7% | 10.2% | 9.7% | 7.6% |
| Monster rate (≥100%) | 8.0% | 3.8% | 4.9% | 5.2% | 4.8% | 3.8% |
| **Mean weeks held** | **52.0** | **16.5** | **21.6** | **22.7** | **22.3** | **16.4** |
| Median weeks held | 52.0 | 9.0 | 15.0 | 15.0 | 15.0 | 9.0 |
| % held beyond 52 weeks | 0.0% | 6.0% | 9.6% | 10.8% | 7.6% | 6.0% |
| Median per-trade annualised | +6.6% | -36.3% | -27.8% | -28.9% | -16.4% | -36.4% |
| **Annual return on deployed capital** | **+19.7%** | **+25.1%** | **+25.0%** | **+26.4%** | **+24.0%** | **+25.2%** |
| Total P&L (Rs) | Rs 6,146,195 | Rs 4,859,824 | Rs 5,483,694 | Rs 5,840,810 | Rs 5,241,981 | Rs 4,878,393 |
| Capital-years used | 3114.0 | 1936.6 | 2196.2 | 2213.9 | 2187.5 | 1932.0 |
| Worst trade | -97.1% | -98.2% | -98.4% | -98.2% | -96.7% | -98.1% |
| Best trade | +726.4% | +2059.3% | +2032.4% | +2057.6% | +2059.3% | +2059.3% |

## Signals passing the recipe filters

Nifty 1-yr return ≤ +10%, stock's prior 1-yr return ≤ 0%, volume ≥1.5× its 20-week average, market cap ≤ Rs 15,000 Cr.

| Metric | fixed_52w | ma_break | ma_2closes | ma_buffer3 | ma_grace8 | ma_hardstop |
|---|---|---|---|---|---|---|
| Trades | 353 | 499 | 476 | 462 | 464 | 501 |
| Still open / truncated | 238 | 142 | 154 | 168 | 161 | 142 |
| **Mean return** | **+48.0%** | **+18.4%** | **+23.1%** | **+26.6%** | **+22.7%** | **+18.3%** |
| Median return | +27.6% | -6.6% | -7.4% | -8.4% | -6.0% | -6.6% |
| Win rate (any profit) | 68.8% | 32.3% | 34.5% | 36.1% | 37.3% | 32.1% |
| Hit rate (≥50%) | 37.7% | 13.0% | 16.0% | 17.3% | 15.1% | 13.0% |
| Monster rate (≥100%) | 19.0% | 8.0% | 9.7% | 11.0% | 9.5% | 8.0% |
| **Mean weeks held** | **52.0** | **20.9** | **26.2** | **27.8** | **25.5** | **20.8** |
| Median weeks held | 52.0 | 13.0 | 17.0 | 17.5 | 16.0 | 12.0 |
| % held beyond 52 weeks | 0.0% | 11.4% | 16.2% | 17.7% | 13.1% | 11.4% |
| Median per-trade annualised | +27.6% | -31.9% | -29.8% | -27.4% | -21.2% | -32.6% |
| **Annual return on deployed capital** | **+48.0%** | **+45.6%** | **+45.9%** | **+49.8%** | **+46.2%** | **+45.7%** |
| Total P&L (Rs) | Rs 1,695,669 | Rs 915,738 | Rs 1,099,695 | Rs 1,230,949 | Rs 1,051,688 | Rs 915,314 |
| Capital-years used | 353.0 | 200.6 | 239.5 | 247.2 | 227.8 | 200.2 |
| Worst trade | -88.8% | -42.3% | -55.3% | -42.3% | -64.5% | -42.3% |
| Best trade | +659.9% | +571.7% | +578.0% | +603.8% | +592.7% | +571.7% |

## Exit rules tested

* **fixed_52w** — hold exactly 52 weeks regardless (the old baseline)
* **ma_break** — first weekly close below the 30-week MA, exit next open, no time cap
* **ma_2closes** — needs two consecutive weekly closes below the MA
* **ma_buffer3** — the close must be 3% below the MA, not merely under it
* **ma_grace8** — as ma_break, but the rule is only armed from week 8
* **ma_hardstop** — ma_break plus a hard -20% stop from entry

## Caveats

* Trades still running when the data ends are **excluded** from the completed-trade stats and counted separately. Including them at the last price would flatter the long-holding rules, since an open trade in an uptrend books an unrealised gain.
* Exits use the weekly open after the triggering close — no intra-week fills, and no assumption you could sell at the exact MA touch.
* Per-trade annualised is a **median**, not a mean: a +40% trade closed in 3 weeks annualises to an absurd number and would distort any average.
* All the standing limitations apply — survivorship bias, reconstructed market cap, adjusted prices, flat costs. Figures are optimistic.
