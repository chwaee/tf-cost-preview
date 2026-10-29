"""Turn terraform show -json output into planned resources.

Pricing uses resource_changes for the action and change.after for attributes.
A value missing from after is filled from planned_values when it is not marked
unknown. Deletes use change.before.
"""

import re
from typing import Any

from tf_cost.models import PlannedResource

_REGION = re.compile(r"^([a-z]{2}-[a-z]+-\d+)")


class PlanError(Exception):
    """The document is not a Terraform plan JSON this tool can read."""


def parse_plan(document: Any) -> tuple[tuple[PlannedResource, ...], tuple[str, ...]]:
    """Return resources that create, update, replace, or delete, plus detected regions."""
    if not isinstance(document, dict):
        raise PlanError("plan JSON must be an object")
    if "resource_changes" not in document:
        if "values" in document or "resources" in document:
            raise PlanError(
                "this looks like a Terraform state file; run terraform show -json on a saved plan"
            )
        raise PlanError("plan JSON has no resource_changes array")

    changes = document.get("resource_changes")
    if not isinstance(changes, list):
        raise PlanError("resource_changes must be an array")

    planned = _index_planned(document.get("planned_values"))
    resources: list[PlannedResource] = []
    regions: set[str] = set()

    for entry in changes:
        if not isinstance(entry, dict):
            continue
        if entry.get("mode") == "data":
            continue
        resource_type = entry.get("type")
        if not isinstance(resource_type, str) or not resource_type:
            continue
        address = _address(entry, resource_type)
        change = entry.get("change")
        if not isinstance(change, dict):
            change = {}
        actions = _actions(change.get("actions"))
        values, unknown = _values(change, actions, planned.get(address, {}))
        region = _region(values, unknown)
        if region:
            regions.add(region)
        if not actions or actions == ("no-op",):
            continue
        resources.append(
            PlannedResource(
                address=address,
                resource_type=resource_type,
                actions=actions,
                values=values,
                unknown=unknown,
            )
        )

    resources.sort(key=lambda item: item.address)
    return tuple(resources), tuple(sorted(regions))


def _address(entry: dict[str, Any], resource_type: str) -> str:
    address = entry.get("address")
    if isinstance(address, str) and address:
        return address
    name = entry.get("name")
    if isinstance(name, str) and name:
        return f"{resource_type}.{name}"
    return resource_type


def _actions(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(action for action in raw if isinstance(action, str))


def _values(
    change: dict[str, Any],
    actions: tuple[str, ...],
    planned: dict[str, Any],
) -> tuple[dict[str, object], frozenset[str]]:
    if actions == ("delete",):
        before = change.get("before")
        values = dict(before) if isinstance(before, dict) else {}
        return values, frozenset()

    after = change.get("after")
    values: dict[str, object] = dict(after) if isinstance(after, dict) else {}
    unknown = _unknown_keys(change.get("after_unknown"))
    if "*" in unknown:
        return values, unknown
    for key, value in planned.items():
        if key not in values and key not in unknown and not _nested_unknown(key, unknown):
            values[key] = value
    return values, unknown


def _unknown_keys(node: Any) -> frozenset[str]:
    found: set[str] = set()

    def walk(value: Any, prefix: str) -> None:
        if value is True:
            found.add(prefix or "*")
            return
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                walk(child, path)
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{prefix}[{index}]")

    if node is True:
        return frozenset({"*"})
    walk(node, "")
    return frozenset(found)


def _nested_unknown(key: str, unknown: frozenset[str]) -> bool:
    prefix_dot = f"{key}."
    prefix_index = f"{key}["
    return any(item.startswith(prefix_dot) or item.startswith(prefix_index) for item in unknown)


def _index_planned(planned_values: Any) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    if not isinstance(planned_values, dict):
        return found
    root = planned_values.get("root_module")
    if isinstance(root, dict):
        _walk_module(root, found)
    return found


def _walk_module(module: dict[str, Any], found: dict[str, dict[str, Any]]) -> None:
    resources = module.get("resources")
    if isinstance(resources, list):
        for resource in resources:
            if not isinstance(resource, dict):
                continue
            address = resource.get("address")
            values = resource.get("values")
            if isinstance(address, str) and isinstance(values, dict):
                found[address] = values
    children = module.get("child_modules")
    if isinstance(children, list):
        for child in children:
            if isinstance(child, dict):
                _walk_module(child, found)


def _region(values: dict[str, object], unknown: frozenset[str]) -> str | None:
    if "region" not in unknown:
        region = values.get("region")
        if isinstance(region, str) and region.strip():
            return region.strip()
    if "availability_zone" not in unknown:
        zone = values.get("availability_zone")
        if isinstance(zone, str):
            match = _REGION.match(zone.strip())
            if match:
                return match.group(1)
    return None
