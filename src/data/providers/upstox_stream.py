from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

import upstox_client


@dataclass(frozen=True)
class LivePriceTick:
    instrument_key: str
    price: Decimal
    timestamp: datetime
    close_price: Decimal | None = None
    quantity: int | None = None


class UpstoxMarketDataStream:
    """
    Real-time Upstox MarketDataStreamerV3 adapter.

    The research engine receives normalized LivePriceTick objects
    instead of Upstox-specific feed structures.
    """

    VALID_MODES = {
        "ltpc",
        "full",
        "full_d30",
        "option_greeks",
    }

    def __init__(
        self,
        access_token: str,
        instrument_keys: list[str] | None = None,
        *,
        mode: str = "ltpc",
        on_tick: Callable[[LivePriceTick], None] | None = None,
    ) -> None:
        if not access_token.strip():
            raise ValueError(
                "access_token must not be empty."
            )

        if mode not in self.VALID_MODES:
            raise ValueError(
                f"Unsupported market-data mode: {mode}"
            )

        self.access_token = access_token.strip()
        if not instrument_keys:
            raise ValueError(
                "instrument_keys must not be empty."
            )

        self.instrument_keys = list(
            dict.fromkeys(
                key.strip()
                for key in instrument_keys
                if key.strip()
            )
        )

        if not self.instrument_keys:
            raise ValueError(
                "instrument_keys must contain "
                "at least one non-empty key."
            )

        self.mode = mode
        self.on_tick = on_tick

        configuration = upstox_client.Configuration()
        configuration.access_token = self.access_token

        self.api_client = upstox_client.ApiClient(
            configuration
        )

        self.streamer = (
            upstox_client.MarketDataStreamerV3(
                self.api_client
            )
        )

        self.streamer.on(
            "open",
            self._handle_open,
        )

        self.streamer.on(
            "message",
            self._handle_message,
        )

        self.streamer.on(
            "error",
            self._handle_error,
        )

        self.streamer.on(
            "close",
            self._handle_close,
        )

    def _handle_open(self, *_args: Any) -> None:
        print(
            "Upstox market-data WebSocket connected."
        )

        if self.instrument_keys:
            self.subscribe(
                self.instrument_keys,
                mode=self.mode,
            )

    @staticmethod
    def _handle_error(*args: Any) -> None:
        print(
            "Upstox market-data WebSocket error:",
            *args,
        )

    @staticmethod
    def _handle_close(*args: Any) -> None:
        print(
            "Upstox market-data WebSocket closed:",
            *args,
        )

    @staticmethod
    def _read(
        obj: Any,
        name: str,
        default: Any = None,
    ) -> Any:
        if obj is None:
            return default

        if isinstance(obj, dict):
            return obj.get(name, default)

        return getattr(
            obj,
            name,
            default,
        )

    @classmethod
    def _extract_ltpc(
        cls,
        feed: Any,
    ) -> Any | None:
        return cls._read(
            feed,
            "ltpc",
        )

    def _handle_message(
        self,
        message: Any,
    ) -> None:
        """
        Normalize incoming Upstox feed data.

        The SDK may expose the message as a dictionary-like
        structure or an SDK model.
        """

        feeds = self._read(
            message,
            "feeds",
        )

        if feeds is None:
            return

        if hasattr(feeds, "items"):
            iterator = feeds.items()
        else:
            return

        for instrument_key, feed in iterator:

            ltpc = self._extract_ltpc(feed)

            if ltpc is None:
                continue

            ltp = self._read(
                ltpc,
                "ltp",
            )

            if ltp is None:
                continue

            ltt = self._read(
                ltpc,
                "ltt",
            )

            timestamp = (
                datetime.fromtimestamp(
                    int(ltt) / 1000,
                    tz=timezone.utc,
                )
                if ltt is not None
                else datetime.now(timezone.utc)
            )

            close_price = self._read(
                ltpc,
                "cp",
            )

            quantity = self._read(
                ltpc,
                "ltq",
            )

            tick = LivePriceTick(
                instrument_key=str(
                    instrument_key
                ),
                price=Decimal(str(ltp)),
                timestamp=timestamp,
                close_price=(
                    Decimal(str(close_price))
                    if close_price is not None
                    else None
                ),
                quantity=(
                    int(quantity)
                    if quantity is not None
                    else None
                ),
            )

            if self.on_tick is not None:
                self.on_tick(tick)

    def connect(self) -> None:
        self.streamer.connect()

    def disconnect(self) -> None:
        self.streamer.disconnect()

    def subscribe(
        self,
        instrument_keys: list[str],
        *,
        mode: str | None = None,
    ) -> None:
        keys = [
            key.strip()
            for key in instrument_keys
            if key.strip()
        ]

        if not keys:
            raise ValueError(
                "instrument_keys must not be empty."
            )

        selected_mode = mode or self.mode

        if selected_mode not in self.VALID_MODES:
            raise ValueError(
                f"Unsupported market-data mode: "
                f"{selected_mode}"
            )

        self.streamer.subscribe(
            keys,
            selected_mode,
        )

    def unsubscribe(
        self,
        instrument_keys: list[str],
    ) -> None:
        keys = [
            key.strip()
            for key in instrument_keys
            if key.strip()
        ]

        if keys:
            self.streamer.unsubscribe(keys)

    def change_mode(
        self,
        instrument_keys: list[str],
        mode: str,
    ) -> None:
        if mode not in self.VALID_MODES:
            raise ValueError(
                f"Unsupported market-data mode: {mode}"
            )

        self.streamer.change_mode(
            instrument_keys,
            mode,
        )
