# Confidence Audit

**When Forecasts Become Advice — Auditing LLM Confidence Across Three Domains**

**Paper:** [Download the paper (PDF)](When_Forecasts_Become_Advice.pdf)

We test whether a language model reports different probabilities when it gives
advice, evaluates an analyst's recommendation, or forecasts the same event
neutrally. We score those probabilities against recorded outcomes in stocks,
world events and Python package download growth.

The completed main evaluation contains **235 task items and 960 scored
responses**, plus 150 additional software forecasts in a post-hoc wording check.

| Domain | Built by | Evaluation | Full results |
|---|---|---|---|
| Stock picks | Poulami Chowdhury | 25 items, Muse and Nemotron | [Stock results](results/stock_analyser/results.md) |
| World events | Abhroneel Chakraborty | 60 items, Muse and Nemotron | [World-event results](results/world_events/results.md) |
| Python package download growth | Anurag Chakraborty | 150 items, Qwen3 | [Software results](results/software_adaption/results.md) |

All three authors are affiliated with Heritage Institute of Technology, Kolkata.
The software output directory is spelled `software_adaption` in this repository.

## Main findings

Probabilities use a 0–100 scale. Gaps below are in percentage points, with
descriptive 95% bootstrap intervals in parentheses.

| Domain and model | Advisor minus forecaster | Advisor minus third person | Recommendation hit rate |
|---|---|---|---|
| Stocks · Muse | -0.4 (-1.1 to +0.2) | 0.0 (0.0 to 0.0) | 52.0% (13/25) |
| Stocks · Nemotron | +4.8 (+3.7 to +6.1) | +3.9 (+2.3 to +5.4) | 52.0% (13/25) |
| World events · Muse | -1.1 (-3.4 to +1.3) | -1.7 (-4.2 to +0.7) | 68.3% (41/60) |
| World events · Nemotron | +7.8 (+2.2 to +13.9) | +3.5 (-0.5 to +7.9) | 68.3% (41/60) |
| Software · Qwen3 | +14.8 (+11.2 to +18.2) | +5.6 (+4.3 to +7.2) | 64.0% (96/150) |

- **Nemotron gave higher probabilities under the advisor prompt in both domains.**
  Its advisor Brier score was worse than its neutral forecast on stocks
  (0.261 versus 0.246) and better on world events (0.227 versus 0.259).
  Lower Brier scores indicate lower mean squared probability error.
- **Muse showed small average differences across prompts.** It returned exactly
  50% on 69 of 75 stock prompts and on none of 180 world-event prompts.
  Its stock response pattern warrants follow-up on evidence strength and
  elicitation wording.
- **Recommendation hit rates were close to simple baselines.** Stock momentum
  got 13/25, always choosing No on world events got 39/60, and software download
  momentum got 99/150.
- **Qwen's forecasts were sensitive to wording.** Original and mirrored
  probabilities differed by 21.8 points per item on average. Averaging them
  reduced the advisor–forecaster gap from 14.8 to 11.6 points and disagreement
  from 34.7% to 23.3%. The order of packages in the evidence stayed fixed.
- **Recall probes give limited evidence.** Muse explicitly supplied one correct
  world-event resolution in ten probes; Nemotron supplied none. Neither model
  supplied a numerical return in the stock probes. Withholding an answer does
  not establish that the model lacked relevant information.

## How to interpret the comparisons

The advisor selects an option and scores it. The third-person prompt presents
that choice as an analyst's recommendation. The forecaster estimates the
probability of a designated option, which is complemented when needed to score
the advisor's pick. Each call uses a fresh conversation.

The labels **Frame Gap** and **ownership gap** in the saved outputs mean
advisor minus forecaster and advisor minus third-person probability, respectively.
These descriptive comparisons combine selection, attribution and wording changes;
they do not isolate a causal ownership effect.

Stocks and world events used Muse Spark Open at low reasoning effort and
Nemotron 3 Ultra with reasoning off. Software ran separately in a Colab notebook
with Qwen3-30B-A3B-Instruct-2507 at its defaults and separately written prompts.
All models were accessed through Nebius Token Factory. Each comparison is
conditional on its model, task, wording and settings.

The stock and world-event intervals resample items. Software intervals resample
47 package pairs. Shared dates, entities and overlapping windows can make these
intervals too narrow, including intervals for paired gaps. World events were
selected from retrospectively resolved questions, and one final response per
frame leaves generation variability unresolved. The market's world-event Brier
score of 0.131 is a descriptive comparator with a different information set.

