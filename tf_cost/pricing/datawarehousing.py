"""Redshift provisioned clusters. us-east-1 on-demand node hours.

RA3 managed storage is billed per GB and is not in the node price.
"""

from decimal import Decimal

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import money, monthly_from_hourly, text, whole_number

# Hourly USD per node, us-east-1, on-demand.
HOURLY: dict[str, str] = {
    "dc2.large": "0.25",
    "dc2.8xlarge": "4.80",
    "ra3.xlplus": "1.086",
    "ra3.4xlarge": "3.26",
}
RA3_PREFIX = "ra3."


def quote_redshift(resource: PlannedResource) -> PriceQuote:
    """Price aws_redshift_cluster from node_type and number_of_nodes."""
    notes: list[str] = []
    nodes = whole_number(resource, "number_of_nodes")
    if nodes is None:
        nodes = 1
        if resource.is_unknown("number_of_nodes"):
            notes.append("number_of_nodes is unknown at plan time; assumed 1")

    node_type = text(resource, "node_type")
    if node_type is None:
        notes.append("unknown node type, manual review required")
        return PriceQuote(0.0, nodes, "redshift:unknown", tuple(notes))

    key = node_type.lower()
    hourly = HOURLY.get(key)
    if hourly is None:
        notes.append(f"unknown node type, manual review required: {node_type}")
        return PriceQuote(0.0, nodes, "redshift:unknown", tuple(notes))

    if key.startswith(RA3_PREFIX):
        notes.append("Redshift Managed Storage is usage-dependent and is not included")
    unit = Decimal(str(monthly_from_hourly(hourly)))
    return PriceQuote(
        money(unit * Decimal(max(nodes, 0))),
        max(nodes, 0),
        f"redshift:us-east-1:{key}",
        tuple(notes),
    )
