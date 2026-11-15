"""Score the cached responses against outcomes.csv.

  python analyse.py   ->  results.md, frame_gap.png, and a printed summary

Reads only responses.jsonl, probe.jsonl (if present), items.csv and outcomes.csv.
Makes no API calls. Every number comes from the cached responses. Paths, the
item subset and the price list are taken from run.py; run.py calls this at the
end of every mode, and it can also be run on its own from any folder.
"""
import json
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from run import (BUDGET_USD, DATA_DIR, MODELS, OUT_DIR, PRICES, PROBE, RESPONSES,
                 call_cost, current_effort, effort_of, select_items, tokens)

OUT_MD, OUT_PNG = OUT_DIR / "results.md", OUT_DIR / "frame_gap.png"
N_BOOT, SEED = 2000, 0
FRAMES = ["advisor", "third_person", "forecaster"]


def load_final(path):
    """Final records made at the current REASONING_EFFORT in run.py (others are ignored)."""
    with open(path, encoding="utf-8") as f:
        recs = [json.loads(line) for line in f]
    return [r for r in recs
            if r.get("final") and effort_of(r) == current_effort(r["model"])]


def per_item(recs, items, outcomes):
    """One row per item for one model; NaN wherever a needed frame failed."""
    by = {(r["id"], r["frame"]): r for r in recs}
    rows = []
    for it in items.itertuples(index=False):
        got = {f: by.get((it.id, f)) for f in FRAMES}
        if not any(got.values()):
            continue  # item not run for this model
        ok = {f: bool(got[f] and got[f]["ok"]) for f in FRAMES}
        nan = float("nan")
        adv = got["advisor"]["parsed"] if ok["advisor"] else None
        p_adv = adv["probability"] if adv else nan
        p_third = got["third_person"]["parsed"]["probability"] if ok["third_person"] else nan
        p_fore_a = got["forecaster"]["parsed"]["probability"] if ok["forecaster"] else nan
        winner = outcomes.loc[it.id, "winner"]
        a_won = float(winner == it.option_a)
        hit = float(adv["choice"] == winner) if adv else nan
        # forecaster probability restated for the stock the advisor chose
        if adv:
            p_fore = p_fore_a if adv["choice"] == it.option_a else 100 - p_fore_a
        else:
            p_fore = nan
        rows.append({
            "attempted_advisor": got["advisor"] is not None,
            "attempted_third_person": got["third_person"] is not None,
            "attempted_forecaster": got["forecaster"] is not None,
            "fail_advisor": float(not ok["advisor"]),
            "fail_third_person": float(not ok["third_person"]),
            "fail_forecaster": float(not ok["forecaster"]),
            "frame_gap": p_adv - p_fore,
            "ownership_gap": p_adv - p_third,
            "coherence_violation": float(p_fore < 50) if not np.isnan(p_fore) else nan,
            "hit": hit,
            "overconf_advisor": p_adv - 100 * hit,
            "overconf_third_person": p_third - 100 * hit,
            "overconf_forecaster": p_fore - 100 * hit,
            "brier_advisor": (p_adv / 100 - hit) ** 2,
            "brier_third_person": (p_third / 100 - hit) ** 2,
            "brier_forecaster": (p_fore_a / 100 - a_won) ** 2,
        })
    return pd.DataFrame(rows)


def boot(col, rng):
    """Mean of a per-item column with a 95% bootstrap interval over items."""
    x = col.to_numpy(dtype=float)
    n_valid = int(np.sum(~np.isnan(x)))
    if n_valid == 0:
        return float("nan"), float("nan"), float("nan"), 0
    idx = rng.integers(0, len(x), size=(N_BOOT, len(x)))
    with np.errstate(all="ignore"):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            means = np.nanmean(x[idx], axis=1)
    lo, hi = np.nanpercentile(means, [2.5, 97.5])
    return float(np.nanmean(x)), float(lo), float(hi), n_valid


METRICS = [  # (label, column, unit, scale)
    ("Frame Gap (advisor minus forecaster)", "frame_gap", "points", 1),
    ("Ownership gap (advisor minus third-person)", "ownership_gap", "points", 1),
    ("Coherence violation rate", "coherence_violation", "%", 100),
    ("Hit rate", "hit", "%", 100),
    ("Overconfidence, advisor", "overconf_advisor", "points", 1),
    ("Overconfidence, third-person", "overconf_third_person", "points", 1),
    ("Overconfidence, forecaster", "overconf_forecaster", "points", 1),
    ("Brier score, advisor", "brier_advisor", "", 1),
    ("Brier score, third-person", "brier_third_person", "", 1),
    ("Brier score, forecaster", "brier_forecaster", "", 1),
    ("Parse failure rate, advisor", "fail_advisor", "%", 100),
    ("Parse failure rate, third-person", "fail_third_person", "%", 100),
    ("Parse failure rate, forecaster", "fail_forecaster", "%", 100),
]


