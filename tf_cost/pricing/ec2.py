"""EC2 on-demand instance hours. us-east-1 Linux shared tenancy.

Monthly price is the hourly list price times 730, rounded to the cent.
Sizes that the family does not sell are absent on purpose. A size ladder
mis-prices GPU, Inferentia, and Trainium.
"""

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import monthly_from_hourly, text

# Hourly USD. Source: public us-east-1 Linux on-demand list.
HOURLY: dict[str, str] = {
    "t3.nano": "0.0052",
    "t3.micro": "0.0104",
    "t3.small": "0.0208",
    "t3.medium": "0.0416",
    "t3.large": "0.0832",
    "t3.xlarge": "0.1664",
    "t3.2xlarge": "0.3328",
    "t3a.nano": "0.0047",
    "t3a.micro": "0.0094",
    "t3a.small": "0.0188",
    "t3a.medium": "0.0376",
    "t3a.large": "0.0752",
    "t3a.xlarge": "0.1504",
    "t3a.2xlarge": "0.3008",
    "m5.large": "0.096",
    "m5.xlarge": "0.192",
    "m5.2xlarge": "0.384",
    "m5.4xlarge": "0.768",
    "m5.8xlarge": "1.536",
    "m5.12xlarge": "2.304",
    "m5.16xlarge": "3.072",
    "m5.24xlarge": "4.608",
    "m5.metal": "4.608",
    "m5a.large": "0.086",
    "m5a.xlarge": "0.172",
    "m5a.2xlarge": "0.344",
    "m5a.4xlarge": "0.688",
    "m5a.8xlarge": "1.376",
    "m5a.12xlarge": "2.064",
    "m5a.16xlarge": "2.752",
    "m5a.24xlarge": "4.128",
    "m6i.large": "0.096",
    "m6i.xlarge": "0.192",
    "m6i.2xlarge": "0.384",
    "m6i.4xlarge": "0.768",
    "m6i.8xlarge": "1.536",
    "m6i.12xlarge": "2.304",
    "m6i.16xlarge": "3.072",
    "m6i.24xlarge": "4.608",
    "m6i.32xlarge": "6.144",
    "m6i.metal": "6.144",
    "c5.large": "0.085",
    "c5.xlarge": "0.17",
    "c5.2xlarge": "0.34",
    "c5.4xlarge": "0.68",
    "c5.9xlarge": "1.53",
    "c5.12xlarge": "2.04",
    "c5.18xlarge": "3.06",
    "c5.24xlarge": "4.08",
    "c5.metal": "4.08",
    "r5.large": "0.126",
    "r5.xlarge": "0.252",
    "r5.2xlarge": "0.504",
    "r5.4xlarge": "1.008",
    "r5.8xlarge": "2.016",
    "r5.12xlarge": "3.024",
    "r5.16xlarge": "4.032",
    "r5.24xlarge": "6.048",
    "r5.metal": "6.048",
    "g4dn.xlarge": "0.526",
    "g4dn.2xlarge": "0.752",
    "g4dn.4xlarge": "1.204",
    "g4dn.8xlarge": "2.176",
    "g4dn.12xlarge": "3.912",
    "g4dn.16xlarge": "4.352",
    "g4dn.metal": "7.824",
    "g5.xlarge": "1.006",
    "g5.2xlarge": "1.212",
    "g5.4xlarge": "1.624",
    "g5.8xlarge": "2.448",
    "g5.12xlarge": "5.672",
    "g5.16xlarge": "4.352",
    "g5.24xlarge": "8.144",
    "g5.48xlarge": "16.288",
    "inf1.xlarge": "0.228",
    "inf1.2xlarge": "0.362",
    "inf1.6xlarge": "1.180",
    "inf1.24xlarge": "4.721",
    "trn1.2xlarge": "1.343",
    "trn1.32xlarge": "21.50",
    "trn1n.32xlarge": "24.78",
}

UNKNOWN = "unknown instance type, manual review required"


def quote_instance(resource: PlannedResource) -> PriceQuote:
    """Price aws_instance from instance_type. EBS volumes are separate resources."""
    instance_type = text(resource, "instance_type")
    if instance_type is None:
        note = UNKNOWN
        if resource.is_unknown("instance_type"):
            note = f"{UNKNOWN}; instance_type is unknown at plan time"
        return PriceQuote(0.0, 1, "ec2:unknown", (note,))
    key = instance_type.lower()
    hourly = HOURLY.get(key)
    if hourly is None:
        return PriceQuote(
            0.0,
            1,
            "ec2:unknown",
            (f"{UNKNOWN}: {instance_type}",),
        )
    return PriceQuote(
        monthly_from_hourly(hourly),
        1,
        f"ec2:us-east-1:{key}",
        ("Linux shared tenancy, on-demand. Root disk is a separate aws_ebs_volume.",),
    )
