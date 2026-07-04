"""One-off manual check for destination-aware compliance. Not part of the test suite."""

from compliance_agent.container import build_container
from compliance_agent.schemas.compliance import ComplianceCheckRequest

container = build_container()

test_cases = [
    ("lithium batteries", "Iran"),      # expect destination_restricted=True (comprehensive)
    ("lithium batteries", "Russia"),    # expect destination_restricted=True (keyword match)
    ("lithium batteries", "Germany"),   # expect destination_restricted=False (no data on file)
    ("lithium batteries", None),        # expect old behavior, unchanged
]

for product, destination in test_cases:
    print(f"\n{'=' * 60}\nProduct: {product} | Destination: {destination}\n{'=' * 60}")
    request = ComplianceCheckRequest(product_description=product, destination_country=destination)
    result = container.compliance_service.check(request)
    print(result.model_dump_json(indent=2))