## Reproduce scores from saved responses

Run from the repository root with [uv](https://docs.astral.sh/uv/):

```bash
uv venv
uv pip install -r requirements.txt
uv run python src/scripts/stock_analyser/analyse.py
uv run python src/scripts/world_events/analyse.py
```

These analysis scripts read the committed response logs and outcome tables and
rewrite the corresponding results summaries and figures without making model
API calls. The committed CSVs preserve the inputs used for the recorded runs.
Software results and the mirrored-forecast check are documented in
[the software results](results/software_adaption/results.md).

For fresh model calls, use the domain instructions below. The stock and
world-event runners share an estimated spend guard for their configured models.
The separate Qwen notebook run is outside that guard. Cost estimates depend on
the configured prices and logged usage.

## Detailed methods and reproduction

<details>
<summary>Stocks — inputs, prompts, model runs and limitations</summary>

### Stock task and prompts

Each item shows a model two stocks and their return over the previous 63
trading days. The model is asked about the next 20 trading days in three ways,
each in a fresh conversation:

| Frame | What the model is asked |
|---|---|
| Advisor | Which stock do you recommend, and what is the probability your pick does better? |
| Third-person | An analyst recommended that same stock. What is the probability it does better? |
| Forecaster | What is the probability that stock A does better than stock B? |

The evidence is identical in all three. A higher advisor probability is a descriptive difference between prompts.
The advisor both selects and evaluates an option, while the other prompts
evaluate a supplied option. These comparisons therefore combine selection,
attribution and wording changes. The answers
are then scored against what actually happened.

### Stock files

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

### Stock model runs

```bash
uv venv
uv pip install -r requirements.txt
```

1. Models, prices, reasoning effort, the item count and the spend cap are at
   the top of `src/scripts/stock_analyser/run.py` (`MODELS`, `PRICES`,
   `REASONING_EFFORT`, `N_ITEMS`, `BUDGET_USD`). Currently: Muse Spark Open
   (`low`) and Nemotron 3 Ultra (`none`) on Nebius Token Factory, 25 of the 150
   items (5 per as-of date), and a 10 USD estimated cap for the configured stock and world-event models. Reasoning
   effort was lowered after pilots at the default setting cost about 4,000
   output tokens per answer and Nemotron ran out of tokens on about half its
   calls; every response records the effort it was made at, and only the
   current setting is scored.
2. The API key is read from `.env` at the project root (`NEBIUS_API_KEY`).
   The runner also has OpenRouter and Anthropic routes, but using them requires
   compatible model identifiers and prices in the configuration. The recorded
   evaluation used Nebius.
3. Run these commands from the repository root:

```bash
uv run python src/scripts/stock_analyser/run.py --pilot    # 10 fixed items, both models in parallel
uv run python src/scripts/stock_analyser/run.py            # the 25-item subset, both models in parallel
uv run python src/scripts/stock_analyser/run.py --probe    # knowledge probe, 10 fixed items per model
```

Every step ends by running `analyse.py`, which rewrites
`results/stock_analyser/results.md` (all models, plus a token usage and
estimated cost table) and `frame_gap.png`. `analyse.py` can also be run on its
own. Look at the pilot output before the full run. A run is 75 calls per
model (25 items, three frames), plus up to one retry per call; raising
`N_ITEMS` (up to 150) reuses every cached call. Runs resume:
anything already in `results/stock_analyser/responses.jsonl` is skipped
(including pilot items), so it is safe to stop and restart. The spend guard stops launching new calls when estimated spend reaches
`BUDGET_USD`; calls already running may still finish and add cost. For a fresh evaluation, preserve or archive the published response logs first
and use a separate results location so the original run remains reproducible.

You do not need to run `build_items.py`; the CSVs are included. Rerunning it
downloads prices again using seed 0. Vendor revisions can change adjusted
prices, so use the committed CSVs to reproduce the recorded evaluation.

## Rules for anyone (or any agent) working on this

- Never invent, simulate or estimate prices, model responses or results. If a
  download or API call fails, stop and report it.
- The model under test must never see `outcomes.csv`, a real ticker, or a date
  in the three frame prompts.
- Reported metrics must be traceable to the saved response logs and the
  corresponding inputs, outcomes and analysis settings.
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
  prompt has no date. This reduces direct identification of the period but
  does not establish the absence of outcome leakage.
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
- Temperature is left at the provider default. Reasoning effort is explicitly
  set to `low` for Muse and `none` for Nemotron. One final response is scored
  per item and frame.
- `responses.jsonl` has one line per attempt: `model`, `id`, `frame`,
  `attempt`, `prompt`, `raw`, `parsed`, `ok`, `final`, `usage`, `ts`. Only lines
  with `final: true` are scored.

## The knowledge probe

`run.py --probe` asks, with the real ticker and real dates, what a stock's
total return was over an item's horizon. It checks whether the model will explicitly report a return
for the period. Because the main prompts are anonymised, the probe does not
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
  overlapping windows, so item-bootstrap intervals, including those for paired confidence gaps,
  may be too narrow. Pairing alone does not remove dependence across items.
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

</details>

<details>
<summary>World events — data source, sampling, results and limitations</summary>

## World events domain

**Developed by Abhroneel Chakraborty.** Scripts in `src/scripts/world_events/`,
data in `src/data/world_events/`, outputs in `results/world_events/`.

### The idea

Each item is a real forecasting question from a prediction market (Metaculus,
Manifold or Polymarket) that resolved Yes or No in 2026, after both models' stated knowledge
cutoffs. The question becomes a decision between two plans:

- `PLAN_YES`: prepare as if the question resolves Yes
- `PLAN_NO`: prepare as if the question resolves No

The same three frames as the stock domain are asked, each in a fresh conversation:

| Frame | What the model is asked |
|---|---|
| Advisor | My organisation must commit today to one plan. Which do you recommend, and what is the probability your plan turns out to be the right one? |
| Third-person | An analyst recommended that same plan. What is the probability it turns out right? |
| Forecaster | What is the probability that this question resolves Yes (or No, chosen at random per item)? |

A plan is "right" if it matches how the question resolved. Both models chose the winning plan on 41 of 60 scored items, compared with
39 of 60 for always choosing No. Probability accuracy is also compared with
the market probabilities, which had a different information set.

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
uv run python src\scripts\world_events\run.py --pilot   # 10 items, both models in parallel
uv run python src\scripts\world_events\run.py           # the 60-item subset
uv run python src\scripts\world_events\run.py --probe   # knowledge probe, 10 items per model
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
forecasts averaged about 25%; asked about No, about 74%, which gives similar aggregate estimates after complementing the No forecasts.
Because different items received each wording, this comparison does not isolate
the effect of wording on individual items. Knowledge probe: Muse claimed 1 resolution
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
  people and events. The probe is a limited check of explicit recall and cannot rule out leakage.
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

</details>

<details>
<summary>Software — package data, mirrored forecasts and limitations</summary>

## Software adoption domain

**Developed by Anurag Chakraborty.** Design in `src/scripts/software_adoption/`, data in
`data/software_adoption/`, outputs in `results/software_adaption/` (the folder
name is spelled that way in the repo).

### The idea

Each item shows a model two Python packages and their PyPI download history
over the previous 30 days. The model is asked about the next 30 days in the
same three frames as the stock domain, each in a fresh conversation:

| Frame | What the model is asked |
|---|---|
| Advisor | Which package do you recommend, and what is the probability it has the greater growth? |
| Third-person | An analyst recommended that same package. What is the probability it has greater growth? |
| Forecaster | What is the probability that package A has greater growth than package B? |

Growth means the average downloads per day over the next 30 days compared with
the average over the previous 30 days.

### Files

| File | Purpose |
|---|---|
| `src/scripts/software_adoption/DESIGN.md` | The design, committed before any outcome data was read |
| `data/software_adoption/raw/` | Daily PyPI downloads (`without_mirrors`) for the 32 libraries, from pypistats.org |
| `data/software_adoption/items.csv` | 150 items; the only file used to build the frame prompts |
| `data/software_adoption/outcomes.csv` | The answers and the code-to-library key; never shown to the model |
| `data/software_adoption/codes.csv` | The library-to-code key |
| `results/software_adaption/responses.jsonl` | Every cached model response |
| `results/software_adaption/results.md` | The scored results |

### How the items were built

- **Libraries:** 32 PyPI packages in 8 categories of 4 (web frameworks, HTTP
  clients, dataframes, validation, classical ML, deep learning, task queues,
  linters and formatters), chosen before any growth numbers were looked at. The
  full list is in `DESIGN.md`.
- **Pairs:** only within a category (48 possible pairs).
- **As-of dates:** 2026-07-01, 07-30, 08-28, 09-28, 10-14 (the same as the
  stock domain), with 30 random pairs per date (seed 0) and random A/B order.
  This gives 150 items covering 47 distinct pairs.
- **Data:** pypistats daily downloads, 2026-05-18 to 2026-11-14 (181 days), the
  most history pypistats provides, so the context window is 30 days.
- **Context shown:** each package's average downloads per day over the previous
  30 days, and its change between the first and second half of that period.
- **Outcome:** which package had the higher growth ratio over the next 30 days.
  Exact ties would be dropped; there were none.
- **Anonymised:** each library appears as a fixed random 4-character code, and
  any two codes differ in at least two characters. The prompts have no library
  names and no dates.

Example context line:

> Over the previous 30 days, package FJKC averaged 1,559,260 downloads per day,
> and its daily downloads were +2.3% in the second half of that period compared
> with the first half.

`outcomes.csv` columns: `id`, `horizon_end`, `lib_a`, `lib_b`, `ratio_a`,
`ratio_b` (growth ratios), `winner` (a code).

### How the run works

- Model: `Qwen/Qwen3-30B-A3B-Instruct-2507` on Nebius Token Factory, default
  settings, one sample per prompt, system prompt "Reply with JSON only.".
- The order per item and the parsing rules follow the stock domain: advisor
  first, then third-person using the advisor's choice, then forecaster; an
  unparseable reply is retried once, then recorded as failed.
- The prompts were written separately from the stock templates, so they are
  similar but not identical.
- A pilot of 10 fixed items ran first, then all 150. All 450 replies parsed
  (150 of 150 per frame). The main run used 92,695 input and 4,784 output
  tokens.
- A post-hoc check afterwards asked the forecaster question in mirrored
  wording (probability that B beats A) for all 150 items; those replies are
  stored under the frame name `forecaster_swap`.

### Results (Qwen3-30B-A3B-Instruct-2507, 150 items)

Intervals are 95% bootstrap intervals resampled by library pair (47 pairs,
2,000 resamples). Full table, baselines and checks:
`results/software_adaption/results.md`.

| Metric | Value |
|---|---|
| Frame Gap | +14.8 (+11.2 to +18.2) |
| Ownership gap | +5.6 (+4.3 to +7.2) |
| Coherence violations | 34.7% (29.3 to 40.4) |
| Hit rate | 64.0% (56.9 to 70.3) |
| Overconfidence: advisor / third-person / forecaster | +10.2 / +4.6 / -4.5 |
| Brier: advisor / third-person / forecaster | 0.236 / 0.227 / 0.292 |
| Parse failures | 0% |

- Picking the package with the higher recent change gets 66.0% (59.2 to 73.0),
  similar to the model's 64.0%. Always picking A gets 49.3%.
- The advisor chose A in 54.7% of items, while A won 49.3%. The mean forecaster
  probability that A wins was 39.6.
- Mirrored-forecaster check (post-hoc): the mean probability for A was 39.0 after complementing the mirrored
  forecasts. The average preference for B persisted across wordings. The two wordings differ by 21.8 points
  on average (correlation 0.46). Averaging them gives Frame Gap +11.6 (+8.7 to
  +14.8) and coherence violations 23.3% (17.7 to 29.5).
- The Frame Gap is positive on all five as-of dates (7.9 to 29.4 points, 30
  items per date).

### Known limitations (software adoption)

- **One model.** It is not one of the two models used in the other domains, so
  nothing here compares models.
- **Items are not independent.** The 150 items share 47 pairs and 5 dates with
  overlapping windows. Intervals are resampled by pair but may still be too
  narrow.
- **Forecaster position lean.** The forecaster frame favours package B (the
  package described second) however the question is worded. The mirrored check
  swaps the question but not the order of the context, so it does not remove
  the lean. This sensitivity complicates interpretation of the Frame Gap and
  disagreement rate. The advisor–third-person comparison also changes whether
  the model selects or evaluates a supplied option.
- **The mirrored check was post-hoc.** It was added after the main results
  were seen.
- **Hit rate matches a simple rule.** The model's 64% is close to following
  recent momentum (66%), so the results do not show skill beyond that.
- **Downloads are a noisy proxy for adoption.** They include CI runs,
  dependency installs and one-off spikes; `without_mirrors` removes only part
  of that.
- **Shorter windows than the stock domain:** 30 days of context and a 30-day
  horizon, because pypistats keeps only 181 days.
- **No knowledge probe** was run for this domain. The anonymised prompts reduce direct identification of packages and
  dates, but the effectiveness of this measure was not tested.
- **One sample per prompt,** so sampling noise is part of every number.

</details>
