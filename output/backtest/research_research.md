# What separated the Stage 2 winners? — attribution study (Indian market)

Sample: **123** scoreable Stage 2 confirmations, 2017-08-21 → 2025-08-04. Baseline hit rate (reached ≥50% in 52 weeks): **20.3%**.

Every feature is measured **at the signal week** — nothing here uses information that only existed later. Buckets with fewer than 40 trades are suppressed as noise.

## Feature attribution, ranked by how much the hit rate varies across buckets

### STOCK: share price (Rs)  *(spread: 22.7 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (300.0, 1000.0] | 44 | 29.5% | +6.5% | +9.2 pts |
| (1000.0, 1000000000.0] | 44 | 6.8% | -5.4% | -13.5 pts |

### INDEX: above 40-week MA at signal  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| True | 111 | 20.7% | +3.4% | +0.4 pts |

### INDEX: % off its own 52wk high  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-3.0, 0.01] | 72 | 22.2% | -2.3% | +1.9 pts |

### INDEX: 3-month return  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0, 5] | 40 | 17.5% | -1.3% | -2.8 pts |

### INDEX: 1-year return (extension)  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (20, 1000] | 44 | 13.6% | -2.3% | -6.7 pts |

### CROWDING: signals firing same week  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0, 5] | 113 | 20.4% | +5.1% | +0.0 pts |

### STOCK: % above its 30wk MA  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (5, 12] | 42 | 19.0% | +6.8% | -1.3 pts |

### STOCK: % off its 52wk high  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (-5.0, 0.01] | 54 | 14.8% | -2.3% | -5.5 pts |

### STOCK: % above its 52wk low  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (25, 50] | 56 | 19.6% | +3.0% | -0.7 pts |

### STOCK: volume vs 20wk avg  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0.0, 1.0] | 41 | 22.0% | +7.8% | +1.6 pts |

### STOCK: weeks already above 30wk MA  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (0, 2] | 56 | 12.5% | +3.0% | -7.8 pts |

### STOCK: market cap (Rs Cr)  *(spread: 0.0 pts)*

| Bucket | Trades | Hit rate | Median return | vs baseline |
|---|---:|---:|---:|---:|
| (15000.0, 50000.0] | 48 | 16.7% | +7.7% | -3.7 pts |

## The stacked filter — an enhanced entry checklist

Each row adds one condition on top of the ones above it.

| Filter applied | Signals left | Hit rate | Median return |
|---|---:|---:|---:|
| All Stage 2 confirmations | 123 | **20.3%** | +5.1% |
| + index above its 40wk MA | 111 | **20.7%** | +3.4% |
| + index within 8% of its 52wk high | 105 | **20.0%** | +3.4% |
| + stock's 30wk MA rising | 77 | **20.8%** | -2.3% |

Rules, stated precisely:

* **Index above its 40-week MA** at the signal week (the weekly equivalent of a 200-DMA regime filter).
* **Index within 8% of its own 52-week high** — an uptrend, not a bear-market rally.
* **Stock's 30-week MA rising** over the prior 4 weeks (Weinstein's own requirement — the MA must not still be falling).

## Split-half validation (is this an edge, or curve-fitting?)

The stack above is derived from the whole window, so it is guaranteed to look good on the whole window. What matters is whether it holds in each half *independently*. If the second half collapses, the rules are fitted to noise.

| Half | Window | All signals | Baseline hit | Filtered signals | Filtered hit |
|---|---|---:|---:|---:|---:|
| first half | 2017-08-21 to 2022-10-03 | 62 | 19.4% | 38 | **18.4%** |
| second half | 2022-10-10 to 2025-08-04 | 61 | 21.3% | 39 | **23.1%** |

## Caveats that apply to every number above

* Inherits all of `backtest_stage2.py`'s limitations: **survivorship bias** (today's NSE list only), **reconstructed market cap**, **adjusted prices**, flat cost model.
* Feature buckets are chosen by hand, not optimised — but they were chosen *after* seeing the data, so treat exact thresholds as approximate, not precise.
* Univariate tables do not control for each other. Several of these features are correlated (a stock far above its 30wk MA usually also has high RS), so their individual lifts are **not additive** — which is exactly why the stacked funnel and split-half test above matter more than any single row.
* Fewer signals surviving a filter is not automatically good: a stack that leaves 20 trades over 9 years has no statistical weight, however pretty its hit rate.
