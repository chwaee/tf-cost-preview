"""RDS and Aurora instance hours plus provisioned storage.

Hourly rates are us-east-1, single-AZ, on-demand. MySQL and MariaDB share a
map. PostgreSQL is separate. Aurora is instance hours only.

multi_az doubles the instance rate and the storage line. The RDS for MySQL
price list bills Multi-AZ storage at twice the single-AZ rate because the
standby holds a second copy. Two readable standbys are a different deployment
and are not selected by multi_az on aws_db_instance.
"""

from decimal import Decimal

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import HOURS_PER_MONTH, flag, money, text, whole_number

# Hourly USD, single-AZ, us-east-1, on-demand.
MYSQL_HOURLY: dict[str, str] = {
    "db.t3.micro": "0.017",
    "db.t3.small": "0.034",
    "db.t3.medium": "0.068",
    "db.t3.large": "0.136",
    "db.m5.large": "0.171",
    "db.m5.xlarge": "0.342",
    "db.r5.large": "0.240",
    "db.m6i.large": "0.171",
}

POSTGRES_HOURLY: dict[str, str] = {
    "db.t3.micro": "0.018",
    "db.t3.small": "0.036",
    "db.t3.medium": "0.072",
    "db.t3.large": "0.145",
    "db.m5.large": "0.178",
    "db.m5.xlarge": "0.356",
    "db.r5.large": "0.250",
    "db.m6i.large": "0.178",
}

# Aurora standard instance hours. Storage and I/O are not on the instance.
AURORA_HOURLY: dict[str, str] = {
    "db.t3.medium": "0.082",
    "db.r5.large": "0.29",
}

# USD per GB-month, single-AZ. io1/io2 also charge provisioned IOPS.
STORAGE_GB: dict[str, str] = {
    "gp2": "0.115",
    "gp3": "0.115",
    "io1": "0.125",
    "io2": "0.125",
    "standard": "0.10",
}
IOPS_MONTH = Decimal("0.10")
IO_TYPES = {"io1", "io2"}


def _engine_family(engine: str | None) -> str:
    if engine is None:
        return "mysql"
    lowered = engine.lower()
    if lowered.startswith("aurora"):
        return "aurora"
    if lowered.startswith("postgres"):
        return "postgres"
    if "oracle" in lowered or "sqlserver" in lowered or "sql-server" in lowered:
        return "license"
    return "mysql"


def quote_db_instance(resource: PlannedResource) -> PriceQuote:
    """Price aws_db_instance compute and, for non-Aurora, provisioned storage."""
    notes: list[str] = []
    engine = text(resource, "engine")
    family = _engine_family(engine)
    if engine is None:
        notes.append("engine not set; compute priced at the MySQL rate")
    elif family == "license":
        notes.append("license cost is not included; compute is priced at the MySQL rate")
    elif family == "mysql" and engine.lower() not in {"mysql", "mariadb"}:
        notes.append(f"engine {engine} is priced at the MySQL rate")

    instance_class = text(resource, "instance_class")
    rate_map = {
        "aurora": AURORA_HOURLY,
        "postgres": POSTGRES_HOURLY,
        "license": MYSQL_HOURLY,
        "mysql": MYSQL_HOURLY,
    }[family]
    label = "aurora" if family == "aurora" else ("postgres" if family == "postgres" else "mysql")

    instance = Decimal("0")
    rate_source = "rds:unknown"
    if instance_class is None:
        notes.append("unknown instance class, manual review required")
    else:
        hourly = rate_map.get(instance_class.lower())
        if hourly is None:
            notes.append(f"unknown instance class, manual review required: {instance_class}")
        else:
            instance = Decimal(hourly) * HOURS_PER_MONTH
            rate_source = f"rds:us-east-1:{label}:{instance_class.lower()}"

    storage = Decimal("0")
    if family == "aurora":
        notes.append("Aurora storage and I/O are usage-dependent and not included")
    else:
        storage = _storage(resource, notes)

    multi_az = flag(resource, "multi_az")
    if multi_az is True:
        instance *= 2
        storage *= 2
        notes.append("Multi-AZ bills the standby instance and a second copy of storage")
    elif multi_az is None and resource.is_unknown("multi_az"):
        notes.append("multi_az is unknown; priced as single-AZ")

    return PriceQuote(
        money(instance + storage),
        1,
        rate_source,
        tuple(notes),
    )


def _storage(resource: PlannedResource, notes: list[str]) -> Decimal:
    size = whole_number(resource, "allocated_storage")
    if size is None:
        if resource.is_unknown("allocated_storage"):
            notes.append("allocated storage is unknown at plan time")
        else:
            notes.append("allocated storage not in the plan")
        return Decimal("0")

    storage_type = text(resource, "storage_type")
    if storage_type is None:
        storage_type = "gp3"
        notes.append("storage type not set; using gp3 at $0.115 per GB-month")
    else:
        storage_type = storage_type.lower()
    rate = STORAGE_GB.get(storage_type)
    if rate is None:
        notes.append(f"unknown storage type {storage_type}; storage priced at gp3")
        rate = STORAGE_GB["gp3"]
        storage_type = "gp3"

    total = Decimal(rate) * Decimal(size)
    if storage_type in IO_TYPES:
        iops = whole_number(resource, "iops")
        if iops is None:
            notes.append("provisioned IOPS not set; IOPS charge not included")
        else:
            total += IOPS_MONTH * Decimal(iops)
    return total
