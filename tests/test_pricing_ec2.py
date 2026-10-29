"""EC2 rate card lookups."""

from tf_cost.pricing.ec2 import quote_instance

from tests.support import planned

NAMED = {
    "t3.micro": 7.59,
    "t3.small": 15.18,
    "t3.medium": 30.37,
    "t3.large": 60.74,
    "t3.xlarge": 121.47,
    "m5.large": 70.08,
    "m5.xlarge": 140.16,
    "m6i.large": 70.08,
    "g4dn.xlarge": 383.98,
}


def test_named_instance_types_match_hourly_times_730():
    for instance_type, monthly in NAMED.items():
        quote = quote_instance(planned("aws_instance", {"instance_type": instance_type}))
        assert quote.monthly_usd == monthly
        assert quote.quantity == 1
        assert quote.rate_source == f"ec2:us-east-1:{instance_type}"


def test_instance_type_match_is_case_insensitive():
    quote = quote_instance(planned("aws_instance", {"instance_type": "T3.MICRO"}))
    assert quote.monthly_usd == 7.59


def test_unknown_instance_type_is_zero_with_a_review_note():
    quote = quote_instance(planned("aws_instance", {"instance_type": "foo.bar"}))
    assert quote.monthly_usd == 0
    assert quote.rate_source == "ec2:unknown"
    assert any("unknown instance type, manual review required" in note for note in quote.notes)


def test_missing_instance_type_is_zero():
    quote = quote_instance(planned("aws_instance", {}))
    assert quote.monthly_usd == 0
    assert any("unknown instance type, manual review required" in note for note in quote.notes)


def test_unknown_at_plan_time_is_zero():
    quote = quote_instance(planned("aws_instance", unknown={"instance_type"}))
    assert quote.monthly_usd == 0
    assert any("unknown at plan time" in note for note in quote.notes)
