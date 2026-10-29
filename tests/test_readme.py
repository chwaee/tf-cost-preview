"""The published resource list and the README stay in sync."""

from pathlib import Path

from tf_cost.pricing import REGISTRY

README = Path("README.md").read_text(encoding="utf-8")
HARDERAWS = (
    "Run terraform show -json tfplan | tf-cost after applying a HarderAWS plan "
    "to see the guardrail costs."
)


def test_readme_names_every_priced_type():
    missing = [resource_type for resource_type in REGISTRY if resource_type not in README]
    assert missing == []


def test_readme_points_at_harderaws():
    assert HARDERAWS in README
