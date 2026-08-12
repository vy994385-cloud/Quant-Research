from pathlib import Path

from src.data.universe import load_symbols


def test_load_symbols_returns_unique_sorted_symbols(
    tmp_path: Path,
) -> None:
    path = tmp_path / "prices.csv"

    path.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "TCS,2026-08-10,1,2,1,2,100\n"
        "INFY,2026-08-10,1,2,1,2,100\n"
        "TCS,2026-08-11,1,2,1,2,100\n",
        encoding="utf-8",
    )

    assert load_symbols(path) == [
        "INFY",
        "TCS",
    ]
