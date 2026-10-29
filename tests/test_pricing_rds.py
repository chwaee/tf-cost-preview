"""RDS and Aurora rate card lookups."""

from tf_cost.pricing.rds import quote_db_instance

from tests.support import planned


def _db(**values: object):
    return planned("aws_db_instance", values)


def test_mysql_micro_includes_gp3_storage():
    quote = quote_db_instance(
        _db(
            engine="mysql",
            instance_class="db.t3.micro",
            allocated_storage=20,
            storage_type="gp3",
            multi_az=False,
        )
    )
    # 0.017 * 730 = 12.41; 20 GB * 0.115 = 2.30.
    assert quote.monthly_usd == 14.71
    assert quote.rate_source == "rds:us-east-1:mysql:db.t3.micro"


def test_postgres_micro_uses_the_postgres_map():
    quote = quote_db_instance(
        _db(engine="postgres", instance_class="db.t3.micro", allocated_storage=0)
    )
    assert quote.monthly_usd == 13.14


def test_mariadb_uses_the_mysql_rate():
    quote = quote_db_instance(
        _db(engine="mariadb", instance_class="db.m5.large", allocated_storage=0)
    )
    assert quote.monthly_usd == 124.83


def test_multi_az_doubles_instance_and_storage():
    single = quote_db_instance(
        _db(
            engine="mysql",
            instance_class="db.t3.micro",
            allocated_storage=20,
            storage_type="gp3",
            multi_az=False,
        )
    )
    doubled = quote_db_instance(
        _db(
            engine="mysql",
            instance_class="db.t3.micro",
            allocated_storage=20,
            storage_type="gp3",
            multi_az=True,
        )
    )
    assert single.monthly_usd == 14.71
    assert doubled.monthly_usd == 29.42
    assert any("second copy of storage" in note for note in doubled.notes)


def test_aurora_skips_storage():
    quote = quote_db_instance(
        _db(
            engine="aurora-mysql",
            instance_class="db.r5.large",
            allocated_storage=100,
            storage_type="gp3",
        )
    )
    assert quote.monthly_usd == 211.70
    assert quote.rate_source == "rds:us-east-1:aurora:db.r5.large"
    assert any("usage-dependent" in note for note in quote.notes)


def test_aurora_t3_medium():
    quote = quote_db_instance(_db(engine="aurora-postgresql", instance_class="db.t3.medium"))
    assert quote.monthly_usd == 59.86


def test_unknown_class_is_zero_without_storage():
    quote = quote_db_instance(_db(engine="mysql", instance_class="db.x9.mega"))
    assert quote.monthly_usd == 0
    assert any("unknown instance class" in note for note in quote.notes)


def test_oracle_uses_mysql_compute_and_says_license_is_excluded():
    quote = quote_db_instance(
        _db(engine="oracle-se2", instance_class="db.t3.micro", allocated_storage=0)
    )
    assert quote.monthly_usd == 12.41
    assert any("license" in note for note in quote.notes)


def test_missing_storage_does_not_invent_a_flat_fee():
    quote = quote_db_instance(_db(engine="mysql", instance_class="db.t3.micro"))
    assert quote.monthly_usd == 12.41
    assert any("allocated storage" in note for note in quote.notes)


def test_io1_storage_adds_provisioned_iops():
    quote = quote_db_instance(
        _db(
            engine="mysql",
            instance_class="db.t3.micro",
            allocated_storage=100,
            storage_type="io1",
            iops=1000,
        )
    )
    # 12.41 + 100 * 0.125 + 1000 * 0.10 = 12.41 + 12.50 + 100 = 124.91
    assert quote.monthly_usd == 124.91
