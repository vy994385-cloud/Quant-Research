from __future__ import annotations

import csv
from pathlib import Path


def load_symbols(file_path: str | Path) -> list[str]:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"market data file not found: {path}"
        )

    symbols: set[str] = set()

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file)

        if "symbol" not in (reader.fieldnames or []):
            raise ValueError(
                "market data CSV must contain a symbol column"
            )

        for row in reader:
            symbol = row["symbol"].strip().upper()

            if symbol:
                symbols.add(symbol)

    return sorted(symbols)