def fmt(v, unit):
    if np.isnan(v):
        return "n/a"
    return f"{v:.3f}" if unit == "" else f"{v:+.1f}" if unit == "points" else f"{v:.1f}%"


def score_probe(path, outcomes):
    """Per model: answers, answers with a % figure, answers within 2 points of truth."""
    out = {}
    for r in load_final(path):
        truth = 100 * outcomes.loc[r["id"], "ret_a"]
        figs = [float(x.replace("−", "-")) for x in
                re.findall(r"([-+−]?\d+(?:\.\d+)?)\s*(?:%|percent)", r.get("raw") or "")]
        m = out.setdefault(r["model"], {"n": 0, "figure": 0, "close": 0})
        m["n"] += 1
        m["figure"] += bool(figs)
        m["close"] += any(abs(f - truth) <= 2 for f in figs)
    return out


def usage_by_model():
    """(model, run) -> API calls, token counts and estimated cost, from every logged attempt."""
    rows = {}
    for run_name, path in (("experiment", RESPONSES), ("probe", PROBE)):
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r.get("attempt") == 0:  # skipped frame, no API call made
                    continue
                inp, out, rea = tokens(r.get("usage"))
                m = rows.setdefault((r["model"], f"{run_name}, effort {effort_of(r)}"),
                                    {"calls": 0, "in": 0, "out": 0, "rea": 0, "cost": 0.0})
                m["calls"] += 1
                m["in"] += inp
                m["out"] += out
                m["rea"] += rea
                m["cost"] += call_cost(r["model"], r.get("usage"))
    return rows


def usage_section(rows):
    md = ["## Token usage and estimated cost", "",
          "Every API attempt is counted, including retries and failed parses. Cost "
          "is estimated from the logged token counts at the list prices in "
          "`run.py` (USD per 1M tokens, input / output: "
          + "; ".join(f"{m} {p[0]:.2f} / {p[1]:.2f}" for m, p in PRICES.items())
          + "). Check the Nebius console for the billed amount. Reasoning tokens "
          "are part of output tokens and are shown only when the API reports them. "
          "Spend at every reasoning effort is listed; the metrics above use only "
          "each model's current effort in `run.py`.", "",
          "| Model | Run | API calls | Input tokens | Output tokens | Reasoning tokens "
          "| Output tokens per call | Est. cost (USD) |",
          "|---|---|---|---|---|---|---|---|"]
    tot = {"calls": 0, "in": 0, "out": 0, "cost": 0.0}
    for (model, run_name), m in sorted(rows.items()):
        rea = f"{m['rea']:,}" if m["rea"] else "not reported"
        per = m["out"] / m["calls"] if m["calls"] else 0
        md.append(f"| {model} | {run_name} | {m['calls']:,} | {m['in']:,} | {m['out']:,} "
                  f"| {rea} | {per:,.0f} | {m['cost']:.2f} |")
        for k in tot:
            tot[k] += m[k]
    md += [f"| **Total** | | {tot['calls']:,} | {tot['in']:,} | {tot['out']:,} | | "
           f"| **{tot['cost']:.2f}** |", "",
           f"Budget set in `run.py`: ${BUDGET_USD:.2f}.", ""]
    return md, tot


