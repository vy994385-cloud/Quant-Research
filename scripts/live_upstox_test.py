from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from src.data.providers.upstox_stream import (
    LivePriceTick,
    UpstoxMarketDataStream,
)


def on_tick(tick: LivePriceTick) -> None:
    print(
        f"LIVE | {tick.instrument_key} | "
        f"LTP={tick.price} | "
        f"time={tick.timestamp.isoformat()} | "
        f"qty={tick.quantity}"
    )


def main() -> None:
    load_dotenv(ROOT / ".env")

    token = os.getenv("UPSTOX_ACCESS_TOKEN")

    if not token:
        raise RuntimeError(
            "UPSTOX_ACCESS_TOKEN is missing. "
            "Add it to ~/quant-research/.env"
        )

    stream = UpstoxMarketDataStream(
        access_token=token,
        instrument_keys=[
            "NSE_INDEX|Nifty 50",
        ],
        mode="ltpc",
        on_tick=on_tick,
    )

    print(
        "Connecting to Upstox live market feed..."
    )

    stream.connect()


if __name__ == "__main__":
    main()
