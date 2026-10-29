"""S3 buckets and DynamoDB tables. Usage that is not in the plan stays at zero."""

from decimal import Decimal

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import money, text, whole_number

# Provisioned capacity, us-east-1, per hour.
RCU_HOUR = Decimal("0.00013")
WCU_HOUR = Decimal("0.00065")
HOURS = Decimal("730")


def quote_s3(resource: PlannedResource) -> PriceQuote:
    """Price aws_s3_bucket. Object storage is not in the plan."""
    del resource
    return PriceQuote(
        0.0,
        1,
        "s3:usage",
        (
            "usage-dependent, requires size input. Standard storage is $0.023/GB-month, "
            "Standard-IA is $0.0125/GB-month, PUT is $0.005 per 1,000, GET is $0.0004 per 1,000",
        ),
    )


def quote_dynamodb(resource: PlannedResource) -> PriceQuote:
    """Price aws_dynamodb_table. On-demand request volume is not estimated."""
    mode = text(resource, "billing_mode")
    normalized = (mode or "").upper().replace("-", "_")
    if normalized in {"PAY_PER_REQUEST", "ON_DEMAND"}:
        return PriceQuote(
            0.0,
            1,
            "dynamodb:on-demand",
            (
                "usage-dependent. On-demand is $0.25 per million read request units and "
                "$1.25 per million write request units",
            ),
        )

    reads = whole_number(resource, "read_capacity")
    writes = whole_number(resource, "write_capacity")
    if reads is None and writes is None:
        return PriceQuote(
            0.0,
            1,
            "dynamodb:usage",
            ("usage-dependent. Billing mode and capacity are not in the plan",),
        )

    total = (RCU_HOUR * Decimal(reads or 0) + WCU_HOUR * Decimal(writes or 0)) * HOURS
    notes = [
        "provisioned capacity at $0.00013 per RCU-hour and $0.00065 per WCU-hour. "
        "On-demand request pricing does not apply",
    ]
    if reads is None:
        notes.append("read capacity is unknown and was treated as 0")
    if writes is None:
        notes.append("write capacity is unknown and was treated as 0")
    return PriceQuote(money(total), 1, "dynamodb:provisioned", tuple(notes))
