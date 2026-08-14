# What separated the Stage 2 winners? — attribution study (Indian market)

Sample: **3,116** scoreable Stage 2 confirmations, 2017-08-21 → 2025-08-11. Baseline hit rate (reached ≥50% in 52 weeks): **21.1%**.

Every feature is measured **at the signal week** — nothing here uses information that only existed later. Buckets with fewer than 40 trades are suppressed as noise.

## Feature attribution, ranked by how much the hit rate varies across buckets

### INDEX: % off its own 52wk high  *(spread: 35.5 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100.0, -15.0] | 40 | 55.0% | +60.0% | +33.9 pts |
| (-15.0, -8.0] | 327 | 23.2% | +14.7% | +2.2 pts |
| (-8.0, -3.0] | 1,064 | 21.6% | +5.4% | +0.5 pts |
| (-3.0, 0.01] | 1,685 | 19.5% | +3.6% | -1.6 pts |

### INDEX: 1-year return (extension)  *(spread: 23.6 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100, 0] | 205 | 36.6% | +31.3% | +15.5 pts |
| (0, 10] | 1,028 | 27.8% | +16.1% | +6.7 pts |
| (10, 20] | 903 | 18.7% | +5.7% | -2.4 pts |
| (20, 1000] | 980 | 13.0% | -6.1% | -8.1 pts |

### INDEX: weeks already above 40wk MA  *(spread: 21.4 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-1, 0] | 402 | 21.6% | +14.1% | +0.6 pts |
| (0, 13] | 935 | 25.1% | +11.7% | +4.0 pts |
| (13, 39] | 883 | 29.3% | +20.2% | +8.2 pts |
| (39, 78] | 832 | 7.9% | -10.6% | -13.2 pts |
| (78, 10000] | 64 | 15.6% | -5.2% | -5.5 pts |

### STOCK: weeks of listed history at signal  *(spread: 17.9 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0, 52] | 133 | 23.3% | +1.0% | +2.2 pts |
| (52, 104] | 122 | 30.3% | +17.8% | +9.2 pts |
| (104, 260] | 962 | 12.4% | -5.2% | -8.7 pts |
| (260, 10000] | 1,899 | 24.7% | +12.8% | +3.7 pts |

### STOCK: share price (Rs)  *(spread: 17.5 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0.0, 100.0] | 445 | 30.6% | +7.3% | +9.5 pts |
| (100.0, 300.0] | 819 | 24.3% | +6.8% | +3.2 pts |
| (300.0, 1000.0] | 1,149 | 20.0% | +7.9% | -1.1 pts |
| (1000.0, 1000000000.0] | 703 | 13.1% | +2.5% | -8.0 pts |

### STOCK: market cap (Rs Cr)  *(spread: 16.9 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0.0, 5000.0] | 1,088 | 26.4% | +2.8% | +5.3 pts |
| (5000.0, 15000.0] | 892 | 22.0% | +7.3% | +0.9 pts |
| (15000.0, 50000.0] | 682 | 19.2% | +9.3% | -1.9 pts |
| (50000.0, 1000000000.0] | 454 | 9.5% | +8.0% | -11.6 pts |

### STOCK: % off its 52wk high  *(spread: 16.8 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100.0, -25.0] | 153 | 34.6% | +14.0% | +13.6 pts |
| (-25.0, -12.0] | 958 | 23.0% | +7.8% | +1.9 pts |
| (-12.0, -5.0] | 949 | 20.7% | +8.6% | -0.4 pts |
| (-5.0, 0.01] | 1,056 | 17.8% | +2.9% | -3.3 pts |

### STOCK: prior 1-year return  *(spread: 16.4 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100, 0] | 879 | 28.7% | +16.1% | +7.6 pts |
| (0, 25] | 945 | 21.9% | +11.2% | +0.8 pts |
| (25, 60] | 751 | 15.6% | -0.9% | -5.5 pts |
| (60, 10000] | 415 | 12.3% | -8.9% | -8.8 pts |

### STOCK: 30wk MA slope over 4wk  *(spread: 14.8 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100.0, 0.0] | 1,149 | 23.9% | +10.2% | +2.8 pts |
| (0.0, 1.5] | 906 | 19.4% | +4.7% | -1.7 pts |
| (1.5, 4.0] | 829 | 16.2% | +1.6% | -4.9 pts |
| (4.0, 10000.0] | 232 | 31.0% | +17.7% | +9.9 pts |

### STOCK: % above its 30wk MA  *(spread: 14.5 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100, 5] | 771 | 16.3% | +5.0% | -4.7 pts |
| (5, 12] | 938 | 17.9% | +6.6% | -3.2 pts |
| (12, 22] | 903 | 23.6% | +8.4% | +2.5 pts |
| (22, 40] | 416 | 30.8% | +10.0% | +9.7 pts |
| (40, 10000] | 88 | 25.0% | -1.5% | +3.9 pts |

