"""One-off manual check for assess_trade_risk. Not part of the test suite."""

from risk_agent.container import build_container

container = build_container()

for country in ["Brazil", "Russia", "Somalia", "Not A Real Country"]:
    print(f"\n{'=' * 60}\n{country}\n{'=' * 60}")
    result = container.risk_assessment_service.assess(country)
    print(result.model_dump_json(indent=2))