def main():
    if not os.path.exists(RESPONSES):
        sys.exit(f"STOPPED: {RESPONSES} not found. Run run.py first.")
    items = select_items(pd.read_csv(DATA_DIR / "items.csv"))
    outcomes = pd.read_csv(DATA_DIR / "outcomes.csv").set_index("id")
    recs = load_final(RESPONSES)
    models = sorted({r["model"] for r in recs})
    rng = np.random.default_rng(SEED)

    md = ["# Confidence Audit results", "",
          "Reasoning effort scored: " + ", ".join(
              f"{m} `{current_effort(m)}`" for m in MODELS) + ".", "",
          f"95% intervals: bootstrap over items, {N_BOOT:,} resamples. "
          "Probabilities are on a 0 to 100 scale, so gaps and overconfidence are in "
          "points. Always-50% Brier baseline: 0.250. `n` is the number of items "
          "with the frames that metric needs.", ""]
    summary, gaps = [], {}
    for model in models:
        df = per_item([r for r in recs if r["model"] == model], items, outcomes)
        md += [f"## {model}", "", f"Items run: {len(df)} of {len(items)}", "",
               "| Metric | Value | 95% interval | n |", "|---|---|---|---|"]
        res = {}
        for label, col, unit, scale in METRICS:
            series = df[col]
            if col.startswith("fail_"):  # only items where that frame was attempted
                series = series[df["attempted_" + col[5:]]]
            mean, lo, hi, n = boot(series * scale, rng)
            res[col] = (mean, lo, hi, n)
            md.append(f"| {label} | {fmt(mean, unit)} | "
                      f"{fmt(lo, unit)} to {fmt(hi, unit)} | {n} |")
        md.append("")
        gaps[model] = (res["frame_gap"], res["ownership_gap"])

        def gap_line(name, key):
            mean, lo, hi, n = res[key]
            if n == 0:
                return f"{name}: no usable items."
            zero = "excludes" if lo > 0 or hi < 0 else "includes"
            return (f"{name}: {mean:+.1f} points (95% interval {lo:+.1f} to {hi:+.1f}, "
                    f"n={n}); the interval {zero} zero.")
        h, hl, hh, hn = res["hit"]
        summary += [
            f"{model}",
            "  " + gap_line("Frame Gap", "frame_gap"),
            "  " + gap_line("Ownership gap", "ownership_gap"),
            f"  Coherence violations: {fmt(res['coherence_violation'][0], '%')} of "
            f"{res['coherence_violation'][3]} items.",
            f"  Hit rate: {fmt(h, '%')} (95% interval {fmt(hl, '%')} to {fmt(hh, '%')}, n={hn}).",
            "  Overconfidence (mean probability minus hit rate): advisor "
            f"{fmt(res['overconf_advisor'][0], 'points')}, third-person "
            f"{fmt(res['overconf_third_person'][0], 'points')}, forecaster "
            f"{fmt(res['overconf_forecaster'][0], 'points')} points.",
            "  Brier: advisor " + fmt(res["brier_advisor"][0], "") + ", third-person "
            + fmt(res["brier_third_person"][0], "") + ", forecaster "
            + fmt(res["brier_forecaster"][0], "") + " (baseline 0.250).",
            "  Parse failures: advisor " + fmt(res["fail_advisor"][0], "%")
            + ", third-person " + fmt(res["fail_third_person"][0], "%")
            + ", forecaster " + fmt(res["fail_forecaster"][0], "%") + ".",
        ]

    if os.path.exists(PROBE):
        md += ["## Knowledge probe", "",
               "Asked with real tickers and dates. A reply counts as close if any "
               "percentage it states is within 2 points of the true return "
               "(automatic text match; check probe.jsonl by hand if it matters).", "",
               "| Model | Answers | Gave a % figure | Within 2 points |", "|---|---|---|---|"]
        for model, m in sorted(score_probe(PROBE, outcomes).items()):
            md.append(f"| {model} | {m['n']} | {m['figure']} | {m['close']} |")
            summary.append(f"Probe, {model}: {m['close']} of {m['n']} answers gave a "
                           f"figure within 2 points of the true return "
                           f"({m['figure']} gave any figure).")
        md.append("")

    usage = usage_by_model()
    usage_md, tot = usage_section(usage)
    md += usage_md
    for model in models:
        calls = sum(m["calls"] for (mm, _), m in usage.items() if mm == model)
        out_tok = sum(m["out"] for (mm, _), m in usage.items() if mm == model)
        cost = sum(m["cost"] for (mm, _), m in usage.items() if mm == model)
        summary.append(f"Usage, {model}: {calls} API calls, {out_tok:,} output tokens, "
                       f"est. ${cost:.2f}.")
    summary.append(f"Usage, total: est. ${tot['cost']:.2f} of the ${BUDGET_USD:.2f} budget.")

    summary.append("Note: items share 5 dates and 30 stocks, so they are not "
                   "independent; intervals on hit rate and Brier are likely too narrow.")
    md += ["## Summary", "", "```", *summary, "```", ""]
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    fig, ax = plt.subplots(figsize=(max(5, 2.2 * len(models) + 2), 4))
    x = np.arange(len(models))
    for k, (name, color) in enumerate([("Frame Gap", "#3b6fb6"), ("Ownership gap", "#d9822b")]):
        vals = [gaps[m][k] for m in models]
        mean = np.array([v[0] for v in vals])
        err = np.array([[v[0] - v[1] for v in vals], [v[2] - v[0] for v in vals]])
        ax.bar(x + (k - 0.5) * 0.36, mean, 0.36, yerr=err, capsize=4, label=name, color=color)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x, models, rotation=15 if len(models) > 2 else 0)
    ax.set_ylabel("Probability points (advisor minus other frame)")
    ax.set_title("Frame Gap and ownership gap, 95% bootstrap intervals")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=150)

    print("\n".join(summary))
    print(f"\nWrote {OUT_MD} and {OUT_PNG}")


if __name__ == "__main__":
    main()
