"""Route 53 hosted zones.

The first 25 hosted zones are $0.50 per month each, public or private.
This card does not know how many zones the account already has, so every
zone uses the $0.50 rate. Queries are not in the plan.
"""

from decimal import Decimal

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import block_count, flag, money

ZONE_MONTHLY = money(Decimal("0.50"))


def quote_route53_zone(resource: PlannedResource) -> PriceQuote:
    """Price aws_route53_zone. Records and health checks are out of scope."""
    private = _is_private(resource)
    if private is True:
        note = "private hosted zone; queries are not charged. Resolver endpoints are not included"
    elif private is False:
        note = "queries are usage-dependent at $0.40 per million standard queries"
    else:
        note = (
            "zone visibility unknown; priced at the hosted zone rate of $0.50. "
            "Public queries are extra"
        )
    source = "route53:hosted-zone:private" if private is True else "route53:hosted-zone"
    return PriceQuote(ZONE_MONTHLY, 1, source, (note,))


def _is_private(resource: PlannedResource) -> bool | None:
    marker = flag(resource, "private_zone")
    if marker is True:
        return True
    vpcs = block_count(resource, "vpc")
    if vpcs is None:
        return None if marker is None else False
    if vpcs > 0:
        return True
    if marker is False:
        return False
    if resource.is_unknown("private_zone"):
        return None
    return False
