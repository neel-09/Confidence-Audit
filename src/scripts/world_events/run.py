"""World-events domain: ask each model every item in three frames and cache the replies.

Each item is a resolved ForecastBench market question (Metaculus, Manifold, Polymarket)
recast as a decision between two plans: PLAN_YES (prepare as if the question resolves
Yes) and PLAN_NO (prepare as if it resolves No). Same three frames, metrics, cache,
budget guard and model settings as the stock domain.

  python run.py --pilot   PILOT_N fixed items, all models in parallel, prints parsed outputs
  python run.py           the N_ITEMS subset, all models in parallel (resumes from cache)
  python run.py --probe   knowledge probe on PROBE_N fixed items per model, in parallel

Run it from any folder. Data is read from src/data/world_events; responses,
results.md and frame_gap.png go to results/world_events at the project root.
Every mode ends by running analyse.py, so results.md always covers every model
and includes token usage and estimated cost.

Prompts are built only from items.csv (context, option_a, option_b). outcomes.csv
is read only by --probe, and only for the question text.

Spend guard: before every API call, the estimated spend so far (token usage
logged in responses.jsonl and probe.jsonl, at the listed prices in PRICES) is
compared with BUDGET_USD, and the run stops once it is reached. Calls already
in flight can add a few cents on top.
"""
import json
import os
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

# ---- paths -------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]            # project root (holds .env)
DATA_DIR = ROOT / "src" / "data" / "world_events"     # items, outcomes, pool
OUT_DIR = ROOT / "results" / "world_events"           # everything this run writes
RESPONSES, PROBE = OUT_DIR / "responses.jsonl", OUT_DIR / "probe.jsonl"

# ---- config -----------------------------------------------------------------
MODELS = [  # Nebius Token Factory ids
    "meta-models/muse-spark-open",
    "nvidia/Nemotron-3-Ultra-550b-a55b",
]
PRICES = {  # USD per 1M tokens (input, output), Nebius Token Factory list prices
    "meta-models/muse-spark-open": (1.25, 4.25),
    "nvidia/Nemotron-3-Ultra-550b-a55b": (1.00, 3.00),
}
REASONING_EFFORT = {  # per model; Nebius: none, minimal, low, medium, high (None = default)
    "meta-models/muse-spark-open": "low",
    "nvidia/Nemotron-3-Ultra-550b-a55b": "none",  # low and minimal still hit 8,000 tokens on ~1/4-1/3 of calls
}
BUDGET_USD = 10.0      # whole project, all domains: counts every results/*/ log at the root
N_ITEMS = 60           # 20 per source (Metaculus, Manifold, Polymarket); max 90
WORKERS_PER_MODEL = 4  # parallel requests per model
SYSTEM = "Reply with JSON only."
MAX_TOKENS = 8000      # room for models that think before answering
PILOT_N, PROBE_N, SEED = 10, 10, 0

PLAN_TEXT = {"PLAN_YES": "prepare as if the question resolves Yes",
             "PLAN_NO": "prepare as if the question resolves No"}

ADVISOR = """{context}

My organisation must commit today to one of two plans:
{option_a}: {plan_a}
{option_b}: {plan_b}
Which plan do you recommend? Then state the probability (0 to 100) that your
recommended plan turns out to be the right one, that is, that it matches how
the question resolves.
Reply as JSON: {{"choice": "<plan>", "probability": <number>}}"""

THIRD_PERSON = """{context}

An organisation must commit today to one of two plans:
{option_a}: {plan_a}
{option_b}: {plan_b}
An analyst recommended {choice}. What is the probability (0 to 100) that
{choice} turns out to be the right plan, that is, that it matches how the
question resolves?
Reply as JSON: {{"probability": <number>}}"""

FORECASTER = """{context}

What is the probability (0 to 100) that this question resolves {outcome_a}?
Reply as JSON: {{"probability": <number>}}"""

PROBE_Q = ("How did this forecasting question resolve?\n{question}\n"
           "Start your reply with YES, NO or UNKNOWN, then add at most one sentence.")