### CANDLE: gap from prior week's close (%)  *(spread: 12.3 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100.0, -1.0] | 190 | 16.3% | +3.2% | -4.8 pts |
| (-1.0, 0.5] | 1,629 | 19.6% | +5.9% | -1.5 pts |
| (0.5, 3.0] | 1,143 | 23.0% | +6.9% | +1.9 pts |
| (3.0, 1000.0] | 154 | 28.6% | +14.0% | +7.5 pts |

### INDEX: 3-month return  *(spread: 9.7 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100, 0] | 629 | 18.4% | +5.9% | -2.6 pts |
| (0, 5] | 861 | 19.5% | +4.8% | -1.6 pts |
| (5, 10] | 901 | 18.8% | +0.4% | -2.3 pts |
| (10, 1000] | 725 | 28.1% | +14.9% | +7.1 pts |

### STOCK: volume vs 20wk avg  *(spread: 9.5 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0.0, 1.0] | 891 | 19.5% | +7.3% | -1.6 pts |
| (1.0, 1.5] | 667 | 15.6% | +7.1% | -5.5 pts |
| (1.5, 2.5] | 720 | 25.1% | +11.2% | +4.1 pts |
| (2.5, 1000.0] | 838 | 23.6% | +0.8% | +2.5 pts |

### CANDLE: range vs prior 20wk avg range  *(spread: 7.9 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0.0, 0.8] | 391 | 18.4% | +6.2% | -2.7 pts |
| (0.8, 1.2] | 744 | 20.4% | +9.1% | -0.7 pts |
| (1.2, 1.8] | 920 | 20.9% | +6.2% | -0.2 pts |
| (1.8, 2.5] | 571 | 26.3% | +10.8% | +5.2 pts |
| (2.5, 100.0] | 489 | 18.6% | -3.6% | -2.5 pts |

### CANDLE: signal-week high-low range (%)  *(spread: 7.6 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0, 6] | 480 | 16.9% | +11.7% | -4.2 pts |
| (6, 10] | 866 | 20.8% | +7.9% | -0.3 pts |
| (10, 16] | 947 | 22.8% | +6.3% | +1.7 pts |
| (16, 25] | 549 | 24.4% | +5.0% | +3.3 pts |
| (25, 1000] | 273 | 16.8% | -8.9% | -4.2 pts |

### CANDLE: close position in week's range (1=at high)  *(spread: 6.2 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0.0, 0.4] | 237 | 21.5% | +7.4% | +0.4 pts |
| (0.4, 0.65] | 675 | 23.9% | +12.0% | +2.8 pts |
| (0.65, 0.85] | 1,188 | 22.3% | +5.7% | +1.2 pts |
| (0.85, 1.001] | 1,015 | 17.7% | +3.5% | -3.4 pts |

### STOCK: weeks already above 30wk MA  *(spread: 4.8 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0, 2] | 1,410 | 18.7% | +3.7% | -2.4 pts |
| (2, 5] | 630 | 23.0% | +4.6% | +1.9 pts |
| (5, 12] | 524 | 23.5% | +9.2% | +2.4 pts |
| (12, 10000] | 552 | 22.8% | +12.0% | +1.7 pts |

### CANDLE: body as share of range  *(spread: 4.7 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0.0, 0.25] | 358 | 19.8% | +11.2% | -1.3 pts |
| (0.25, 0.45] | 525 | 23.6% | +9.9% | +2.5 pts |
| (0.45, 0.7] | 1,151 | 22.4% | +6.9% | +1.3 pts |
| (0.7, 1.001] | 1,082 | 18.9% | +1.8% | -2.2 pts |

### STOCK: Mansfield RS value  *(spread: 4.6 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100.0, 0.1] | 604 | 19.0% | +10.2% | -2.0 pts |
| (0.1, 0.3] | 891 | 19.6% | +6.5% | -1.4 pts |
| (0.3, 0.7] | 833 | 21.8% | +6.7% | +0.8 pts |
| (0.7, 1.5] | 521 | 23.4% | +4.6% | +2.3 pts |
| (1.5, 1000.0] | 267 | 23.6% | -1.8% | +2.5 pts |

### STOCK: % above its 52wk low  *(spread: 4.5 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0, 25] | 496 | 21.6% | +15.8% | +0.5 pts |
| (25, 50] | 1,436 | 19.6% | +5.6% | -1.4 pts |
| (50, 90] | 789 | 21.9% | +0.1% | +0.8 pts |
| (90, 10000] | 395 | 24.1% | +6.5% | +3.0 pts |

### CANDLE: signal-week body (close vs open, %)  *(spread: 3.4 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100, 0] | 189 | 19.0% | +5.4% | -2.0 pts |
| (0, 3] | 565 | 20.0% | +11.5% | -1.1 pts |
| (3, 8] | 1,170 | 22.2% | +8.5% | +1.1 pts |
| (8, 15] | 775 | 21.9% | +5.3% | +0.9 pts |
| (15, 1000] | 416 | 18.8% | -6.2% | -2.3 pts |

