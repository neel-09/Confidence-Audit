"""Build the world-events Confidence Audit items from the official ForecastBench datasets.

  python build_items.py

Source: github.com/forecastingresearch/forecastbench-datasets (CC BY-SA 4.0), pinned to
one commit so the build is reproducible. Downloads every 2026 LLM question set and
resolution set from FIRST_SET to LAST_SET, then keeps market questions that:
  - come from Metaculus, Manifold or Polymarket (Infer has too few resolved questions),
  - first appear in a set whose freeze date is on or after MIN_FREEZE (after the
    knowledge cutoff of every model in run.py),
  - have a final resolution of exactly Yes (1) or No (0) dated after that freeze date.

Outputs (in src/data/world_events, wherever this is run from):
  pool.csv      every eligible question with its outcome and metadata (for reference)
  items.csv     id, as_of, source, option_a, option_b, context   (all the model may see)
  outcomes.csv  id, source, question, resolved_to, resolution_date, winner, crowd_p_yes, url
                (never shown to the model; crowd_p_yes is the market value at the freeze
                date, used only as a comparison baseline)

Selection is outcome-blind: a fixed number of questions per source is drawn with a fixed
seed from the eligible pool, before outcomes are joined. Nothing is estimated: if a
download fails or a field is missing, the script stops with a message.
"""
import datetime as dt
import json
import random
import sys
from pathlib import Path

import pandas as pd
import requests

COMMIT = "fe2a07344bf835fc44356c8f497a7542e8a58f94"   # forecastbench-datasets, Nov 2026
RAW = f"https://raw.githubusercontent.com/forecastingresearch/forecastbench-datasets/{COMMIT}"
FIRST_SET, LAST_SET = dt.date(2026, 2, 1), dt.date(2026, 10, 25)  # sets are 14 days apart
MIN_FREEZE = "2026-01-18"     # Muse Spark Open cutoff 2026-01-04; Nemotron 3 Ultra 2025-09
SOURCES = ["metaculus", "manifold", "polymarket"]
PER_SOURCE = 30               # 90 items in items.csv; run.py uses a nested subset
MAX_BACKGROUND = 1200         # characters of background text shown to the model
SEED = 0
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "world_events"
CACHE = DATA_DIR / "_download_cache"


def fail(msg):
    sys.exit(f"STOPPED: {msg}")


def fetch(path):
    """Download one dataset file (cached on disk) and return the parsed JSON."""
    local = CACHE / path.replace("/", "__")
    if not local.exists():
        r = requests.get(f"{RAW}/{path}", timeout=120)
        if r.status_code != 200:
            fail(f"download failed ({r.status_code}): {RAW}/{path}")
        local.write_bytes(r.content)
    return json.loads(local.read_text(encoding="utf-8"))


def set_dates():
    d = FIRST_SET
    while d <= LAST_SET:
        yield d.isoformat()
        d += dt.timedelta(days=14)


def context_for(q, as_of):
    bg = (q.get("background") or "").strip()
    if len(bg) > MAX_BACKGROUND:
        bg = bg[:MAX_BACKGROUND].rsplit(" ", 1)[0] + " [...]"
    parts = [f"Today is {as_of}.", f"Question: {q['question'].strip()}"]
    if bg and bg.upper() != "N/A":
        parts.append(f"Background: {bg}")
    return "\n".join(parts)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    first, resolutions = {}, {}
    for d in set_dates():
        qset = fetch(f"datasets/question_sets/{d}-llm.json")
        for q in qset["questions"]:
            if q["source"] in SOURCES and q["id"] not in first \
                    and q["freeze_datetime"][:10] >= MIN_FREEZE:
                first[q["id"]] = (d, q)
        rset = fetch(f"datasets/resolution_sets/{d}_resolution_set.json")
        for r in rset["resolutions"]:
            if r["source"] in SOURCES and r.get("resolved"):
                resolutions.setdefault(r["id"], set()).add((r["resolved_to"], r["resolution_date"]))
    if not first:
        fail("no questions found; check FIRST_SET / LAST_SET and the commit")

    pool = []
    for qid, (set_date, q) in first.items():
        res = resolutions.get(qid)
        if not res:
            continue  # not resolved yet
        values = {v for v, _ in res}
        if len(values) != 1:
            fail(f"question {qid} has conflicting resolutions {res}")
        value = values.pop()
        res_date = max(day for _, day in res)
        as_of = q["freeze_datetime"][:10]
        if value not in (0.0, 1.0) or res_date <= as_of:
            continue
        try:
            crowd = float(q["freeze_datetime_value"])
        except (TypeError, ValueError):
            crowd = float("nan")
        pool.append(dict(qid=qid, set_date=set_date, source=q["source"], as_of=as_of,
                         question=q["question"].strip(), resolved_to=int(value),
                         resolution_date=res_date, crowd_p_yes=crowd, url=q.get("url", ""),
                         context=context_for(q, as_of)))
    pool = pd.DataFrame(pool).sort_values(["source", "qid"]).reset_index(drop=True)

    # outcome-blind selection: shuffle each source's ids with a fixed seed, take the first ones
    rng = random.Random(SEED)
    rows = []
    for src in SOURCES:
        ids = sorted(pool.loc[pool.source == src, "qid"])
        if len(ids) < PER_SOURCE:
            fail(f"only {len(ids)} eligible {src} questions, need {PER_SOURCE}")
        rng.shuffle(ids)
        for rank, qid in enumerate(ids[:PER_SOURCE], 1):
            rows.append((src, rank, qid))

    items, outcomes = [], []
    order_rng = random.Random(SEED + 1)
    for src, rank, qid in rows:
        p = pool.set_index("qid").loc[qid]
        item_id = f"{src}_{rank:02d}"
        a, b = ("PLAN_YES", "PLAN_NO") if order_rng.random() < 0.5 else ("PLAN_NO", "PLAN_YES")
        items.append(dict(id=item_id, as_of=p.as_of, source=src, option_a=a, option_b=b,
                          context=p.context))
        outcomes.append(dict(id=item_id, source=src, qid=qid, question=p.question,
                             resolved_to=p.resolved_to, resolution_date=p.resolution_date,
                             winner="PLAN_YES" if p.resolved_to == 1 else "PLAN_NO",
                             crowd_p_yes=p.crowd_p_yes, url=p.url))

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pool.drop(columns=["context"]).to_csv(DATA_DIR / "pool.csv", index=False)
    pd.DataFrame(items).to_csv(DATA_DIR / "items.csv", index=False)
    pd.DataFrame(outcomes).to_csv(DATA_DIR / "outcomes.csv", index=False)
    out = pd.DataFrame(outcomes)
    print(f"pool.csv: {len(pool)} eligible questions "
          f"({', '.join(f'{s} {int((pool.source == s).sum())}' for s in SOURCES)})")
    print(f"items.csv / outcomes.csv: {len(items)} items; resolved Yes: "
          f"{int(out.resolved_to.sum())} ({out.resolved_to.mean():.0%}); "
          f"as-of dates {out.merge(pd.DataFrame(items)[['id', 'as_of']]).as_of.min()} "
          f"to {out.merge(pd.DataFrame(items)[['id', 'as_of']]).as_of.max()}")


if __name__ == "__main__":
    main()
