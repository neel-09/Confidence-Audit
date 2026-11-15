# Confidence Audit

A small experiment that measures whether an LLM is more confident in a
recommendation when it is its own advice than when it forecasts the same event
neutrally, and checks that confidence against what actually happened.

| Domain | Folder names | Built by | Status |
|---|---|---|---|
| Stock picks | `stock_analyser` | Poulami Chowdhury | 25-item run done (`results/stock_analyser/results.md`) |
| World events (ForecastBench questions as decisions) | `world_events` | Abhroneel Chakraborty | 60-item run done (`results/world_events/results.md`) |

All domains share the models, the three frames, the metrics and one spend cap
(`BUDGET_USD`, counted across every log under `results/`). The sections up to
"World events domain" describe the stock domain.

## Results so far

Models: Muse Spark Open (Meta) at low reasoning effort and Nemotron 3 Ultra
(NVIDIA) with reasoning off, both via Nebius Token Factory. Probabilities are on
a 0 to 100 scale; intervals are 95% bootstrap intervals over items.

| | Stocks (n = 25) | World events (n = 60) |
|---|---|---|
| Nemotron Frame Gap (advisor minus forecaster) | +4.8 (+3.7 to +6.1) | +7.8 (+2.2 to +13.9) |
| Nemotron ownership gap (advisor minus third-person) | +3.9 (+2.3 to +5.4) | +3.5 (-0.5 to +7.9) |
| Muse Frame Gap | -0.4 (-1.1 to +0.2) | -1.1 (-3.4 to +1.3) |
| Muse ownership gap | +0.0 (+0.0 to +0.0) | -1.7 (-4.2 to +0.7) |
| Hit rate, both models | 52% | 68.3% (always recommending PLAN_NO: 65%) |

- **Nemotron** is more confident in its own advice than in its own neutral
  forecast of the same event, in both domains, and the extra confidence is not
  backed by accuracy (stock hit rate 52%; world-events advisor overconfidence
  +13.2 points against +5.5 as forecaster). In world events it recommended a
  plan its own forecaster called the less likely one on 12 of 60 items (20%).
- **Muse** shows no frame effect in either domain. On stocks it answered 50% to
  almost everything; on world events it is overconfident by about 10 points in
  all three frames alike.
- **Neither model is close to the market.** On the world-events items, the
  prediction market's own probability at the as-of date scores Brier 0.131,
  against 0.207 (Muse) and 0.259 (Nemotron) for the models' forecasts.
- **Knowledge probes** found no sign that either model remembers the outcomes.
- **Caveat:** the two models ran at different reasoning settings, chosen to
  keep cost and failed answers down, so differences between the models may
  partly reflect those settings. Each model's gap compares its own answers at
  one setting, so the gaps themselves are not affected.
