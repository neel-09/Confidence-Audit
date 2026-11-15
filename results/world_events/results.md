# Confidence Audit results

Reasoning effort scored: meta-models/muse-spark-open `low`, nvidia/Nemotron-3-Ultra-550b-a55b `none`.

Items: 60; resolved Yes: 21 (35%). A model that always recommended PLAN_NO would be right 65% of the time; always stating the base rate scores Brier 0.227.

95% intervals: bootstrap over items, 2,000 resamples. Probabilities are on a 0 to 100 scale, so gaps and overconfidence are in points. Always-50% Brier baseline: 0.250. `n` is the number of items with the frames that metric needs.

## meta-models/muse-spark-open

Items run: 60 of 60

| Metric | Value | 95% interval | n |
|---|---|---|---|
| Frame Gap (advisor minus forecaster) | -1.1 | -3.4 to +1.3 | 60 |
| Ownership gap (advisor minus third-person) | -1.7 | -4.2 to +0.7 | 60 |
| Coherence violation rate | 5.0% | 0.0% to 11.7% | 60 |
| Hit rate | 68.3% | 56.7% to 80.0% | 60 |
| Overconfidence, advisor | +9.8 | -0.8 to +21.9 | 60 |
| Overconfidence, third-person | +11.4 | -0.1 to +23.3 | 60 |
| Overconfidence, forecaster | +10.9 | -0.0 to +22.2 | 60 |
| Brier score, advisor | 0.214 | 0.149 to 0.284 | 60 |
| Brier score, third-person | 0.219 | 0.149 to 0.294 | 60 |
| Brier score, forecaster | 0.207 | 0.140 to 0.274 | 60 |
| Parse failure rate, advisor | 0.0% | 0.0% to 0.0% | 60 |
| Parse failure rate, third-person | 0.0% | 0.0% to 0.0% | 60 |
| Parse failure rate, forecaster | 0.0% | 0.0% to 0.0% | 60 |

## nvidia/Nemotron-3-Ultra-550b-a55b

Items run: 60 of 60

| Metric | Value | 95% interval | n |
|---|---|---|---|
| Frame Gap (advisor minus forecaster) | +7.8 | +2.2 to +13.9 | 60 |
| Ownership gap (advisor minus third-person) | +3.5 | -0.5 to +7.9 | 60 |
| Coherence violation rate | 20.0% | 10.0% to 30.0% | 60 |
| Hit rate | 68.3% | 56.7% to 80.0% | 60 |
| Overconfidence, advisor | +13.2 | +1.0 to +25.0 | 60 |
| Overconfidence, third-person | +9.7 | -2.5 to +21.3 | 60 |
| Overconfidence, forecaster | +5.5 | -6.9 to +18.2 | 60 |
| Brier score, advisor | 0.227 | 0.157 to 0.309 | 60 |
| Brier score, third-person | 0.230 | 0.151 to 0.310 | 60 |
| Brier score, forecaster | 0.259 | 0.174 to 0.348 | 60 |
| Parse failure rate, advisor | 0.0% | 0.0% to 0.0% | 60 |
| Parse failure rate, third-person | 0.0% | 0.0% to 0.0% | 60 |
| Parse failure rate, forecaster | 0.0% | 0.0% to 0.0% | 60 |

## Knowledge probe

Asked how each question resolved, with no date or context. A reply counts as a claim if it starts with YES or NO; a correct claim matches the real resolution. Most questions resolved No (see the top of this file), so always answering NO would already be right most of the time; compare correct claims with that before reading them as memory (automatic match; check probe.jsonl by hand if it matters).

| Model | Answers | Claimed YES or NO | Claims correct |
|---|---|---|---|
| meta-models/muse-spark-open | 10 | 1 | 1 |
| nvidia/Nemotron-3-Ultra-550b-a55b | 10 | 0 | 0 |

## Comparison: the prediction market itself

