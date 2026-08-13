# What separated the Stage 2 winners? — attribution study (Indian market)

Sample: **3,119** scoreable Stage 2 confirmations, 2017-08-21 → 2025-08-11. Baseline hit rate (reached ≥50% in 52 weeks): **20.9%**.

Every feature is measured **at the signal week** — nothing here uses information that only existed later. Buckets with fewer than 40 trades are suppressed as noise.

## Feature attribution, ranked by how much the hit rate varies across buckets

### INDEX: % off its own 52wk high  *(spread: 38.4 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100.0, -15.0] | 40 | 57.5% | +61.0% | +36.6 pts |
| (-15.0, -8.0] | 327 | 23.2% | +14.3% | +2.3 pts |
| (-8.0, -3.0] | 1,062 | 21.8% | +5.9% | +0.8 pts |
| (-3.0, 0.01] | 1,690 | 19.1% | +3.5% | -1.9 pts |

### INDEX: 1-year return (extension)  *(spread: 24.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100, 0] | 206 | 36.9% | +31.6% | +16.0 pts |
| (0, 10] | 1,024 | 27.5% | +16.1% | +6.6 pts |
| (10, 20] | 909 | 18.5% | +5.4% | -2.4 pts |
| (20, 1000] | 980 | 12.9% | -6.0% | -8.0 pts |

### INDEX: weeks already above 40wk MA  *(spread: 20.5 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-1, 0] | 401 | 21.9% | +14.0% | +1.0 pts |
| (0, 13] | 940 | 24.8% | +11.8% | +3.9 pts |
| (13, 39] | 882 | 28.7% | +20.1% | +7.8 pts |
| (39, 78] | 832 | 8.2% | -10.3% | -12.7 pts |
| (78, 10000] | 64 | 15.6% | -5.2% | -5.3 pts |

### STOCK: % off its 52wk high  *(spread: 17.1 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100.0, -25.0] | 157 | 34.4% | +12.6% | +13.5 pts |
| (-25.0, -12.0] | 954 | 23.2% | +7.7% | +2.3 pts |
| (-12.0, -5.0] | 953 | 20.5% | +9.0% | -0.4 pts |
| (-5.0, 0.01] | 1,055 | 17.3% | +2.9% | -3.7 pts |

### STOCK: share price (Rs)  *(spread: 17.1 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0.0, 100.0] | 449 | 30.3% | +8.6% | +9.4 pts |
| (100.0, 300.0] | 818 | 24.0% | +6.8% | +3.1 pts |
| (300.0, 1000.0] | 1,148 | 19.8% | +8.0% | -1.1 pts |
| (1000.0, 1000000000.0] | 704 | 13.2% | +2.6% | -7.7 pts |

### STOCK: prior 1-year return  *(spread: 16.1 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100, 0] | 883 | 28.5% | +16.0% | +7.6 pts |
| (0, 25] | 948 | 21.3% | +11.2% | +0.4 pts |
| (25, 60] | 751 | 15.7% | -0.9% | -5.2 pts |
| (60, 10000] | 412 | 12.4% | -8.5% | -8.5 pts |

### STOCK: market cap (Rs Cr)  *(spread: 16.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0.0, 5000.0] | 1,086 | 25.8% | +2.6% | +4.9 pts |
| (5000.0, 15000.0] | 896 | 22.2% | +7.3% | +1.3 pts |
| (15000.0, 50000.0] | 678 | 18.9% | +9.2% | -2.0 pts |
| (50000.0, 1000000000.0] | 459 | 9.8% | +8.3% | -11.1 pts |

### STOCK: 30wk MA slope over 4wk  *(spread: 13.5 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100.0, 0.0] | 1,149 | 23.8% | +10.1% | +2.9 pts |
| (0.0, 1.5] | 912 | 19.2% | +4.7% | -1.7 pts |
| (1.5, 4.0] | 830 | 16.3% | +1.7% | -4.6 pts |
| (4.0, 10000.0] | 228 | 29.8% | +17.7% | +8.9 pts |

### STOCK: % above its 30wk MA  *(spread: 13.3 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100, 5] | 768 | 16.5% | +5.2% | -4.4 pts |
| (5, 12] | 945 | 17.9% | +6.5% | -3.0 pts |
| (12, 22] | 908 | 23.2% | +7.3% | +2.3 pts |
| (22, 40] | 409 | 29.8% | +12.9% | +8.9 pts |
| (40, 10000] | 89 | 25.8% | +1.8% | +4.9 pts |

### INDEX: 3-month return  *(spread: 9.5 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100, 0] | 627 | 18.7% | +6.2% | -2.2 pts |
| (0, 5] | 859 | 19.1% | +4.7% | -1.8 pts |
| (5, 10] | 912 | 18.5% | +0.1% | -2.4 pts |
| (10, 1000] | 721 | 28.0% | +15.7% | +7.1 pts |

### STOCK: volume vs 20wk avg  *(spread: 9.4 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0.0, 1.0] | 890 | 19.3% | +6.8% | -1.6 pts |
| (1.0, 1.5] | 669 | 15.7% | +7.6% | -5.2 pts |
| (1.5, 2.5] | 724 | 25.1% | +11.0% | +4.2 pts |
| (2.5, 1000.0] | 836 | 23.1% | +0.8% | +2.2 pts |

### CROWDING: signals firing same week  *(spread: 6.3 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (10, 15] | 52 | 26.9% | +17.3% | +6.0 pts |
| (15, 20] | 136 | 22.1% | +9.4% | +1.2 pts |
| (20, 1000] | 2,904 | 20.6% | +5.8% | -0.3 pts |

