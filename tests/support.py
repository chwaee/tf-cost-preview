"""Shared constructors for pricing tests."""

from tf_cost.models import PlannedResource


def planned(
    resource_type: str,
    values: dict[str, object] | None = None,
    *,
    address: str = "test.main",
    actions: tuple[str, ...] = ("create",),
    unknown: frozenset[str] | set[str] = frozenset(),
) -> PlannedResource:
    """Build a planned resource without a full Terraform document."""
    return PlannedResource(
        address=address,
        resource_type=resource_type,
        actions=actions,
        values=dict(values or {}),
        unknown=frozenset(unknown),
    )