Brier score of the market probability at the as-of date (never shown to the models), on the same items, for the frame-free question "will it resolve Yes?". Compare with each model's forecaster Brier above.

| Model's items | n | Market Brier |
|---|---|---|
| meta-models/muse-spark-open | 60 | 0.131 |
| nvidia/Nemotron-3-Ultra-550b-a55b | 60 | 0.131 |

## Token usage and estimated cost

Every API attempt is counted, including retries and failed parses. Cost is estimated from the logged token counts at the list prices in `run.py` (USD per 1M tokens, input / output: meta-models/muse-spark-open 1.25 / 4.25; nvidia/Nemotron-3-Ultra-550b-a55b 1.00 / 3.00). Check the Nebius console for the billed amount. Reasoning tokens are part of output tokens and are shown only when the API reports them. Spend at every reasoning effort is listed; the metrics above use only each model's current effort in `run.py`.

| Model | Run | API calls | Input tokens | Output tokens | Reasoning tokens | Output tokens per call | Est. cost (USD) |
|---|---|---|---|---|---|---|---|
| meta-models/muse-spark-open | experiment, effort low | 180 | 76,626 | 95,420 | 92,147 | 530 | 0.50 |
| meta-models/muse-spark-open | probe, effort low | 10 | 1,835 | 5,020 | 4,584 | 502 | 0.02 |
| nvidia/Nemotron-3-Ultra-550b-a55b | experiment, effort none | 180 | 58,621 | 2,217 | not reported | 12 | 0.07 |
| nvidia/Nemotron-3-Ultra-550b-a55b | probe, effort none | 10 | 579 | 261 | not reported | 26 | 0.00 |
| **Total** | | 380 | 137,661 | 102,918 | | | **0.59** |

Budget set in `run.py`: $10.00.

## Summary

```
meta-models/muse-spark-open
  Frame Gap: -1.1 points (95% interval -3.4 to +1.3, n=60); the interval includes zero.
  Ownership gap: -1.7 points (95% interval -4.2 to +0.7, n=60); the interval includes zero.
  Coherence violations: 5.0% of 60 items.
  Hit rate: 68.3% (95% interval 56.7% to 80.0%, n=60).
  Overconfidence (mean probability minus hit rate): advisor +9.8, third-person +11.4, forecaster +10.9 points.
  Brier: advisor 0.214, third-person 0.219, forecaster 0.207 (baseline 0.250).
  Parse failures: advisor 0.0%, third-person 0.0%, forecaster 0.0%.
nvidia/Nemotron-3-Ultra-550b-a55b
  Frame Gap: +7.8 points (95% interval +2.2 to +13.9, n=60); the interval excludes zero.
  Ownership gap: +3.5 points (95% interval -0.5 to +7.9, n=60); the interval includes zero.
  Coherence violations: 20.0% of 60 items.
  Hit rate: 68.3% (95% interval 56.7% to 80.0%, n=60).
  Overconfidence (mean probability minus hit rate): advisor +13.2, third-person +9.7, forecaster +5.5 points.
  Brier: advisor 0.227, third-person 0.230, forecaster 0.259 (baseline 0.250).
  Parse failures: advisor 0.0%, third-person 0.0%, forecaster 0.0%.
Probe, meta-models/muse-spark-open: 1 of 10 answers claimed a resolution; 1 of those were correct.
Probe, nvidia/Nemotron-3-Ultra-550b-a55b: 0 of 10 answers claimed a resolution; 0 of those were correct.
Usage, meta-models/muse-spark-open: 190 API calls, 100,440 output tokens, est. $0.52.
Usage, nvidia/Nemotron-3-Ultra-550b-a55b: 190 API calls, 2,478 output tokens, est. $0.07.
Usage, total: est. $0.59 of the $10.00 budget.
Note: only questions resolved by the dataset commit are included, so early-resolving questions are over-represented (see README).
```
