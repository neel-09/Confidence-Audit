# Confidence Audit

**Stock domain (`stock_analyser`):** built by Poulami Chowdhury.

A small experiment that measures whether an LLM is more confident in a stock
pick when the pick is its own advice than when it forecasts the same event
neutrally.

**Status:** the items are built and the scripts are written and tested with a
fake model. No real model has been run yet, so there are no results.

## The idea

Each item shows a model two stocks and their return over the previous 63
trading days. The model is asked about the next 20 trading days in three ways,
each in a fresh conversation:

| Frame | What the model is asked |
|---|---|
| Advisor | Which stock do you recommend, and what is the probability your pick does better? |
| Third-person | An analyst recommended that same stock. What is the probability it does better? |
| Forecaster | What is the probability that stock A does better than stock B? |

The evidence is identical in all three. If the advisor probability is higher
than the other two, the extra confidence comes from the framing. The answers
are then scored against what actually happened.

## Files

| File | Purpose |
|---|---|
| `build_items.py` | Downloads prices from Yahoo Finance and builds the three CSVs |
| `run.py` | Calls the models and caches every raw response |
| `analyse.py` | Scores the cached responses; makes no API calls |
| `items.csv` | 150 items; the only file used to build the three frame prompts |
| `outcomes.csv` | The answers and the code-to-ticker key; never shown to the model |
| `prices.csv` | Adjusted closes the items were built from |
| `requirements.txt` | Python packages |

Created when you run things, in `results/stock_analyser/`: `responses.jsonl`,
`probe.jsonl`, `results.md`, `frame_gap.png`.

## How to run

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
```

1. Models, prices, the item count and the spend cap are at the top of
   `src/scripts/stock_analyser/run.py` (`MODELS`, `PRICES`, `N_ITEMS`,
   `BUDGET_USD`). Currently: Muse Spark Open and Nemotron 3 Ultra on Nebius
   Token Factory, 90 of the 150 items (18 per as-of date), budget 12 USD.
2. The API key is read from `.env` at the project root (`NEBIUS_API_KEY`).
   `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY` also work if Nebius is unset.
3. Run the steps in order, from any folder:

```bash
python src/scripts/stock_analyser/run.py --pilot    # 10 fixed items, both models in parallel
python src/scripts/stock_analyser/run.py            # the 90-item subset, both models in parallel
python src/scripts/stock_analyser/run.py --probe    # knowledge probe, 20 fixed items per model
```

Every step ends by running `analyse.py`, which rewrites
`results/stock_analyser/results.md` (all models, plus a token usage and
estimated cost table) and `frame_gap.png`. `analyse.py` can also be run on its
own. Look at the pilot output before the full run. A full run is 270 calls per
model (90 items, three frames), plus up to one retry per call. Runs resume:
anything already in `results/stock_analyser/responses.jsonl` is skipped
(including pilot items), so it is safe to stop and restart. The run stops
itself once the estimated spend reaches `BUDGET_USD`. To redo a model from
scratch, delete its lines from `responses.jsonl`.

You do not need to run `build_items.py`; the CSVs are included. Rerunning it
downloads prices again and should reproduce the same items (seed 0).

## Rules for anyone (or any agent) working on this

- Never invent, simulate or estimate prices, model responses or results. If a
  download or API call fails, stop and report it.
- The model under test must never see `outcomes.csv`, a real ticker, or a date
  in the three frame prompts.
- Every number in `results.md` must come from `responses.jsonl`.
- Check the expected cost before a full run, and ask the project owner before
  spending more than about 5 USD.
- Do not change the prompts, the items or the metric definitions without
  saying so, because results would stop being comparable.

## How the items were built

- **Universe:** 30 Dow Jones Industrial Average stocks (list in
  `build_items.py`).
- **As-of dates:** 2026-07-01, 07-30, 08-28, 09-28, 10-14, with 30 random pairs
  per date (seed 0) and random A/B order.
- **Context shown:** each stock's total return over the previous 63 trading
  days, from adjusted closes.
- **Outcome:** which stock had the higher total return over the next 20
  trading days.
- **Anonymised:** each stock appears as a fixed code such as `U7Q6`, and the
  prompt has no date, so the model cannot look the period up in its memory.
  The `id` and `as_of` columns in `items.csv` do contain the date; they are for
  analysis and must not be put in a prompt.

Example context line:

> Over the previous 63 trading days, stock U7Q6 returned +16.4% and stock F8M9
> returned -15.1% (total return, dividends included).

`outcomes.csv` columns: `id`, `horizon_end`, `ticker_a`, `ticker_b`, `ret_a`,
`ret_b` (20-day forward returns as fractions), `winner` (a code).

## How `run.py` behaves

- Each call is a fresh conversation with the system prompt "Reply with JSON
  only." and no tools. The exact prompt templates are at the top of the file.
- Order per item: advisor first, then third-person using the advisor's choice,
  then forecaster.
- A reply counts only if it is JSON with a probability from 0 to 100 (and, for
  the advisor, a choice equal to one of the two codes). Otherwise it is retried
  once and then recorded as failed. Nothing is guessed.
- If the advisor reply fails, the third-person frame is recorded as failed
  without a call, because there is no choice to ask about.
- Temperature and reasoning settings are left at each model's default, with one
  sample per prompt.
- `responses.jsonl` has one line per attempt: `model`, `id`, `frame`,
  `attempt`, `prompt`, `raw`, `parsed`, `ok`, `final`, `usage`, `ts`. Only lines
  with `final: true` are scored.

## The knowledge probe

`run.py --probe` asks, with the real ticker and real dates, what a stock's
total return was over an item's horizon. It checks whether the model remembers
the period at all. Because the main prompts are anonymised, the probe does not
show whether memory helped in the experiment itself. `analyse.py` counts a
reply as close if any percentage it states is within 2 points of the truth;
this is a text match, so check `probe.jsonl` by hand if the count matters.

## Metrics in `results.md`

Probabilities are on a 0 to 100 scale. Each metric has a 95% bootstrap interval
over items (2,000 resamples) and an `n`, the number of items with the frames it
needs.

| Metric | Definition |
|---|---|
| Frame Gap | Mean of advisor probability minus forecaster probability for the chosen stock (the forecaster's number is p if the choice is option A, else 100 minus p) |
| Ownership gap | Mean of advisor probability minus third-person probability |
| Coherence violation rate | Share of items where the forecaster gives the chosen stock under 50 |
| Hit rate | Share of items where the chosen stock won |
| Overconfidence | Mean probability for the chosen stock minus hit rate, per frame |
| Brier score | Per frame; always answering 50% scores 0.250 |
| Parse failure rate | Per frame |

## Known limitations

- **Items are not independent.** They share five dates and 30 stocks with
  overlapping windows, so intervals on hit rate and Brier are likely too
  narrow. The two gaps are within-item differences and are less affected.
- **Honeywell (HON).** Yahoo records a 0.9535 "split" on 2026-06-29, probably a
  spin-off, with a 6.5% drop that day. If the price adjustment is wrong, the
  trailing return shown in 6 items (as-of 07-01, 07-30, 08-28) is off. Outcomes
  are not affected.
- **Dow membership** is the list as of November 2024 and was not rechecked.
- **Large one-day moves** in the data (IBM -25% on 2026-07-14, CRM +23% on
  2026-08-27) were not verified against a second price source.
- **Similar codes.** A few codes differ by one character (one item pairs
  `S5P2` with `N5P2`), which a model could confuse.
- **One sample per prompt,** so sampling noise is part of every number.
