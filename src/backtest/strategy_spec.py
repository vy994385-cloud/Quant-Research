from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True)
class ParameterRange:
    """
    Inclusive deterministic parameter range.

    Values are generated as:

        minimum
        minimum + step
        ...
        maximum
    """

    minimum: Decimal
    maximum: Decimal
    step: Decimal

    def __post_init__(self) -> None:
        minimum = Decimal(self.minimum)
        maximum = Decimal(self.maximum)
        step = Decimal(self.step)

        if step <= Decimal("0"):
            raise ValueError(
                "step must be greater than zero"
            )

        if maximum < minimum:
            raise ValueError(
                "maximum must be greater than or equal to minimum"
            )

    def values(self) -> tuple[Decimal, ...]:
        values: list[Decimal] = []

        current = Decimal(self.minimum)
        maximum = Decimal(self.maximum)
        step = Decimal(self.step)

        while current <= maximum:
            values.append(current)
            current += step

        return tuple(values)


@dataclass(frozen=True)
class ParameterSet:
    """
    Immutable strategy parameter configuration.
    """

    values: Mapping[str, Decimal]

    def __post_init__(self) -> None:
        normalized = {
            str(key): Decimal(value)
            for key, value in self.values.items()
        }

        if not normalized:
            raise ValueError(
                "parameter set cannot be empty"
            )

        object.__setattr__(
            self,
            "values",
            normalized,
        )

    def get(self, name: str) -> Decimal:
        try:
            return self.values[name]
        except KeyError as exc:
            raise KeyError(
                f"Unknown strategy parameter: {name}"
            ) from exc

    def as_dict(self) -> dict[str, Decimal]:
        return dict(self.values)
