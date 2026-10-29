"""Rate cards other than EC2 and RDS."""

from tests.support import planned
from tf_cost.pricing.cache import quote_elasticache
from tf_cost.pricing.cdn import quote_cloudfront
from tf_cost.pricing.compute import quote_lambda
from tf_cost.pricing.datawarehousing import quote_redshift
from tf_cost.pricing.dns import quote_route53_zone
from tf_cost.pricing.ebs import quote_snapshot, quote_volume
from tf_cost.pricing.lb import quote_lb
from tf_cost.pricing.messaging import quote_sns, quote_sqs
from tf_cost.pricing.networking import quote_eip, quote_nat_gateway
from tf_cost.pricing.security import quote_secret
from tf_cost.pricing.storage import quote_dynamodb, quote_s3


def test_ebs_rates_and_default_type():
    assert quote_volume(planned("aws_ebs_volume", {"size": 100, "type": "gp3"})).monthly_usd == 8
    assert quote_volume(planned("aws_ebs_volume", {"size": 100, "type": "gp2"})).monthly_usd == 10
    assert quote_volume(planned("aws_ebs_volume", {"size": 1000, "type": "st1"})).monthly_usd == 45
    assert quote_volume(planned("aws_ebs_volume", {"size": 1000, "type": "sc1"})).monthly_usd == 15
    default = quote_volume(planned("aws_ebs_volume", {"size": 10}))
    assert default.monthly_usd == 0.8
    assert any("gp3" in note for note in default.notes)


def test_ebs_io1_includes_provisioned_iops():
    quote = quote_volume(planned("aws_ebs_volume", {"size": 100, "type": "io1", "iops": 1000}))
    assert quote.monthly_usd == 77.5


def test_ebs_missing_size_is_zero():
    quote = quote_volume(planned("aws_ebs_volume", {}))
    assert quote.monthly_usd == 0
    assert any("size" in note for note in quote.notes)


def test_snapshot_uses_volume_size():
    quote = quote_snapshot(planned("aws_ebs_snapshot", {"volume_size": 100}))
    assert quote.monthly_usd == 5
    missing = quote_snapshot(planned("aws_ebs_snapshot", {}))
    assert missing.monthly_usd == 0


def test_load_balancer_types():
    application = quote_lb(planned("aws_lb", {"load_balancer_type": "application"}))
    network = quote_lb(planned("aws_lb", {"load_balancer_type": "network"}))
    gateway = quote_lb(planned("aws_lb", {"load_balancer_type": "gateway"}))
    default = quote_lb(planned("aws_alb", {}))
    assert application.monthly_usd == 26.5
    assert network.monthly_usd == 26.28
    assert gateway.monthly_usd == 0
    assert default.monthly_usd == 26.5
    assert any("LCU" in note for note in application.notes)
    assert any("no rate card" in note for note in gateway.notes)


def test_nat_gateway_is_the_hourly_base():
    quote = quote_nat_gateway(planned("aws_nat_gateway"))
    assert quote.monthly_usd == 32.85
    assert any("0.045" in note for note in quote.notes)


def test_eip_attachment_states():
    attached = quote_eip(planned("aws_eip", {"instance": "i-abc"}))
    unattached = quote_eip(planned("aws_elastic_ip", {"instance": None, "network_interface": None}))
    unknown = quote_eip(planned("aws_eip", unknown={"instance"}))
    assert attached.monthly_usd == 0
    assert unattached.monthly_usd == 3.65
    assert unknown.monthly_usd == 3.65
    assert any("free" in note for note in attached.notes)
    assert any("unknown" in note for note in unknown.notes)


def test_usage_priced_resources_stay_at_zero():
    s3 = quote_s3(planned("aws_s3_bucket"))
    function = quote_lambda(planned("aws_lambda_function", {"memory_size": 256}))
    topic = quote_sns(planned("aws_sns_topic"))
    queue = quote_sqs(planned("aws_sqs_queue"))
    distribution = quote_cloudfront(planned("aws_cloudfront_distribution"))
    on_demand = quote_dynamodb(planned("aws_dynamodb_table", {"billing_mode": "PAY_PER_REQUEST"}))
    assert s3.monthly_usd == topic.monthly_usd == queue.monthly_usd == 0
    assert function.monthly_usd == distribution.monthly_usd == on_demand.monthly_usd == 0
    assert any("requires size input" in note for note in s3.notes)
    assert any("memory_size is 256 MB" in note for note in function.notes)
    assert any("usage-dependent" in note for note in topic.notes)
    assert any("0.40" in note for note in queue.notes)
    assert any("0.085" in note for note in distribution.notes)


def test_dynamodb_provisioned_capacity():
    quote = quote_dynamodb(
        planned(
            "aws_dynamodb_table",
            {"billing_mode": "PROVISIONED", "read_capacity": 5, "write_capacity": 5},
        )
    )
    assert quote.monthly_usd == 2.85
    assert quote.rate_source == "dynamodb:provisioned"


def test_elasticache_node_count():
    quote = quote_elasticache(
        planned(
            "aws_elasticache_replication_group",
            {"node_type": "cache.t3.micro", "num_cache_clusters": 3},
        )
    )
    assert quote.quantity == 3
    assert quote.monthly_usd == 37.23
    assert any("Valkey" in note for note in quote.notes)


def test_elasticache_unknown_node_is_zero():
    quote = quote_elasticache(
        planned("aws_elasticache_replication_group", {"node_type": "cache.z9.mega"})
    )
    assert quote.monthly_usd == 0


def test_redshift_node_count():
    single = quote_redshift(planned("aws_redshift_cluster", {"node_type": "dc2.large"}))
    pair = quote_redshift(
        planned("aws_redshift_cluster", {"node_type": "dc2.large", "number_of_nodes": 2})
    )
    ra3 = quote_redshift(planned("aws_redshift_cluster", {"node_type": "ra3.xlplus"}))
    assert single.monthly_usd == 182.5
    assert single.quantity == 1
    assert pair.monthly_usd == 365
    assert pair.quantity == 2
    assert ra3.monthly_usd == 792.78
    assert any("Managed Storage" in note for note in ra3.notes)


def test_route53_public_and_private_zones_share_the_rate():
    public = quote_route53_zone(planned("aws_route53_zone", {"name": "example.com"}))
    private = quote_route53_zone(
        planned("aws_route53_zone", {"name": "internal", "vpc": [{"vpc_id": "vpc-1"}]})
    )
    assert public.monthly_usd == private.monthly_usd == 0.5
    assert any("0.40" in note for note in public.notes)
    assert any("private" in note for note in private.notes)


def test_secret_and_one_replica():
    single = quote_secret(planned("aws_secretsmanager_secret", {"name": "db"}))
    replicated = quote_secret(
        planned(
            "aws_secretsmanager_secret",
            {"name": "db", "replica": [{"region": "eu-west-1"}]},
        )
    )
    assert single.monthly_usd == 0.4
    assert single.quantity == 1
    assert replicated.monthly_usd == 0.8
    assert replicated.quantity == 2
