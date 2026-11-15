"""Build the Confidence Audit items from real Yahoo Finance prices.

Outputs (in src/data/stock_analyser, wherever this is run from):
  items.csv     id, as_of, option_a, option_b, context      (what the model may see;
                stocks appear only as neutral codes, never as tickers)
  outcomes.csv  id, horizon_end, ticker_a, ticker_b, ret_a, ret_b, winner
                (never shown to the model; holds the code-to-ticker key)
  prices.csv    adjusted closes, one column per ticker

Nothing is estimated: if a ticker has missing data or a horizon has not finished,
the script stops with a message instead of filling anything in.
"""
import itertools
import random
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

# Dow Jones Industrial Average constituents (30).
TICKERS = [
    "AAPL", "AMGN", "AMZN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS",
    "GS", "HD", "HON", "IBM", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK",
    "MSFT", "NKE", "NVDA", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT",
]
AS_OF = ["2026-07-01", "2026-07-30", "2026-08-28", "2026-09-28", "2026-10-14"]
PAIRS_PER_DATE = 30
LOOKBACK = 63   # trading days of trailing return shown as context
HORIZON = 20    # trading days over which the outcome is measured
SEED = 0
DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "stock_analyser"
START = "2026-02-01"  # enough history for the first 63-day lookback


def fail(msg):
    sys.exit(f"STOPPED: {msg}")


def main():
    raw = yf.download(TICKERS, start=START, auto_adjust=True, progress=False)
    if raw is None or raw.empty:
        fail("price download returned no data.")
    px = raw["Close"].dropna(how="all")

    missing = [t for t in TICKERS if t not in px.columns or px[t].isna().all()]
    if missing:
        fail(f"no data for ticker(s): {missing}")
    px = px[TICKERS]
    gaps = [t for t in TICKERS if px[t].isna().any()]
    if gaps:
        fail(f"missing prices inside the window for ticker(s): {gaps}")

    # Neutral code per ticker (letter-digit-letter-digit, so it cannot be a real
    # ticker). Own random stream, so the pair sampling below is unchanged.
    code_rng = random.Random(SEED + 1)
    letters, digits = "ABCDEFGHJKLMNPQRSTUVWXYZ", "23456789"
    codes = set()
    while len(codes) < len(TICKERS):
        codes.add(code_rng.choice(letters) + code_rng.choice(digits)
                  + code_rng.choice(letters) + code_rng.choice(digits))
    code = dict(zip(TICKERS, code_rng.sample(sorted(codes), len(TICKERS))))

    days = px.index
    rng = random.Random(SEED)
    all_pairs = list(itertools.combinations(TICKERS, 2))
    items, outcomes = [], []

    for date in AS_OF:
        # snap back to the last trading day on or before the requested date
        i = days.searchsorted(pd.Timestamp(date), side="right") - 1
        if i < LOOKBACK:
            fail(f"not enough history before {date} for a {LOOKBACK}-day lookback.")
        if i + HORIZON >= len(days):
            fail(f"the {HORIZON}-day horizon after {date} has not finished "
                 f"(last price date {days[-1].date()}). Move this as-of date earlier.")
        as_of = days[i].date().isoformat()
        end = days[i + HORIZON].date().isoformat()
        trail = px.iloc[i] / px.iloc[i - LOOKBACK] - 1
        fwd = px.iloc[i + HORIZON] / px.iloc[i] - 1

        for n, pair in enumerate(rng.sample(all_pairs, PAIRS_PER_DATE), 1):
            a, b = pair if rng.random() < 0.5 else pair[::-1]
            if fwd[a] == fwd[b]:
                fail(f"exact tie between {a} and {b} from {as_of}.")
            item_id = f"{as_of}_{n:02d}"
            context = (
                # no date here: the model must not know which period this is
                f"Over the previous {LOOKBACK} trading days, stock {code[a]} returned "
                f"{trail[a] * 100:+.1f}% and stock {code[b]} returned "
                f"{trail[b] * 100:+.1f}% (total return, dividends included)."
            )
            items.append(dict(id=item_id, as_of=as_of, option_a=code[a],
                              option_b=code[b], context=context))
            # real tickers live only here, for scoring and the knowledge probe
            outcomes.append(dict(id=item_id, horizon_end=end,
                                 ticker_a=a, ticker_b=b,
                                 ret_a=round(float(fwd[a]), 6),
                                 ret_b=round(float(fwd[b]), 6),
                                 winner=code[a] if fwd[a] > fwd[b] else code[b]))

    pd.DataFrame(items).to_csv(DATA_DIR / "items.csv", index=False)
    pd.DataFrame(outcomes).to_csv(DATA_DIR / "outcomes.csv", index=False)
    px.round(6).to_csv(DATA_DIR / "prices.csv", index_label="date")
    print(f"items.csv: {len(items)} rows | outcomes.csv: {len(outcomes)} rows | "
          f"prices.csv: {len(px)} days x {px.shape[1]} tickers "
          f"({days[0].date()} to {days[-1].date()})")


if __name__ == "__main__":
    main()
