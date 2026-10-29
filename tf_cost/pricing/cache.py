"""ElastiCache replication groups. Redis OSS node hours, us-east-1.

Valkey is cheaper and is not a separate card. The note says so.
"""

from decimal import Decimal

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import money, monthly_from_hourly, text, whole_number

# Hourly USD, Redis OSS / Memcached, us-east-1, on-demand.
HOURLY: dict[str, str] = {
    "cache.t3.micro": "0.017",
    "cache.t3.small": "0.034",
    "cache.m5.large": "0.156",
    "cache.r5.large": "0.252",
}


def quote_elasticache(resource: PlannedResource) -> PriceQuote:
    """Price aws_elasticache_replication_group by node type and node count."""
    notes = ["priced at Redis OSS; Valkey is cheaper and is not a separate card"]
    quantity, count_note = _node_count(resource)
    if count_note:
        notes.append(count_note)

    node_type = text(resource, "node_type")
    if node_type is None:
        notes.append("unknown node type, manual review required")
        return PriceQuote(0.0, quantity, "elasticache:unknown", tuple(notes))
    hourly = HOURLY.get(node_type.lower())
    if hourly is None:
        notes.append(f"unknown node type, manual review required: {node_type}")
        return PriceQuote(0.0, quantity, "elasticache:unknown", tuple(notes))

    unit = Decimal(str(monthly_from_hourly(hourly)))
    return PriceQuote(
        money(unit * Decimal(quantity)),
        quantity,
        f"elasticache:us-east-1:redis:{node_type.lower()}",
        tuple(notes),
    )


def _node_count(resource: PlannedResource) -> tuple[int, str | None]:
    clusters = whole_number(resource, "num_cache_clusters")
    if clusters is not None:
        return max(clusters, 0), None
    if resource.is_unknown("num_cache_clusters"):
        return 1, "node count is unknown at plan time; assumed 1"

    groups = whole_number(resource, "num_node_groups")
    if groups is None:
        if resource.is_unknown("num_node_groups"):
            return 1, "node count is unknown at plan time; assumed 1"
        return 1, "node count not in the plan; assumed 1"

    replicas = whole_number(resource, "replicas_per_node_group")
    note = None
    if replicas is None:
        replicas = 0
        note = "replicas_per_node_group not set; assumed 0"
    return max(groups, 0) * (replicas + 1), note
