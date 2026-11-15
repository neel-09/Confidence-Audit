# Confidence Audit results

Reasoning effort scored: meta-models/muse-spark-open `low`, nvidia/Nemotron-3-Ultra-550b-a55b `none`.

95% intervals: bootstrap over items, 2,000 resamples. Probabilities are on a 0 to 100 scale, so gaps and overconfidence are in points. Always-50% Brier baseline: 0.250. `n` is the number of items with the frames that metric needs.

## meta-models/muse-spark-open

Items run: 25 of 25

| Metric | Value | 95% interval | n |
|---|---|---|---|
| Frame Gap (advisor minus forecaster) | -0.4 | -1.1 to +0.2 | 25 |
| Ownership gap (advisor minus third-person) | +0.0 | +0.0 to +0.0 | 25 |
| Coherence violation rate | 8.0% | 0.0% to 20.0% | 25 |
| Hit rate | 52.0% | 32.0% to 72.0% | 25 |
| Overconfidence, advisor | -2.0 | -22.0 to +18.0 | 25 |
| Overconfidence, third-person | -2.0 | -22.0 to +18.0 | 25 |
| Overconfidence, forecaster | -1.6 | -21.6 to +18.6 | 25 |
| Brier score, advisor | 0.250 | 0.250 to 0.250 | 25 |
| Brier score, third-person | 0.250 | 0.250 to 0.250 | 25 |
| Brier score, forecaster | 0.253 | 0.247 to 0.261 | 25 |
| Parse failure rate, advisor | 0.0% | 0.0% to 0.0% | 25 |
| Parse failure rate, third-person | 0.0% | 0.0% to 0.0% | 25 |
| Parse failure rate, forecaster | 0.0% | 0.0% to 0.0% | 25 |

## nvidia/Nemotron-3-Ultra-550b-a55b

Items run: 25 of 25

| Metric | Value | 95% interval | n |
|---|---|---|---|
| Frame Gap (advisor minus forecaster) | +4.8 | +3.7 to +6.1 | 25 |
| Ownership gap (advisor minus third-person) | +3.9 | +2.3 to +5.4 | 25 |
| Coherence violation rate | 0.0% | 0.0% to 0.0% | 25 |
| Hit rate | 52.0% | 32.0% to 72.0% | 25 |
| Overconfidence, advisor | +3.2 | -16.9 to +23.5 | 25 |
| Overconfidence, third-person | -0.7 | -20.6 to +19.2 | 25 |
| Overconfidence, forecaster | -1.6 | -21.4 to +18.2 | 25 |
| Brier score, advisor | 0.261 | 0.237 to 0.286 | 25 |
| Brier score, third-person | 0.245 | 0.236 to 0.255 | 25 |
| Brier score, forecaster | 0.246 | 0.240 to 0.250 | 25 |
| Parse failure rate, advisor | 0.0% | 0.0% to 0.0% | 25 |
| Parse failure rate, third-person | 0.0% | 0.0% to 0.0% | 25 |
| Parse failure rate, forecaster | 0.0% | 0.0% to 0.0% | 25 |

## Knowledge probe

Asked with real tickers and dates. A reply counts as close if any percentage it states is within 2 points of the true return (automatic text match; check probe.jsonl by hand if it matters).

| Model | Answers | Gave a % figure | Within 2 points |
|---|---|---|---|
| meta-models/muse-spark-open | 10 | 0 | 0 |
| nvidia/Nemotron-3-Ultra-550b-a55b | 10 | 0 | 0 |

## Token usage and estimated cost

Every API attempt is counted, including retries and failed parses. Cost is estimated from the logged token counts at the list prices in `run.py` (USD per 1M tokens, input / output: meta-models/muse-spark-open 1.25 / 4.25; nvidia/Nemotron-3-Ultra-550b-a55b 1.00 / 3.00). Check the Nebius console for the billed amount. Reasoning tokens are part of output tokens and are shown only when the API reports them. Spend at every reasoning effort is listed; the metrics above use only each model's current effort in `run.py`.

| Model | Run | API calls | Input tokens | Output tokens | Reasoning tokens | Output tokens per call | Est. cost (USD) |
|---|---|---|---|---|---|---|---|
| meta-models/muse-spark-open | experiment, effort default | 30 | 7,290 | 118,992 | 118,422 | 3,966 | 0.51 |
| meta-models/muse-spark-open | experiment, effort low | 75 | 18,225 | 57,380 | 55,967 | 765 | 0.27 |
| meta-models/muse-spark-open | probe, effort low | 10 | 1,776 | 3,499 | 2,266 | 350 | 0.02 |
| nvidia/Nemotron-3-Ultra-550b-a55b | experiment, effort default | 39 | 4,759 | 173,102 | 172,809 | 4,439 | 0.52 |
| nvidia/Nemotron-3-Ultra-550b-a55b | experiment, effort low | 40 | 4,910 | 152,405 | 152,045 | 3,810 | 0.46 |
| nvidia/Nemotron-3-Ultra-550b-a55b | experiment, effort minimal | 38 | 4,662 | 120,850 | 120,480 | 3,180 | 0.37 |
| nvidia/Nemotron-3-Ultra-550b-a55b | experiment, effort none | 75 | 9,238 | 909 | not reported | 12 | 0.01 |
| nvidia/Nemotron-3-Ultra-550b-a55b | probe, effort none | 10 | 577 | 449 | not reported | 45 | 0.00 |
| **Total** | | 317 | 51,437 | 627,586 | | | **2.17** |

Budget set in `run.py`: $10.00.

## Summary

```
meta-models/muse-spark-open
  Frame Gap: -0.4 points (95% interval -1.1 to +0.2, n=25); the interval includes zero.
  Ownership gap: +0.0 points (95% interval +0.0 to +0.0, n=25); the interval includes zero.
  Coherence violations: 8.0% of 25 items.
  Hit rate: 52.0% (95% interval 32.0% to 72.0%, n=25).
  Overconfidence (mean probability minus hit rate): advisor -2.0, third-person -2.0, forecaster -1.6 points.
  Brier: advisor 0.250, third-person 0.250, forecaster 0.253 (baseline 0.250).
  Parse failures: advisor 0.0%, third-person 0.0%, forecaster 0.0%.
nvidia/Nemotron-3-Ultra-550b-a55b
  Frame Gap: +4.8 points (95% interval +3.7 to +6.1, n=25); the interval excludes zero.
  Ownership gap: +3.9 points (95% interval +2.3 to +5.4, n=25); the interval excludes zero.
  Coherence violations: 0.0% of 25 items.
  Hit rate: 52.0% (95% interval 32.0% to 72.0%, n=25).
  Overconfidence (mean probability minus hit rate): advisor +3.2, third-person -0.7, forecaster -1.6 points.
  Brier: advisor 0.261, third-person 0.245, forecaster 0.246 (baseline 0.250).
  Parse failures: advisor 0.0%, third-person 0.0%, forecaster 0.0%.
Probe, meta-models/muse-spark-open: 0 of 10 answers gave a figure within 2 points of the true return (0 gave any figure).
Probe, nvidia/Nemotron-3-Ultra-550b-a55b: 0 of 10 answers gave a figure within 2 points of the true return (0 gave any figure).
Usage, meta-models/muse-spark-open: 115 API calls, 179,871 output tokens, est. $0.80.
Usage, nvidia/Nemotron-3-Ultra-550b-a55b: 202 API calls, 447,715 output tokens, est. $1.37.
Usage, total: est. $2.17 of the $10.00 budget.
Note: items share 5 dates and 30 stocks, so they are not independent; intervals on hit rate and Brier are likely too narrow.
```
