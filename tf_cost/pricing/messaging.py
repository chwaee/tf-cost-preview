"""SNS topics and SQS queues. An idle topic or queue has no monthly flat fee."""

from tf_cost.models import PlannedResource, PriceQuote


def quote_sns(resource: PlannedResource) -> PriceQuote:
    """Price aws_sns_topic. Publish volume is not in the plan."""
    del resource
    return PriceQuote(
        0.0,
        1,
        "sns:usage",
        ("usage-dependent. Standard publishes are $0.50 per million; deliveries are extra",),
    )


def quote_sqs(resource: PlannedResource) -> PriceQuote:
    """Price aws_sqs_queue. Request volume is not in the plan."""
    del resource
    return PriceQuote(
        0.0,
        1,
        "sqs:usage",
        (
            "usage-dependent. Standard requests are $0.40 per million after the free tier; "
            "FIFO requests are $0.50 per million",
        ),
    )
