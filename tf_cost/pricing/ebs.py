"""EBS volume and snapshot storage. us-east-1.

gp3 baseline IOPS and throughput are included in the GB rate. Extra gp3 IOPS
and throughput are not priced. io1 and io2 add $0.065 per provisioned IOPS-month,
which is the EBS rate, not the RDS rate.
"""

from decimal import Decimal

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import money, text, whole_number

GB_MONTH: dict[str, str] = {
    "gp3": "0.08",
    "gp2": "0.10",
    "io1": "0.125",
    "io2": "0.125",
    "st1": "0.045",
    "sc1": "0.015",
    "standard": "0.05",
}
IOPS_MONTH = Decimal("0.065")
IO_TYPES = {"io1", "io2"}
SNAPSHOT_GB = Decimal("0.05")


def quote_volume(resource: PlannedResource) -> PriceQuote:
    """Price aws_ebs_volume from size and type. Missing type uses gp3."""
    size = whole_number(resource, "size")
    if size is None:
        note = "size missing"
        if resource.is_unknown("size"):
            note = "size is unknown at plan time"
        return PriceQuote(0.0, 1, "ebs:unknown", (note,))

    volume_type = text(resource, "type")
    notes: list[str] = []
    if volume_type is None:
        volume_type = "gp3"
        notes.append("volume type not set; using gp3 at $0.08 per GB-month")
    else:
        volume_type = volume_type.lower()

    rate = GB_MONTH.get(volume_type)
    if rate is None:
        notes.append(f"unknown volume type {volume_type}; priced as gp3")
        volume_type = "gp3"
        rate = GB_MONTH["gp3"]

    total = Decimal(rate) * Decimal(size)
    if volume_type in IO_TYPES:
        iops = whole_number(resource, "iops")
        if iops is None:
            notes.append("provisioned IOPS not set; IOPS charge not included")
        else:
            total += IOPS_MONTH * Decimal(iops)
    elif volume_type == "gp3":
        notes.append("gp3 baseline IOPS are included; extra IOPS and throughput are not priced")

    return PriceQuote(money(total), 1, f"ebs:{volume_type}", tuple(notes))


def quote_snapshot(resource: PlannedResource) -> PriceQuote:
    """Price aws_ebs_snapshot from volume_size. Incremental data is often smaller."""
    size = whole_number(resource, "volume_size")
    if size is None:
        note = "volume size unknown"
        return PriceQuote(0.0, 1, "ebs:snapshot", (note,))
    return PriceQuote(
        money(SNAPSHOT_GB * Decimal(size)),
        1,
        "ebs:snapshot",
        ("priced from the full volume size; incremental snapshot data can be smaller",),
    )
