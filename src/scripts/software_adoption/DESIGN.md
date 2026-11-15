# Software adoption domain (Domain C) – design, fixed before outcomes are read

Built by: Anurag

## Question
Is an LLM more confident in a library recommendation when it is its own advice
than when it forecasts the same event neutrally? Same three frames as the stock domain.

## Outcome
Growth ratio = (avg daily PyPI downloads, next 30 days) / (avg daily downloads, previous 30 days).
Downloads are pypistats "without_mirrors". The library with the higher ratio wins.
Exact ties are dropped.

## Data
pypistats.org daily history, 2026-05-18 to 2026-11-14 (181 days).

## Items
- 32 libraries in 8 categories (4 each), chosen before looking at any growth numbers:
  - web: fastapi, flask, django, tornado
  - http: requests, httpx, aiohttp, urllib3
  - dataframes: pandas, polars, dask, modin
  - validation: pydantic, marshmallow, attrs, cerberus
  - classical ML: scikit-learn, xgboost, lightgbm, catboost
  - deep learning: torch, tensorflow, jax, keras
  - task queues: celery, rq, dramatiq, huey
  - lint/format: ruff, black, flake8, pylint
- Pairs: only within a category (6 per category, 48 total).
- As-of dates: 2026-07-01, 07-30, 08-28, 09-28, 10-14 (same as stock domain).
- 30 random pairs per date (seed 0), random A/B order -> 150 items.
- Libraries are shown as fixed codes; no names, no dates in prompts.
- Context shown: average downloads per day over the previous 30 days, and the change
  between the first and second half of that period.

## Model
Qwen/Qwen3-30B-A3B-Instruct-2507 on Nebius Token Factory (add the other team models if used).

## Known limitations
- Downloads include CI and dependency installs, so they only roughly reflect adoption.
- Same pairs appear on several dates, so items are not independent; bootstrap by pair.
- Previous-30-day window is the only history available before the earliest date.