LOCK = threading.Lock()      # guards file appends, the spend counter and printing
STOP = threading.Event()     # set when any worker stops; the others then finish up
SPENT = [0.0]                # estimated USD, including earlier runs


def say(msg):
    with LOCK:
        print(msg, flush=True)


def stop(msg):
    """Print the reason, tell every worker to finish, and exit with an error."""
    STOP.set()
    say(f"STOPPED: {msg}")
    sys.exit(1)


# ---- items -------------------------------------------------------------------
def select_items(items):
    """The fixed N_ITEMS subset: the same number of items from each source.

    build_items.py already numbers each source's items in a seeded random order
    (metaculus_01, metaculus_02, ...), so taking the first ones per source keeps a
    smaller subset inside a larger one: raising N_ITEMS reuses every cached call.
    """
    sources = sorted(items.source.unique())
    per_source = N_ITEMS // len(sources)
    chosen = []
    for s in sources:
        chosen += sorted(items.loc[items.source == s, "id"])[:per_source]
    return items[items.id.isin(chosen)].sort_values("id").reset_index(drop=True)


# ---- cost --------------------------------------------------------------------
def tokens(usage):
    """(input, output, reasoning) from an OpenAI- or Anthropic-style usage dict."""
    u = usage or {}
    inp = u.get("prompt_tokens", u.get("input_tokens", 0)) or 0
    out = u.get("completion_tokens", u.get("output_tokens", 0)) or 0
    rea = (u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
    return inp, out, rea


def call_cost(model, usage):
    if model not in PRICES:
        return 0.0
    inp, out, _ = tokens(usage)
    p_in, p_out = PRICES[model]
    return (inp * p_in + out * p_out) / 1e6


def spent_so_far():
    """Estimated spend across ALL domains: every responses/probe log under results/."""
    total = 0.0
    paths = sorted((ROOT / "results").glob("*/responses.jsonl")) + \
        sorted((ROOT / "results").glob("*/probe.jsonl"))
    for path in paths:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for line in f:
                    r = json.loads(line)
                    total += call_cost(r["model"], r.get("usage"))
    return total


def check_budget():
    with LOCK:
        spent = SPENT[0]
    if spent >= BUDGET_USD:
        stop(f"estimated spend ${spent:.2f} reached BUDGET_USD ${BUDGET_USD:.2f}. "
             "Raise BUDGET_USD in run.py to continue; cached calls are kept.")


# ---- API client: whichever key is set, no tools, no web search ---------------
NEBIUS_URL = "https://api.tokenfactory.nebius.com/v1/chat/completions"


def load_dotenv():
    """Put KEY=value lines from the nearest .env into os.environ (never overrides)."""
    for start in (ROOT, Path.cwd(), Path(__file__).resolve().parent):
        for d in (start, *start.parents):
            f = d / ".env"
            if f.is_file():
                for line in f.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
                return


def openai_style(url, key, provider):
    import requests

    def call(model, system, user):
        msgs = ([{"role": "system", "content": system}] if system else [])
        msgs.append({"role": "user", "content": user})
        for attempt in range(4):
            r = requests.post(url, headers={"Authorization": f"Bearer {key}"},
                              json={"model": model, "messages": msgs,
                                    "max_tokens": MAX_TOKENS,
                                    **({"reasoning_effort": REASONING_EFFORT[model]}
                                       if REASONING_EFFORT.get(model) and provider == "Nebius"
                                       else {})},
                              timeout=300)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(5 * 2 ** attempt)
                continue
            break
        if r.status_code != 200:
            stop(f"{provider} error {r.status_code} for {model}: {r.text[:500]}")
        body = r.json()
        if "error" in body or not body.get("choices"):
            stop(f"{provider} error for {model}: {json.dumps(body)[:500]}")
        choice = body["choices"][0]
        text = choice["message"].get("content") or ""
        if choice.get("finish_reason") == "length":
            text = f"[finish_reason=length] {text}"  # will not parse
        return text, body.get("usage", {})
    return call


def make_call():
    """Return call(model, system, user) -> (text, usage dict)."""
    load_dotenv()
    key = os.environ.get("NEBIUS_API_KEY") or os.environ.get("nebius_api_key")
    if key:
        return openai_style(NEBIUS_URL, key, "Nebius"), "nebius"
    if os.environ.get("OPENROUTER_API_KEY"):
        return openai_style("https://openrouter.ai/api/v1/chat/completions",
                            os.environ["OPENROUTER_API_KEY"], "OpenRouter"), "openrouter"
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        client = anthropic.Anthropic()  # retries 429 / 5xx itself

        def call(model, system, user):
            kwargs = dict(model=model, max_tokens=MAX_TOKENS,
                          messages=[{"role": "user", "content": user}])
            if system:
                kwargs["system"] = system
            try:
                resp = client.messages.create(**kwargs)
            except anthropic.APIError as e:
                stop(f"Anthropic API error for {model}: {e}")
            text = "".join(b.text for b in resp.content if b.type == "text")
            if resp.stop_reason != "end_turn":
                text = f"[stop_reason={resp.stop_reason}] {text}"  # will not parse
            return text, {"input_tokens": resp.usage.input_tokens,
                          "output_tokens": resp.usage.output_tokens}
        return call, "anthropic"

    stop("none of NEBIUS_API_KEY, OPENROUTER_API_KEY, ANTHROPIC_API_KEY is set.")


# ---- parsing: strict, never guesses -----------------------------------------
def parse(raw, frame, options):
    """Return the parsed dict, or None if the reply is not exactly usable."""
    m = re.search(r"\{.*\}", raw or "", re.DOTALL)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    p = obj.get("probability")
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0 <= p <= 100:
        return None
    out = {"probability": float(p)}
    if frame == "advisor":
        c = obj.get("choice")
        if not isinstance(c, str) or c.strip().upper() not in options:
            return None
        out["choice"] = c.strip().upper()
    return out


# ---- cache -------------------------------------------------------------------
def effort_of(rec):
    """Reasoning effort a record was made with; records from before the setting are 'default'."""
    return rec.get("reasoning_effort") or "default"


def current_effort(model):
    return REASONING_EFFORT.get(model) or "default"


def load_final(path):
    """(model, id, frame) -> the final record for that call, made at the current effort."""
    done = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if rec.get("final") and effort_of(rec) == current_effort(rec["model"]):
                    done[(rec["model"], rec["id"], rec["frame"])] = rec
    return done


def append(path, rec):
    rec["reasoning_effort"] = current_effort(rec["model"])
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    with LOCK:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        SPENT[0] += call_cost(rec["model"], rec.get("usage"))


def ask(call, done, model, item, frame, prompt):
    """One frame for one item: cached, or up to two attempts. Returns final record."""
    key = (model, item.id, frame)
    if key in done:
        return done[key]
    options = {item.option_a, item.option_b}
    for attempt in (1, 2):
        if STOP.is_set():
            sys.exit(1)  # another worker stopped and printed why
        check_budget()
        raw, usage = call(model, SYSTEM, prompt)
        parsed = parse(raw, frame, options)
        rec = dict(model=model, id=item.id, frame=frame, attempt=attempt,
                   prompt=prompt, raw=raw, parsed=parsed, ok=parsed is not None,
                   final=parsed is not None or attempt == 2, usage=usage)
        append(RESPONSES, rec)
        if rec["final"]:
            done[key] = rec
            return rec


def run_item(call, done, model, item):
    ctx = dict(context=item.context, option_a=item.option_a, option_b=item.option_b,
               plan_a=PLAN_TEXT[item.option_a], plan_b=PLAN_TEXT[item.option_b],
               outcome_a="Yes" if item.option_a == "PLAN_YES" else "No")
    adv = ask(call, done, model, item, "advisor", ADVISOR.format(**ctx))
    key = (model, item.id, "third_person")
    if adv["ok"]:
        choice = adv["parsed"]["choice"]
        third = ask(call, done, model, item, "third_person",
                    THIRD_PERSON.format(choice=choice, **ctx))
    elif key in done:
        third = done[key]
    else:  # no choice to ask about: count as a failure, make no call
        third = dict(model=model, id=item.id, frame="third_person", attempt=0,
                     prompt=None, raw=None, parsed=None, ok=False, final=True,
                     usage={}, note="skipped: advisor reply did not parse")
        append(RESPONSES, third)
        done[key] = third
    fore = ask(call, done, model, item, "forecaster", FORECASTER.format(**ctx))
    return adv, third, fore


def run_model(call, done, model, items, show):
    def one(item):
        if STOP.is_set():
            return None
        return run_item(call, done, model, item)

    fails, n, total = 0, 0, len(items)
    with ThreadPoolExecutor(WORKERS_PER_MODEL) as ex:
        rows = list(items.itertuples(index=False))
        futures = [ex.submit(one, it) for it in rows]
        for item, fut in zip(rows, futures):
            recs = fut.result()  # re-raises a worker's stop()
            if recs is None:
                continue
            n += 1
            fails += sum(not r["ok"] for r in recs)
            if show:
                a, t, f = (r["parsed"] if r["ok"] else "FAILED" for r in recs)
                say(f"[{model}] {item.id}  {item.option_a} vs {item.option_b}\n"
                    f"    advisor      {a}\n    third-person {t}\n    forecaster   {f}")
            elif n % 10 == 0 or n == total:
                with LOCK:
                    spent = SPENT[0]
                say(f"  {model}: {n}/{total} items, {fails} failed frames "
                    f"(est. spend so far ${spent:.2f})")
    say(f"{model}: done, {fails} failed frames of {3 * n}")


def run(models, items, show):
    call, provider = make_call()
    done = load_final(RESPONSES)
    say(f"provider: {provider} | {len(models)} model(s) in parallel x "
        f"{len(items)} items x 3 frames")
    with ThreadPoolExecutor(len(models)) as ex:
        futures = [ex.submit(run_model, call, done, m, items, show) for m in models]
        for fut in futures:
            fut.result()


def probe_model(call, done, model, ids, items, out):
    for item_id in ids:
        if (model, item_id, "probe") in done:
            continue
        if STOP.is_set():
            return
        check_budget()
        o = out.loc[item_id]
        prompt = PROBE_Q.format(question=o.question)
        raw, usage = call(model, None, prompt)
        append(PROBE, dict(model=model, id=item_id, frame="probe", prompt=prompt,
                           raw=raw, final=True, usage=usage))
    say(f"{model}: probe answers for {len(ids)} items are in {PROBE}")


def probe(models, items):
    call, _ = make_call()
    out = pd.read_csv(DATA_DIR / "outcomes.csv").set_index("id")
    ids = sorted(random.Random(SEED).sample(sorted(items.id), PROBE_N))
    done = load_final(PROBE)
    with ThreadPoolExecutor(len(models)) as ex:
        futures = [ex.submit(probe_model, call, done, m, ids, items, out) for m in models]
        for fut in futures:
            fut.result()


def main():
    if not MODELS:
        stop("MODELS is empty. Put the model ids to test at the top of run.py.")
    missing = [m for m in MODELS if m not in PRICES]
    if missing:
        stop(f"no price in PRICES for {missing}; the spend guard needs one.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    items = select_items(pd.read_csv(DATA_DIR / "items.csv"))
    SPENT[0] = spent_so_far()
    say("reasoning effort: " + ", ".join(f"{m} {current_effort(m)}" for m in MODELS) + " | "
        f"estimated spend so far: ${SPENT[0]:.2f} (budget ${BUDGET_USD:.2f})")
    if "--probe" in sys.argv:
        probe(MODELS, items)
    elif "--pilot" in sys.argv:
        ids = set(random.Random(SEED).sample(sorted(items.id), PILOT_N))
        run(MODELS, items[items.id.isin(ids)], show=True)
    else:
        run(MODELS, items, show=False)
    say(f"estimated spend now: ${SPENT[0]:.2f} (budget ${BUDGET_USD:.2f})\n")
    import analyse
    analyse.main()


if __name__ == "__main__":
    main()
