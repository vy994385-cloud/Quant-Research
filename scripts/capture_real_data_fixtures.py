"""
Capture recorded real-data fixtures for the real-data research
verification milestone.

This script documents HOW the committed fixtures were produced.

- tcs_market.csv     : real TCS + ^NSEI daily OHLCV bars replayed
                       from the existing raw archive that was captured
                       from the Yahoo Finance provider on
                       2026-08-15 16:16 UTC.
- tcs_financials.json: real TCS annual financials captured from the
                       Yahoo Finance fundamentals provider at capture
                       time (requires live network access).

The recorded research source candidates (tcs_sources.json) are curated
from publicly available, dated TCS disclosures and are NOT regenerated
by this script.

Usage:

    .venv/bin/python scripts/capture_real_data_fixtures.py
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from src.data.providers.yahoo_financials import YahooFinanceFinancialProvider

REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = (
    REPO_ROOT / "data" / "raw" / "research" / "yahoofinancemarketdataprovider"
)
FIXTURE_DIR = REPO_ROOT / "fixtures" / "real_data"

# Point-in-time as-of used by the verification suite. The recorded
# market bars are capped on the last completed trading day strictly
# before this timestamp (2026-08-07).
VERIFICATION_AS_OF = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
MARKET_CUTOFF_DATE = date(2026, 8, 7)


def capture_market_csv() -> Path:
    records: list[dict] = []

    if not ARCHIVE_ROOT.exists():
        raise RuntimeError(
            f"raw archive not found: {ARCHIVE_ROOT}. "
            "The recorded market fixture cannot be regenerated "
            "without the original archived provider response."
        )

    for path in sorted(ARCHIVE_ROOT.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        payload = record["payload"]
        trading_date = date.fromisoformat(payload["trading_date"])

        if trading_date > MARKET_CUTOFF_DATE:
            continue

        records.append(payload)

    records.sort(
        key=lambda row: (row["symbol"], row["trading_date"])
    )

    target = FIXTURE_DIR / "tcs_market.csv"

    with target.open("w", encoding="utf-8", newline="") as handle:
        handle.write("symbol,date,open,high,low,close,volume\n")

        for row in records:
            handle.write(
                f"{row['symbol']},{row['trading_date']},"
                f"{row['open']},{row['high']},{row['low']},"
                f"{row['close']},{row['volume']}\n"
            )

    return target


def capture_financials_json() -> Path:
    provider = YahooFinanceFinancialProvider(timeout=20)

    snapshots = provider.get_annual_financials(
        "TCS",
        date(2016, 4, 1),
        VERIFICATION_AS_OF.date(),
    )

    if not snapshots:
        raise RuntimeError(
            "live financial capture returned no snapshots. "
            "The financial fixture cannot be regenerated right now."
        )

    target = FIXTURE_DIR / "tcs_financials.json"

    with target.open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "captured_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "provider": "yahoo_finance_fundamentals",
                "company": "TCS",
                "snapshots": [
                    snapshot.model_dump(mode="json")
                    for snapshot in snapshots
                ],
            },
            handle,
            indent=2,
            ensure_ascii=False,
        )

    return target


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    market = capture_market_csv()
    financials = capture_financials_json()

    print(f"wrote {market}")
    print(f"wrote {financials}")


if __name__ == "__main__":
    main()
