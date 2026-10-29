"""Full plan to report."""

import json
from datetime import UTC, datetime
from pathlib import Path

from tf_cost.report import build_report, render_json, render_table

FIXTURES = Path(__file__).parent / "fixtures"
WHEN = datetime(2026, 10, 29, tzinfo=UTC)

SAMPLE_LINES = {
    "aws_instance.web": 7.59,
    "aws_db_instance.primary": 14.71,
    "aws_ebs_volume.data": 8.0,
    "aws_lb.main": 26.5,
    "module.network.aws_nat_gateway.main": 32.85,
    "aws_eip.nat": 3.65,
    "aws_s3_bucket.logs": 0.0,
    "aws_lambda_function.api": 0.0,
    "aws_route53_zone.main": 0.5,
    "aws_secretsmanager_secret.db": 0.4,
}


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_sample_plan_prices_and_total():
    report = build_report(_load("sample_plan.json"), now=WHEN)
    by_address = {line.resource_address: line for line in report.resources}
    assert set(by_address) == set(SAMPLE_LINES)
    for address, monthly in SAMPLE_LINES.items():
        assert by_address[address].monthly_estimate == monthly
    assert report.total_monthly_estimate == 94.2
    assert [line.resource_address for line in report.unpriced] == ["aws_vpc.main"]
    assert report.generated_at == "2026-10-29T00:00:00Z"
    assert "us-east-1" in report.region_assumptions
    assert any("not a bill delta" in note for note in report.notes)


def test_sample_table_and_json_round_trip_shape():
    report = build_report(_load("sample_plan.json"), now=WHEN)
    table = render_table(report)
    assert "Resource" in table and "Monthly Est." in table
    assert "TOTAL ESTIMATE:" in table
    assert "$94.20 / month" in table
    assert "aws_vpc.main" not in table
    assert "1 resource has no rate card" in table
    assert "aws_instance.web:" in table

    shown = render_table(report, include_unpriced=True)
    assert "aws_vpc.main" in shown
    assert "$0.00" in shown
    assert "$94.20 / month" in shown

    payload = json.loads(render_json(report))
    assert payload["schema_version"] == "1.0"
    assert payload["metadata"]["schema_version"] == "1.0"
    assert payload["metadata"]["generated_at"] == "2026-10-29T00:00:00Z"
    assert payload["metadata"]["currency"] == "USD"
    assert payload["metadata"]["hours_per_month"] == 730
    assert payload["total_monthly_estimate"] == 94.2
    row = payload["resources"][0]
    for key in (
        "resource_address",
        "resource_type",
        "quantity",
        "monthly_estimate",
        "rate_source",
        "notes",
    ):
        assert key in row
    assert payload["unpriced"][0]["resource_type"] == "aws_vpc"


def test_same_input_and_clock_produce_the_same_json():
    document = _load("sample_plan.json")
    first = render_json(build_report(document, now=WHEN))
    second = render_json(build_report(document, now=WHEN))
    assert first == second


def test_empty_plan_table():
    table = render_table(build_report(_load("empty_plan.json"), now=WHEN))
    assert "No priced resources." in table
    assert "$0.00 / month" in table


def test_destroy_plan_is_zero_and_names_the_prior_rate():
    report = build_report(_load("destroy_plan.json"), now=WHEN)
    assert report.total_monthly_estimate == 0
    assert report.resources[0].monthly_estimate == 0
    assert any("prior monthly run rate $7.59" in note for note in report.resources[0].notes)


def test_mixed_plan_uses_after_and_skips_noop():
    report = build_report(_load("mixed_plan.json"), now=WHEN)
    by_address = {line.resource_address: line for line in report.resources}
    assert "aws_instance.unchanged" not in by_address
    assert "data.aws_ami.ubuntu" not in by_address
    assert by_address["aws_instance.created"].monthly_estimate == 15.18
    assert by_address["aws_instance.resized"].monthly_estimate == 60.74
    assert any("action: update" in note for note in by_address["aws_instance.resized"].notes)
    assert by_address["aws_instance.removed"].monthly_estimate == 0
    assert any("30.37" in note for note in by_address["aws_instance.removed"].notes)
    assert by_address["aws_instance.replaced"].monthly_estimate == 70.08
    assert any("action: replace" in note for note in by_address["aws_instance.replaced"].notes)
    assert report.total_monthly_estimate == 146
