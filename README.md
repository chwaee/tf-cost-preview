# tf-cost-preview

Estimate the monthly AWS run rate of a Terraform plan before apply. It reads `terraform show -json` output and prices the resources it knows with a checked-in us-east-1 on-demand rate card. No AWS account, no API calls, no network.

Use it in a client review when the question is "what will this plan cost to run," not "what is the invoice."

## Install

Python 3.11 or newer.

```bash
pip install .
tf-cost --help
```

`pipx install .` works the same way.

Development install:

```bash
uv sync
uv run tf-cost --help
```

## Usage

Save a plan, then estimate it:

```bash
terraform plan -out=tfplan && terraform show -json tfplan > plan.json
tf-cost plan.json
tf-cost --format json < plan.json
tf-cost --format table < plan.json
tf-cost --currency USD < plan.json
tf-cost --include-unpriced < plan.json
terraform show -json tfplan | tf-cost
```

Run terraform show -json tfplan | tf-cost after applying a HarderAWS plan to see the guardrail costs.

`--format` chooses stdout. The default is `table`. JSON is one document with `schema_version` `1.0`. `--currency` accepts only `USD`. `--include-unpriced` adds resources that have no rate card to the table at `$0.00`. Those resources are always present in the JSON `unpriced` array, so the flag is a display switch.

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | A report was written. Unknown resource types do not fail the run. |
| 2 | The estimate could not start: missing file, empty input, invalid JSON, a state file instead of a plan, or a currency other than USD. |

Pass a plan file, `-`, or a pipe. With no path and a terminal on stdin, the command exits 2.

## How to read the total

The total is the monthly run rate of resources this plan creates, updates, or replaces. It is not the difference from the current bill. A tag-only update still lists that resource's full run rate. Deletes are listed at `$0.00` with the prior run rate in the notes.

Dollar amounts are directional. `rate_source` in the JSON names the card entry. Compute prices are the public hourly rate times 730 hours, rounded to the cent. The application load balancer line is a low-traffic baseline, not a measured LCU bill.

JSON reports use `schema_version` `1.0` on the document and inside `metadata`.

## Supported resources

| Terraform type | What is priced | What is not |
| --- | --- | --- |
| `aws_instance` | `instance_type` for t3, t3a, m5, m5a, m6i, c5, r5, g4dn, g5, inf1, trn1 | EBS volumes, data transfer, spot, reserved |
| `aws_db_instance` | Instance class for MySQL, MariaDB, PostgreSQL, and a short Aurora list; `allocated_storage`; Multi-AZ | Backups, PIOPS beyond io1/io2, license for Oracle and SQL Server, Aurora storage and I/O |
| `aws_ebs_volume` | Size and type (gp3, gp2, io1, io2, st1, sc1, standard). io1/io2 add provisioned IOPS | Extra gp3 IOPS and throughput, snapshots of the volume |
| `aws_ebs_snapshot` | `volume_size` at $0.05/GB-month | Incremental savings versus the full volume |
| `aws_lb`, `aws_alb` | Application baseline $26.50; network hourly base $26.28 | Measured LCU or processed bytes. Gateway load balancers are $0 |
| `aws_nat_gateway` | $32.85 hourly base | $0.045/GB processed |
| `aws_eip`, `aws_elastic_ip` | $0 while associated; $3.65 when unattached or unknown | The running instance it points at |
| `aws_route53_zone` | $0.50 per hosted zone, public or private | Queries, health checks, resolver endpoints |
| `aws_secretsmanager_secret` | $0.40 per secret, plus $0.40 per replica | API calls |
| `aws_s3_bucket` | Listed at $0 | Storage and requests. The note has the list rates |
| `aws_dynamodb_table` | Provisioned RCU and WCU hours | On-demand request volume |
| `aws_lambda_function` | Listed at $0 | GB-seconds and invocations |
| `aws_elasticache_replication_group` | Redis OSS node price times node count for cache.t3.micro, cache.t3.small, cache.m5.large, cache.r5.large | Valkey discount, backups, transfer |
| `aws_redshift_cluster` | Node price times `number_of_nodes` for dc2.large, dc2.8xlarge, ra3.xlplus, ra3.4xlarge | RA3 managed storage |
| `aws_sns_topic` | Listed at $0 | Publishes and deliveries |
| `aws_sqs_queue` | Listed at $0 | Requests |
| `aws_cloudfront_distribution` | Listed at $0 | Data transfer |

An `aws_*` type that is not in the table is skipped and counted under "no rate card." Pass `--include-unpriced` to print those rows.

`multi_az = true` on `aws_db_instance` doubles the instance rate and the storage line. The standby holds a second copy of storage, and the RDS price list bills that copy.

## Pricing notes

Rates are us-east-1 public on-demand prices. They are a pre-apply conversation, not a bill.

- EC2 is Linux, shared tenancy. Unknown instance types are $0 and say `unknown instance type, manual review required`.
- RDS MySQL and MariaDB share a map. PostgreSQL is separate. Aurora prices instance hours only.
- EBS defaults to gp3 at $0.08/GB-month when `type` is absent. io1 and io2 add $0.065 per provisioned IOPS-month.
- RDS gp2 and gp3 storage are $0.115/GB-month. There is no flat database fee.
- DynamoDB provisioned capacity is $0.00013 per RCU-hour and $0.00065 per WCU-hour.
- SNS and SQS have no monthly flat fee. Idle topics and queues are $0.
- The plan's region is recorded in `region_assumptions` and does not change the rate.
- Data transfer, Savings Plans, reserved instances, and spot are omitted.

## Limits

- One plan per run. The tool does not call AWS and does not apply the plan.
- Updates are priced at the after-apply run rate of that resource, including tag-only changes.
- Usage-dependent resources stay at $0 rather than inventing traffic.
- Oracle and SQL Server use the MySQL compute rate and say that license cost is not included.
- This is not the AWS Pricing Calculator. Confirm anything a finance owner would sign in the calculator.

## Development

```bash
uv sync
make lint
make test
```

`make test` runs pytest with coverage and fails under 80%. `make format` applies ruff. Tests use fixtures under `tests/fixtures/`. They do not call AWS.

## Consulting

I run this against a plan before apply and walk through the lines that move the total, including the ones the card refuses to guess. The output is this report, plus the conversation about which numbers are firm and which are usage.

CONTACT: hello@appliedaiconsulting.io
