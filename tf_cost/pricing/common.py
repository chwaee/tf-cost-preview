"""Rate-card arithmetic and attribute readers shared by the pricers."""

from decimal import ROUND_HALF_UP, Decimal

from tf_cost.models import PlannedResource

# Public list prices are hourly. 730 hours is 365 / 12 * 24.
HOURS_PER_MONTH = Decimal("730")


def money(value: Decimal) -> float:
    """Round a dollar amount to the cent."""
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def monthly_from_hourly(hourly: str) -> float:
    """Convert a public hourly list price to a 730-hour month."""
    return money(Decimal(hourly) * HOURS_PER_MONTH)


def text(resource: PlannedResource, key: str) -> str | None:
    """Return a known non-empty string attribute."""
    if resource.is_unknown(key):
        return None
    value = resource.values.get(key)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def whole_number(resource: PlannedResource, key: str) -> int | None:
    """Return a known integer attribute. Floats are accepted only when whole."""
    if resource.is_unknown(key):
        return None
    value = resource.values.get(key)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def flag(resource: PlannedResource, key: str) -> bool | None:
    """Return a known boolean attribute."""
    if resource.is_unknown(key):
        return None
    value = resource.values.get(key)
    if isinstance(value, bool):
        return value
    return None


def block_count(resource: PlannedResource, key: str) -> int | None:
    """Count a Terraform block. None means the block is unknown at plan time."""
    if resource.is_unknown(key):
        return None
    value = resource.values.get(key)
    if value is None:
        return 0
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return 1
    return 0
