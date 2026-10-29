"""Terraform plan parsing."""

import json
from pathlib import Path

import pytest
from tf_cost.parser import PlanError, parse_plan

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_minimal_plan_is_one_create():
    resources, regions = parse_plan(_load("minimal_plan.json"))
    assert len(resources) == 1
    assert resources[0].address == "aws_instance.web"
    assert resources[0].actions == ("create",)
    assert resources[0].values["instance_type"] == "t3.micro"
    assert regions == ("us-east-1",)


def test_empty_plan_has_no_resources():
    resources, regions = parse_plan(_load("empty_plan.json"))
    assert resources == ()
    assert regions == ()


def test_destroy_uses_before_values():
    resources, _regions = parse_plan(_load("destroy_plan.json"))
    assert len(resources) == 1
    assert resources[0].actions == ("delete",)
    assert resources[0].values["instance_type"] == "t3.micro"


def test_mixed_actions_skip_noop_and_data_sources():
    resources, _regions = parse_plan(_load("mixed_plan.json"))
    by_address = {item.address: item for item in resources}
    assert "aws_instance.unchanged" not in by_address
    assert "data.aws_ami.ubuntu" not in by_address
    assert by_address["aws_instance.resized"].values["instance_type"] == "t3.large"
    assert by_address["aws_instance.removed"].actions == ("delete",)
    assert by_address["aws_instance.replaced"].actions == ("delete", "create")
    assert by_address["aws_instance.replaced"].values["instance_type"] == "m5.large"


def test_sample_plan_keeps_the_module_address_and_skips_nothing_priced():
    resources, _regions = parse_plan(_load("sample_plan.json"))
    addresses = [item.address for item in resources]
    assert "module.network.aws_nat_gateway.main" in addresses
    assert "aws_vpc.main" in addresses


def test_missing_after_value_is_filled_from_planned_values():
    document = {
        "resource_changes": [
            {
                "address": "aws_instance.web",
                "mode": "managed",
                "type": "aws_instance",
                "change": {
                    "actions": ["create"],
                    "after": {"ami": "ami-1"},
                    "after_unknown": {"id": True},
                },
            }
        ],
        "planned_values": {
            "root_module": {
                "resources": [
                    {
                        "address": "aws_instance.web",
                        "values": {"instance_type": "t3.micro", "ami": "ami-from-plan"},
                    }
                ]
            }
        },
    }
    resources, _regions = parse_plan(document)
    assert resources[0].values["instance_type"] == "t3.micro"
    assert resources[0].values["ami"] == "ami-1"


def test_after_unknown_is_not_filled_from_planned_values():
    document = {
        "resource_changes": [
            {
                "address": "aws_instance.web",
                "type": "aws_instance",
                "change": {
                    "actions": ["create"],
                    "after": {},
                    "after_unknown": {"instance_type": True},
                },
            }
        ],
        "planned_values": {
            "root_module": {
                "resources": [
                    {"address": "aws_instance.web", "values": {"instance_type": "t3.micro"}}
                ]
            }
        },
    }
    resources, _regions = parse_plan(document)
    assert resources[0].is_unknown("instance_type")
    assert "instance_type" not in resources[0].values


def test_state_document_is_rejected():
    with pytest.raises(PlanError, match="state file"):
        parse_plan({"values": {"root_module": {}}})


def test_non_object_is_rejected():
    with pytest.raises(PlanError, match="object"):
        parse_plan([{"type": "aws_instance"}])


def test_missing_attributes_do_not_raise():
    resources, _regions = parse_plan(
        {
            "resource_changes": [
                {
                    "address": "aws_instance.web",
                    "type": "aws_instance",
                    "change": {"actions": ["create"]},
                }
            ]
        }
    )
    assert resources[0].values == {}
