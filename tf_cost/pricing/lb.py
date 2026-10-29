"""Load balancers. Application uses a low-traffic baseline, not a measured LCU bill."""

from decimal import Decimal

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import money, monthly_from_hourly, text

# 0.036 USD/hour * 730. Hourly base only. Processed bytes are extra.
NETWORK_MONTHLY = monthly_from_hourly("0.036")
APPLICATION_BASELINE = money(Decimal("26.50"))


def quote_lb(resource: PlannedResource) -> PriceQuote:
    """Price aws_lb and the aws_alb alias."""
    kind = text(resource, "load_balancer_type")
    if kind is None:
        kind = "application"
        unknown = resource.is_unknown("load_balancer_type")
        note = (
            "load balancer type unknown; using the application baseline"
            if unknown
            else "load balancer type not set; using the application baseline"
        )
        return _application(extra=note)
    kind = kind.lower()
    if kind == "network":
        return PriceQuote(
            NETWORK_MONTHLY,
            1,
            "lb:network:hourly",
            ("Network Load Balancer hourly base. Processed bytes are not included.",),
        )
    if kind == "gateway":
        return PriceQuote(
            0.0,
            1,
            "lb:gateway:none",
            ("gateway load balancers have no rate card entry",),
        )
    if kind != "application":
        return _application(extra=f"load balancer type {kind} is priced as application")
    return _application(extra=None)


def _application(extra: str | None) -> PriceQuote:
    notes = [
        "baseline includes a low-traffic LCU allowance; real LCU charges vary",
    ]
    if extra:
        notes.insert(0, extra)
    return PriceQuote(APPLICATION_BASELINE, 1, "lb:application:baseline", tuple(notes))
