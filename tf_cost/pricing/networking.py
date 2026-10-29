"""NAT Gateway hourly base and Elastic IP addresses."""

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import monthly_from_hourly, text

NAT_MONTHLY = monthly_from_hourly("0.045")
EIP_UNATTACHED = monthly_from_hourly("0.005")
_ASSOCIATION_KEYS = ("instance", "network_interface", "association_id")


def quote_nat_gateway(resource: PlannedResource) -> PriceQuote:
    """Price one aws_nat_gateway. Data processing is not in the plan."""
    del resource
    return PriceQuote(
        NAT_MONTHLY,
        1,
        "nat:us-east-1:hourly",
        ("data processing is $0.045 per GB and is not included",),
    )


def quote_eip(resource: PlannedResource) -> PriceQuote:
    """Price aws_eip and the aws_elastic_ip alias.

    An address associated with an instance or network interface is free.
    An address with no association is the hourly charge. When the plan has
    not decided, the unattached rate is used so the line is not hidden.
    """
    attached = _attached(resource)
    if attached is True:
        return PriceQuote(
            0.0,
            1,
            "eip:attached",
            ("free while associated with a running instance",),
        )
    if attached is False:
        return PriceQuote(
            EIP_UNATTACHED,
            1,
            "eip:unattached",
            ("unattached address",),
        )
    return PriceQuote(
        EIP_UNATTACHED,
        1,
        "eip:unattached",
        (
            "attachment unknown at plan time; unattached addresses are "
            f"${EIP_UNATTACHED:.2f}/month and attached addresses are free",
        ),
    )


def _attached(resource: PlannedResource) -> bool | None:
    known_target = False
    saw_unknown = False
    for key in _ASSOCIATION_KEYS:
        if resource.is_unknown(key):
            saw_unknown = True
            continue
        if text(resource, key):
            known_target = True
    if known_target:
        return True
    if saw_unknown:
        return None
    return False
