"""Command line entry point for tf-cost."""

import argparse
import json
import sys
from pathlib import Path

from tf_cost.parser import PlanError
from tf_cost.report import build_report, render_json, render_table

EPILOG = """
examples:
  terraform plan -out=tfplan && terraform show -json tfplan > plan.json
  tf-cost plan.json
  tf-cost --format json < plan.json
  tf-cost --format table < plan.json
  tf-cost --currency USD < plan.json
  tf-cost --include-unpriced < plan.json
  terraform show -json tfplan | tf-cost

Run terraform show -json tfplan | tf-cost after a HarderAWS plan to see the guardrail costs.
""".strip()


def build_parser() -> argparse.ArgumentParser:
    """Parser for tf-cost. Help text includes the worked examples."""
    parser = argparse.ArgumentParser(
        prog="tf-cost",
        description="Estimate monthly AWS cost from a Terraform plan.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    parser.add_argument(
        "plan",
        nargs="?",
        help="Path to terraform show -json output. Omit or pass - to read stdin.",
    )
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format written to stdout. Default: table.",
    )
    parser.add_argument(
        "--currency",
        default="USD",
        help="Currency code. Only USD is supported. Default: USD.",
    )
    parser.add_argument(
        "--include-unpriced",
        action="store_true",
        help="List resources with no rate card in the table at $0.00.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns 0 when a report is written, 2 when input is unusable."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 0

    currency = str(args.currency).upper()
    if currency != "USD":
        print("error: only USD is supported", file=sys.stderr)
        return 2

    try:
        raw = _read_input(args.plan)
        document = json.loads(raw)
        report = build_report(document)
    except PlanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError:
        print("error: plan is not valid JSON", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        sys.stdout.write(render_json(report))
    else:
        sys.stdout.write(render_table(report, include_unpriced=args.include_unpriced))
    return 0


def _read_input(path: str | None) -> str:
    if path is None or path == "-":
        if path is None and sys.stdin.isatty():
            raise PlanError("pass a plan file or pipe terraform show -json output")
        raw = sys.stdin.read()
    else:
        file = Path(path)
        if not file.is_file():
            raise PlanError(f"plan file not found: {path}")
        raw = file.read_text(encoding="utf-8")
    if not raw.strip():
        raise PlanError("plan input is empty")
    return raw