- **Spend so far:** about $2.76 estimated, of the $10 cap.


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
uv venv
uv pip install -r requirements.txt   # or: python -m venv .venv, then pip install
```

1. Models, prices, reasoning effort, the item count and the spend cap are at
   the top of `src/scripts/stock_analyser/run.py` (`MODELS`, `PRICES`,
   `REASONING_EFFORT`, `N_ITEMS`, `BUDGET_USD`). Currently: Muse Spark Open
   (`low`) and Nemotron 3 Ultra (`none`) on Nebius Token Factory, 25 of the 150
   items (5 per as-of date), and a 10 USD cap shared by all domains. Reasoning
   effort was lowered after pilots at the default setting cost about 4,000
   output tokens per answer and Nemotron ran out of tokens on about half its
   calls; every response records the effort it was made at, and only the
   current setting is scored.
2. The API key is read from `.env` at the project root (`NEBIUS_API_KEY`).
   `OPENROUTER_API_KEY` or `ANTHROPIC_API_KEY` also work if Nebius is unset.
3. Run the steps in order, from any folder:

```bash
python src/scripts/stock_analyser/run.py --pilot    # 10 fixed items, both models in parallel
python src/scripts/stock_analyser/run.py            # the 25-item subset, both models in parallel
python src/scripts/stock_analyser/run.py --probe    # knowledge probe, 10 fixed items per model
```

Every step ends by running `analyse.py`, which rewrites
`results/stock_analyser/results.md` (all models, plus a token usage and
estimated cost table) and `frame_gap.png`. `analyse.py` can also be run on its
own. Look at the pilot output before the full run. A run is 75 calls per
model (25 items, three frames), plus up to one retry per call; raising
`N_ITEMS` (up to 150) reuses every cached call. Runs resume:
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

---

## World events domain

**Developed by Abhroneel Chakraborty.** Scripts in `src/scripts/world_events/`,
data in `src/data/world_events/`, outputs in `results/world_events/`.

### The idea

Each item is a real forecasting question from a prediction market (Metaculus,
Manifold or Polymarket) that resolved Yes or No in 2026, after the knowledge
cutoff of both models. The question becomes a decision between two plans:

- `PLAN_YES`: prepare as if the question resolves Yes
- `PLAN_NO`: prepare as if the question resolves No

The same three frames as the stock domain are asked, each in a fresh conversation:

| Frame | What the model is asked |
|---|---|
| Advisor | My organisation must commit today to one plan. Which do you recommend, and what is the probability your plan turns out to be the right one? |
| Third-person | An analyst recommended that same plan. What is the probability it turns out right? |
| Forecaster | What is the probability that this question resolves Yes (or No, chosen at random per item)? |

A plan is "right" if it matches how the question resolved. Unlike the stock
domain, models have some real skill here, so confidence can be checked against
accuracy and against the prediction market itself.

### Data source

All questions and resolutions come from the official ForecastBench datasets
(github.com/forecastingresearch/forecastbench-datasets, pinned to commit
`fe2a07344bf835fc44356c8f497a7542e8a58f94`), licensed CC BY-SA 4.0. The
derived files in `src/data/world_events/` are shared under the same licence.
Cite: Karger et al., *ForecastBench: A Dynamic Benchmark of AI Forecasting
Capabilities*, ICLR 2025.

### Files

| File | Purpose |
|---|---|
| `src/scripts/world_events/build_items.py` | Downloads the ForecastBench question and resolution sets and builds the CSVs below |
| `src/scripts/world_events/run.py` | Calls the models and caches every raw response (same settings and spend cap as the stock domain) |
| `src/scripts/world_events/analyse.py` | Scores the cached responses; makes no API calls |
| `src/data/world_events/items.csv` | 90 items (30 per source); the only file used to build the frame prompts |
| `src/data/world_events/outcomes.csv` | Resolution, resolution date, the market probability at the as-of date, URL; never shown to the model |
| `src/data/world_events/pool.csv` | All 1,134 eligible questions, for reference |

`build_items.py` keeps a download cache in `src/data/world_events/_download_cache/`
(about 36 MB, git-ignored). You do not need to rerun it; the CSVs are included.

### How the items were built

- **Question sets:** every ForecastBench LLM question set from 2026-02-01 to
  2026-10-25 (one every 14 days) and its resolution set.
- **Eligible:** Metaculus, Manifold and Polymarket questions first seen with a
  freeze date on or after 2026-01-18, whose final resolution is exactly Yes or
  No and dated after that freeze date. Infer was left out (only 5 resolved).
  Result: 1,134 questions.
- **As-of date:** the question's freeze date, shown to the model as "Today is ...".
- **Selection:** 30 per source, drawn with seed 0 before outcomes were looked at.
  `run.py` uses the first 20 per source (`N_ITEMS = 60`); raising `N_ITEMS`
  reuses cached calls.
- **Shown to the model:** the as-of date, the question and up to 1,200
  characters of the market's background text. Not shown: the market probability,
  the URL, the resolution.
- **Plan order and forecaster wording** are randomised per item (seed 1), so
  neither plan is always listed first and the forecaster is asked about Yes on
  some items and No on others.
- Of the 90 items, 28 (31%) resolved Yes.

### How to run

```powershell
python src\scripts\world_events\run.py --pilot   # 10 items, both models in parallel
python src\scripts\world_events\run.py           # the 60-item subset
python src\scripts\world_events\run.py --probe   # knowledge probe, 10 items per model
```

Each step rewrites `results/world_events/results.md`. Besides the stock-domain
metrics it reports the base rate (always recommending `PLAN_NO` is right 69% of
the time on the full 90) and the Brier score of the prediction market itself at
the as-of date, as a strong comparison for the forecaster frame.

### Results (60-item run)

Full table: `results/world_events/results.md`. Base rate: 21 of the 60 items
(35%) resolved Yes.

| Metric | Muse Spark Open (low) | Nemotron 3 Ultra (none) |
|---|---|---|
| Frame Gap | -1.1 (-3.4 to +1.3) | +7.8 (+2.2 to +13.9) |
| Ownership gap | -1.7 (-4.2 to +0.7) | +3.5 (-0.5 to +7.9) |
| Coherence violations | 5.0% (3 of 60) | 20.0% (12 of 60) |
| Recommended PLAN_NO | 54 of 60 | 46 of 60 |
| Hit rate | 68.3% | 68.3% |
| Overconfidence: advisor / third-person / forecaster | +9.8 / +11.4 / +10.9 | +13.2 / +9.7 / +5.5 |
| Brier: advisor / third-person / forecaster | 0.214 / 0.219 / 0.207 | 0.227 / 0.230 / 0.259 |
| Parse failures | 0% | 0% |

Comparisons: always 50% scores Brier 0.250; always stating the base rate 0.227;
the prediction market at the as-of date 0.131. Asked about Yes, the models'
forecasts averaged about 25%; asked about No, about 74%, so the randomised
wording did not create a Yes/No bias. Knowledge probe: Muse claimed 1 resolution
of 10 (correct), Nemotron none. Estimated cost of this domain: $0.59.

### Knowledge probe

Asks each model, with the question text only, how the question resolved
(YES, NO or UNKNOWN). Because most questions resolved No, a model that always
says NO looks right most of the time; compare correct claims with the base rate
before treating them as memory.

### Known limitations (world events)

- **Resolved-only selection.** Only questions resolved by the dataset commit
  are included. Questions that resolve early are over-represented, and early
  resolution is not independent of the outcome (for example, "Will X happen
  before 2027?" resolves early only if X happens, or if the deadline is near).
  This is the selection problem described by Paleka et al. (2026), "Pitfalls in
  Evaluating Language Model Forecasters".
- **Knowledge cutoffs are not guaranteed.** Every as-of date (2026-01-22 or
  later) is after the stated cutoffs (Muse Spark Open 2026-01-04, Nemotron 3
  Ultra 2025-09), but stated cutoffs can be wrong and the questions name real
  people and events. The probe reduces, not removes, this risk.
- **Generic decision framing.** "Prepare as if Yes/No" turns a forecast into a
  decision without real costs or payoffs, so "the right plan" just means
  "matches the resolution". Real decisions have asymmetric costs.
- **Market questions are noisy.** Some Manifold questions are user-created and
  self-referential, and resolutions are taken from ForecastBench as published;
  a few may be wrong or disputed.
- **Equal numbers per source** (not proportional: Polymarket is 66% of the pool),
  so results are not representative of the whole pool.
- **Truncated background** (1,200 characters) may cut details a human would use.
- **Forecaster wording varies** (Yes on some items, No on others) to control
  for a bias toward saying Yes; this adds a small difference between items.
- **Model settings** are the same as the stock domain (Muse Spark Open at low
  reasoning effort, Nemotron 3 Ultra with reasoning off), one sample per prompt;
  compare each model's own gaps, not raw confidence levels across models.
- **Topics include politics, conflicts and elections.** Prompts are neutral and
  the questions are taken as published; no view on any outcome is implied.