### STOCK: weeks already above 30wk MA  *(spread: 4.8 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0, 2] | 1,415 | 18.6% | +3.6% | -2.3 pts |
| (2, 5] | 626 | 22.7% | +4.6% | +1.8 pts |
| (5, 12] | 525 | 23.4% | +10.1% | +2.5 pts |
| (12, 10000] | 553 | 22.4% | +12.0% | +1.5 pts |

### STOCK: Mansfield RS value  *(spread: 4.4 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-100.0, 0.1] | 606 | 19.0% | +9.7% | -1.9 pts |
| (0.1, 0.3] | 894 | 19.6% | +6.3% | -1.3 pts |
| (0.3, 0.7] | 832 | 21.8% | +6.0% | +0.9 pts |
| (0.7, 1.5] | 529 | 23.4% | +4.6% | +2.5 pts |
| (1.5, 1000.0] | 258 | 22.1% | -0.2% | +1.2 pts |

### STOCK: % above its 52wk low  *(spread: 4.4 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0, 25] | 496 | 21.6% | +15.7% | +0.7 pts |
| (25, 50] | 1,440 | 19.3% | +5.3% | -1.6 pts |
| (50, 90] | 791 | 22.0% | +0.2% | +1.1 pts |
| (90, 10000] | 392 | 23.7% | +7.1% | +2.8 pts |

### INDEX: above 40-week MA at signal  *(spread: 1.1 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| False | 401 | 21.9% | +14.0% | +1.0 pts |
| True | 2,718 | 20.8% | +4.8% | -0.2 pts |

## Confound check — which features survive controlling for the year?

Regime dominates this strategy, so any feature that happens to correlate with calendar time will look predictive in the pooled tables above. Each year is split at its own median for that feature; a real edge should stay positive in most years.

| Feature | Mean within-year edge | Years positive | Verdict |
|---|---:|---:|---|
| idx_52wk_ret | +7.6 pts | 8/9 | **survives** |
| price | +7.4 pts | 7/9 | **survives** |
| mcap_cr | +6.5 pts | 7/9 | **survives** |
| idx_weeks_above_40wma | +6.3 pts | 7/9 | **survives** |
| vol_surge_x | +3.9 pts | 6/9 | confounded / inconsistent |
| breadth | +3.7 pts | 7/9 | **survives** |
| idx_13wk_ret | +2.7 pts | 4/9 | confounded / inconsistent |
| mrs | +1.8 pts | 5/9 | confounded / inconsistent |
| ma30_slope_pct | -0.7 pts | 3/9 | confounded / inconsistent |
| weeks_above_ma30 | -1.7 pts | 3/9 | confounded / inconsistent |
| idx_off_52wk_high | -2.8 pts | 3/9 | confounded / inconsistent |
| pct_off_52wk_high | -3.6 pts | 2/9 | confounded / inconsistent |
| prior_52wk_ret | -3.6 pts | 4/9 | confounded / inconsistent |
| pct_above_ma30 | -4.2 pts | 3/9 | confounded / inconsistent |

Only features marked *survives* belong in the entry checklist. A feature that flips sign year to year is riding the regime, not predicting it.

## The stacked filter — an enhanced entry checklist

Each row adds one condition on top of the ones above it.

| Filter applied | Signals left | Hit rate | Median return |
|---|---:|---:|---:|
| All Stage 2 confirmations | 3,119 | **20.9%** | +6.6% |
| + index above its 40wk MA | 2,718 | **20.8%** | +4.8% |
| + index within 8% of its 52wk high | 2,663 | **20.0%** | +4.0% |
| + stock's 30wk MA rising | 1,860 | **19.4%** | +4.5% |
| + not a crowded signal week | 41 | **4.9%** | +0.2% |

Rules, stated precisely:

* **Index above its 40-week MA** at the signal week (the weekly equivalent of a 200-DMA regime filter).
* **Index within 8% of its own 52-week high** — an uptrend, not a bear-market rally.
* **Stock's 30-week MA rising** over the prior 4 weeks (Weinstein's own requirement — the MA must not still be falling).
* **Fewer than ~18 Stage 2 signals the same week** — included only if it survived the confound check.

## Split-half validation (is this an edge, or curve-fitting?)

The stack above is derived from the whole window, so it is guaranteed to look good on the whole window. What matters is whether it holds in each half *independently*. If the second half collapses, the rules are fitted to noise.

| Half | Window | All signals | Baseline hit | Filtered signals | Filtered hit |
|---|---|---:|---:|---:|---:|
| first half | 2017-08-21 to 2022-08-29 | 1,561 | 18.6% | 30 | **0.0%** |
| second half | 2022-09-05 to 2025-08-11 | 1,558 | 23.2% | 11 | **18.2%** |

## Caveats that apply to every number above

* Inherits all of `backtest_stage2.py`'s limitations: **survivorship bias** (today's NSE list only), **reconstructed market cap**, **adjusted prices**, flat cost model.
* Feature buckets are chosen by hand, not optimised — but they were chosen *after* seeing the data, so treat exact thresholds as approximate, not precise.
* Univariate tables do not control for each other. Several of these features are correlated (a stock far above its 30wk MA usually also has high RS), so their individual lifts are **not additive** — which is exactly why the stacked funnel and split-half test above matter more than any single row.
* Fewer signals surviving a filter is not automatically good: a stack that leaves 20 trades over 9 years has no statistical weight, however pretty its hit rate.
