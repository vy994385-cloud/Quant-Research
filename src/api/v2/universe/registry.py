from __future__ import annotations

import csv
from pathlib import Path

from .models import UniverseSecurity


class UniverseRegistry:
    """
    Loads QRQuant's configured security universe.

    The registry owns universe membership only. It does not call
    external APIs and does not infer missing company metadata.
    """

    def __init__(self, path: Path):
        self.path = path
        self._securities: tuple[UniverseSecurity, ...] | None = None

    def load(self) -> tuple[UniverseSecurity, ...]:
        if self._securities is not None:
            return self._securities

        if not self.path.exists():
            raise FileNotFoundError(
                f"QRQuant universe not found: {self.path}"
            )

        securities: list[UniverseSecurity] = []
        seen: set[str] = set()

        with self.path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)

            if "symbol" not in (reader.fieldnames or []):
                raise ValueError(
                    "QRQuant universe must contain a 'symbol' column."
                )

            for row in reader:
                symbol = (row.get("symbol") or "").strip().upper()

                if not symbol or symbol in seen:
                    continue

                seen.add(symbol)

                securities.append(
                    UniverseSecurity(symbol=symbol)
                )

        self._securities = tuple(securities)

        return self._securities
