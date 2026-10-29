"""CloudFront. Traffic is not in the plan, so the line is zero."""

from tf_cost.models import PlannedResource, PriceQuote


def quote_cloudfront(resource: PlannedResource) -> PriceQuote:
    """Price aws_cloudfront_distribution as usage-dependent."""
    del resource
    return PriceQuote(
        0.0,
        1,
        "cloudfront:usage",
        (
            "highly usage-dependent; $0.085/GB for the first 10 TB to the internet "
            "is not included because the plan has no traffic",
        ),
    )