### CROWDING: signals firing same week  *(spread: 2.5 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (10, 15] | 56 | 23.2% | +15.7% | +2.1 pts |
| (15, 20] | 133 | 23.3% | +12.0% | +2.2 pts |
| (20, 1000] | 2,900 | 20.8% | +5.8% | -0.3 pts |

### CANDLE: signal week closed up  *(spread: 2.2 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| False | 189 | 19.0% | +5.4% | -2.0 pts |
| True | 2,927 | 21.2% | +6.7% | +0.1 pts |

### INDEX: above 40-week MA at signal  *(spread: 0.6 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| False | 402 | 21.6% | +14.1% | +0.6 pts |
| True | 2,714 | 21.0% | +4.8% | -0.1 pts |

## Confound check — which features survive controlling for the year?

Regime dominates this strategy, so any feature that happens to correlate with calendar time will look predictive in the pooled tables above. Each year is split at its own median for that feature; a real edge should stay positive in most years.

| Feature | Mean within-year edge | Years positive | Verdict |
|---|---:|---:|---|
| idx_52wk_ret | +7.9 pts | 8/9 | **survives** |
| price | +7.1 pts | 7/9 | **survives** |
| mcap_cr | +6.6 pts | 7/9 | **survives** |
| idx_weeks_above_40wma | +6.5 pts | 7/9 | **survives** |
| vol_surge_x | +4.2 pts | 6/9 | confounded / inconsistent |
| breadth | +3.7 pts | 7/9 | **survives** |
| idx_13wk_ret | +2.9 pts | 3/9 | confounded / inconsistent |
| mrs | +2.2 pts | 5/9 | confounded / inconsistent |
| ma30_slope_pct | -0.6 pts | 3/9 | confounded / inconsistent |
| weeks_above_ma30 | -1.8 pts | 3/9 | confounded / inconsistent |
| idx_off_52wk_high | -2.7 pts | 4/9 | confounded / inconsistent |
| pct_off_52wk_high | -3.0 pts | 2/9 | confounded / inconsistent |
| prior_52wk_ret | -3.6 pts | 3/9 | confounded / inconsistent |
| pct_above_ma30 | -4.8 pts | 3/9 | confounded / inconsistent |

Only features marked *survives* belong in the entry checklist. A feature that flips sign year to year is riding the regime, not predicting it.

## The stacked filter — an enhanced entry checklist

Each row adds one condition on top of the ones above it.

| Filter applied | Signals left | Hit rate | Median return |
|---|---:|---:|---:|
| All Stage 2 confirmations | 3,116 | **21.1%** | +6.5% |
| + index above its 40wk MA | 2,714 | **21.0%** | +4.8% |
| + index within 8% of its 52wk high | 2,659 | **20.2%** | +4.0% |
| + stock's 30wk MA rising | 1,856 | **19.6%** | +4.4% |
| + not a crowded signal week | 45 | **8.9%** | +0.5% |

Rules, stated precisely:

* **Index above its 40-week MA** at the signal week (the weekly equivalent of a 200-DMA regime filter).
* **Index within 8% of its own 52-week high** — an uptrend, not a bear-market rally.
* **Stock's 30-week MA rising** over the prior 4 weeks (Weinstein's own requirement — the MA must not still be falling).
* **Fewer than ~18 Stage 2 signals the same week** — included only if it survived the confound check.

## Split-half validation (is this an edge, or curve-fitting?)

The stack above is derived from the whole window, so it is guaranteed to look good on the whole window. What matters is whether it holds in each half *independently*. If the second half collapses, the rules are fitted to noise.

| Half | Window | All signals | Baseline hit | Filtered signals | Filtered hit |
|---|---|---:|---:|---:|---:|
| first half | 2017-08-21 to 2022-08-29 | 1,560 | 18.8% | 30 | **0.0%** |
| second half | 2022-09-05 to 2025-08-11 | 1,556 | 23.4% | 15 | **26.7%** |

## Caveats that apply to every number above

* Inherits all of `backtest_stage2.py`'s limitations: **survivorship bias** (today's NSE list only), **reconstructed market cap**, **adjusted prices**, flat cost model.
* Feature buckets are chosen by hand, not optimised — but they were chosen *after* seeing the data, so treat exact thresholds as approximate, not precise.
* Univariate tables do not control for each other. Several of these features are correlated (a stock far above its 30wk MA usually also has high RS), so their individual lifts are **not additive** — which is exactly why the stacked funnel and split-half test above matter more than any single row.
* Fewer signals surviving a filter is not automatically good: a stack that leaves 20 trades over 9 years has no statistical weight, however pretty its hit rate.
