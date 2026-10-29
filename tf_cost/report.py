"""Text table and JSON report for a parsed plan."""

import json
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal

from tf_cost.models import EstimateLine, PlannedResource, Report
from tf_cost.parser import parse_plan
from tf_cost.pricing import quote
from tf_cost.pricing.common import money

SCHEMA_VERSION = "1.0"
DISCLAIMERS: tuple[str, ...] = (
    "Rates are us-east-1 on-demand list prices, 730 hours/month.",
    "Data transfer, reserved instances, and spot pricing are not included.",
    "Total is the monthly run rate of resources this plan creates, updates, or replaces. "
    "It is not a bill delta.",
    "Actual costs may vary based on usage patterns and region.",
)


def build_report(document: object, *, now: datetime | None = None) -> Report:
    """Price a Terraform plan document."""
    resources, regions = parse_plan(document)
    priced: list[EstimateLine] = []
    unpriced: list[EstimateLine] = []
    for resource in resources:
        line, kind = _line(resource)
        if kind == "priced":
            priced.append(line)
        else:
            unpriced.append(line)
    priced.sort(key=lambda item: item.resource_address)
    unpriced.sort(key=lambda item: item.resource_address)
    total = _sum(line.monthly_estimate or 0 for line in priced)
    return Report(
        resources=tuple(priced),
        unpriced=tuple(unpriced),
        total_monthly_estimate=total,
        notes=DISCLAIMERS,
        generated_at=_timestamp(now),
        region_assumptions=_regions(regions),
    )


def render_table(report: Report, *, include_unpriced: bool = False) -> str:
    """Render the human-readable table. Unpriced rows are optional."""
    body: list[tuple[str, str, str, str]] = []
    for line in report.resources:
        body.append(_priced_row(line))
    if include_unpriced:
        for line in report.unpriced:
            body.append(
                (
                    line.resource_address,
                    line.resource_type,
                    "-",
                    "$0.00",
                )
            )

    header = ("Resource", "Type", "Qty", "Monthly Est.")
    widths = [len(cell) for cell in header]
    for row in body:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def format_row(cells: tuple[str, str, str, str], *, money_col: bool) -> str:
        left = f"{cells[0]:<{widths[0]}}  {cells[1]:<{widths[1]}}  {cells[2]:>{widths[2]}}"
        gap = "  "
        if money_col:
            return f"{left}{gap}{cells[3]:>{widths[3]}}"
        return f"{left}{gap}{cells[3]}"

    lines = [format_row(header, money_col=True), ""]
    if body:
        lines.extend(format_row(row, money_col=True) for row in body)
    else:
        lines.append("No priced resources.")
    lines.append("")

    total = f"${report.total_monthly_estimate:,.2f} / month"
    label = "TOTAL ESTIMATE:"
    span = widths[0] + 2 + widths[1] + 2 + widths[2] + 2 + widths[3]
    if len(label) + 2 + len(total) <= span:
        lines.append(f"{label}{total:>{span - len(label)}}")
    else:
        lines.append(f"{label}  {total}")
    lines.append("")
    lines.append("Notes:")
    for note in report.notes:
        lines.append(f"- {note}")
    if report.unpriced and not include_unpriced:
        lines.append(f"- {_unpriced_hint(len(report.unpriced))}")
    for line in report.resources:
        for note in line.notes:
            lines.append(f"- {line.resource_address}: {note}")
    if include_unpriced:
        for line in report.unpriced:
            for note in line.notes:
                lines.append(f"- {line.resource_address}: {note}")
    return "\n".join(lines) + "\n"


def render_json(report: Report) -> str:
    """Render the machine-readable document. schema_version is duplicated in metadata."""
    payload = {
        "schema_version": report.schema_version,
        "metadata": {
            "schema_version": report.schema_version,
            "generated_at": report.generated_at,
            "region_assumptions": report.region_assumptions,
            "currency": report.currency,
            "hours_per_month": report.hours_per_month,
        },
        "resources": [_priced_json(line) for line in report.resources],
        "unpriced": [_unpriced_json(line) for line in report.unpriced],
        "total_monthly_estimate": report.total_monthly_estimate,
        "notes": list(report.notes),
    }
    return json.dumps(payload, indent=2) + "\n"


def _line(resource: PlannedResource) -> tuple[EstimateLine, str]:
    action = _action_label(resource.actions)
    priced = quote(resource)
    if priced is None:
        notes = [f"action: {action}", "no rate card for this resource type"]
        return (
            EstimateLine(
                resource_address=resource.address,
                resource_type=resource.resource_type,
                quantity=None,
                monthly_estimate=None,
                rate_source=None,
                notes=tuple(notes),
            ),
            "unpriced",
        )

    notes = [f"action: {action}", *priced.notes]
    if resource.actions == ("delete",):
        prior = f"${priced.monthly_usd:,.2f}"
        notes = [
            "action: delete",
            f"prior monthly run rate {prior}",
            *priced.notes,
        ]
        monthly = 0.0
        quantity = priced.quantity
        source = priced.rate_source
    else:
        monthly = priced.monthly_usd
        quantity = priced.quantity
        source = priced.rate_source

    return (
        EstimateLine(
            resource_address=resource.address,
            resource_type=resource.resource_type,
            quantity=quantity,
            monthly_estimate=monthly,
            rate_source=source,
            notes=tuple(notes),
        ),
        "priced",
    )


def _action_label(actions: tuple[str, ...]) -> str:
    if actions == ("delete",):
        return "delete"
    if set(actions) == {"create", "delete"}:
        return "replace"
    if actions == ("update",):
        return "update"
    if actions == ("create",):
        return "create"
    return "+".join(actions)


def _priced_row(line: EstimateLine) -> tuple[str, str, str, str]:
    quantity = "-" if line.quantity is None else str(line.quantity)
    amount = 0.0 if line.monthly_estimate is None else line.monthly_estimate
    return (
        line.resource_address,
        line.resource_type,
        quantity,
        f"${amount:,.2f}",
    )


def _priced_json(line: EstimateLine) -> dict[str, object]:
    return {
        "resource_address": line.resource_address,
        "resource_type": line.resource_type,
        "quantity": line.quantity,
        "monthly_estimate": line.monthly_estimate,
        "rate_source": line.rate_source,
        "notes": list(line.notes),
    }


def _unpriced_json(line: EstimateLine) -> dict[str, object]:
    return {
        "resource_address": line.resource_address,
        "resource_type": line.resource_type,
        "notes": list(line.notes),
    }


def _sum(amounts: Iterable[float]) -> float:
    total = Decimal("0")
    for amount in amounts:
        total += Decimal(str(amount))
    return money(total)


def _regions(regions: tuple[str, ...]) -> str:
    base = "us-east-1 on-demand, 730 hours/month"
    if not regions:
        return base
    listed = ", ".join(regions)
    return f"{base}. Plan mentions: {listed}. Rates are not adjusted for region."


def _timestamp(now: datetime | None) -> str:
    moment = now if now is not None else datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    moment = moment.astimezone(UTC).replace(microsecond=0)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _unpriced_hint(count: int) -> str:
    if count == 1:
        return "1 resource has no rate card. Re-run with --include-unpriced to list it."
    return f"{count} resources have no rate card. Re-run with --include-unpriced to list them."
