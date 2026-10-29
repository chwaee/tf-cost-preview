"""Lambda functions. Invocations and duration are not in the plan."""

from tf_cost.models import PlannedResource, PriceQuote
from tf_cost.pricing.common import whole_number


def quote_lambda(resource: PlannedResource) -> PriceQuote:
    """Price aws_lambda_function as usage-dependent."""
    notes = [
        "usage-dependent, estimate requires invocation metrics. "
        "Compute is $0.0000166667 per GB-second and requests are $0.20 per million",
    ]
    memory = whole_number(resource, "memory_size")
    if memory is not None:
        notes.append(f"memory_size is {memory} MB")
    return PriceQuote(0.0, 1, "lambda:usage", tuple(notes))
