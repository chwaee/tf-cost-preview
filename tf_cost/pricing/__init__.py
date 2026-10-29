"""Deterministic us-east-1 on-demand rate card.

Add a resource type by writing quote() in a new module and registering it below.
The functions take a planned resource and return a PriceQuote. They do not read
the network.
"""

from collections.abc import Callable

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.cache import quote_elasticache
from tf_cost.pricing.cdn import quote_cloudfront
from tf_cost.pricing.compute import quote_lambda
from tf_cost.pricing.datawarehousing import quote_redshift
from tf_cost.pricing.dns import quote_route53_zone
from tf_cost.pricing.ebs import quote_snapshot, quote_volume
from tf_cost.pricing.ec2 import quote_instance
from tf_cost.pricing.lb import quote_lb
from tf_cost.pricing.messaging import quote_sns, quote_sqs
from tf_cost.pricing.networking import quote_eip, quote_nat_gateway
from tf_cost.pricing.rds import quote_db_instance
from tf_cost.pricing.security import quote_secret
from tf_cost.pricing.storage import quote_dynamodb, quote_s3

Pricer = Callable[[PlannedResource], PriceQuote]

REGISTRY: dict[str, Pricer] = {
    "aws_instance": quote_instance,
    "aws_db_instance": quote_db_instance,
    "aws_ebs_volume": quote_volume,
    "aws_ebs_snapshot": quote_snapshot,
    "aws_lb": quote_lb,
    "aws_alb": quote_lb,
    "aws_nat_gateway": quote_nat_gateway,
    "aws_eip": quote_eip,
    "aws_elastic_ip": quote_eip,
    "aws_cloudfront_distribution": quote_cloudfront,
    "aws_route53_zone": quote_route53_zone,
    "aws_secretsmanager_secret": quote_secret,
    "aws_s3_bucket": quote_s3,
    "aws_dynamodb_table": quote_dynamodb,
    "aws_lambda_function": quote_lambda,
    "aws_elasticache_replication_group": quote_elasticache,
    "aws_redshift_cluster": quote_redshift,
    "aws_sns_topic": quote_sns,
    "aws_sqs_queue": quote_sqs,
}


def quote(resource: PlannedResource) -> PriceQuote | None:
    """Price one resource, or return None when this card has no entry for the type."""
    pricer = REGISTRY.get(resource.resource_type)
    if pricer is None:
        return None
    return pricer(resource)
