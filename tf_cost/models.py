"""Plan resources and price quotes shared by the parser, rate card, and report."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlannedResource:
    """One managed resource change that can affect the monthly run rate."""

    address: str
    resource_type: str
    actions: tuple[str, ...]
    values: dict[str, object]
    unknown: frozenset[str]

    def is_unknown(self, key: str) -> bool:
        """True when Terraform has not chosen this attribute yet."""
        if "*" in self.unknown or key in self.unknown:
            return True
        prefix_dot = f"{key}."
        prefix_index = f"{key}["
        return any(
            item.startswith(prefix_dot) or item.startswith(prefix_index) for item in self.unknown
        )


@dataclass(frozen=True)
class PriceQuote:
    """Line total for one resource. monthly_usd is already multiplied by quantity."""

    monthly_usd: float
    quantity: int
    rate_source: str
    notes: tuple[str, ...]


@dataclass(frozen=True)
class EstimateLine:
    """A row in the report. Priced rows and unpriced rows share this shape."""

    resource_address: str
    resource_type: str
    quantity: int | None
    monthly_estimate: float | None
    rate_source: str | None
    notes: tuple[str, ...]


@dataclass(frozen=True)
class Report:
    """Deterministic estimate. generated_at is the only clock-dependent field."""

    resources: tuple[EstimateLine, ...]
    unpriced: tuple[EstimateLine, ...]
    total_monthly_estimate: float
    notes: tuple[str, ...]
    generated_at: str
    region_assumptions: str
    currency: str = "USD"
    schema_version: str = "1.0"
    hours_per_month: int = 730
