from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UniverseSecurity(BaseModel):
    """
    Canonical V2 security identity.

    Universe membership comes from QRQuant's configured universe.
    Optional metadata is populated only when an authoritative source
    provides it. Missing metadata remains None.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    company_name: str | None = None

    sector: str | None = None

    industry: str | None = None

    exchange: str | None = None

    currency: str | None = None

    instrument_type: str | None = None

    metadata_source: str | None = None

    def yahoo_symbol(self) -> str:
        """
        Return the Yahoo symbol used by the market-data provider.
        """

        normalized = self.symbol.strip().upper()

        if normalized.startswith("^"):
            return normalized

        if "." in normalized:
            return normalized

        return f"{normalized}.NS"
