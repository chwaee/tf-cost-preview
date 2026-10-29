"""Secrets Manager secret storage. API calls are not in the plan."""

from decimal import Decimal

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import block_count, money

# us-east-1 public list: $0.40 per secret-month. $0.05 is per 10,000 API calls.
SECRET_MONTHLY = Decimal("0.40")


def quote_secret(resource: PlannedResource) -> PriceQuote:
    """Price aws_secretsmanager_secret. Each replica is another secret on the bill."""
    replicas = block_count(resource, "replica")
    notes = ["API calls are $0.05 per 10,000 and are not included"]
    if replicas is None:
        notes.append("replica count unknown; priced as one secret")
        replicas = 0
    quantity = 1 + replicas
    if replicas:
        notes.append("each cross-region replica is billed as an additional secret")
    return PriceQuote(
        money(SECRET_MONTHLY * Decimal(quantity)),
        quantity,
        "secretsmanager:secret",
        tuple(notes),
    )
