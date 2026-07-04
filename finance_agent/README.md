## Status

Fully implemented. Endpoints: `/finance/import-duty`, `/finance/tax`, `/finance/freight`,
`/finance/insurance`, `/finance/landed-cost`, `/finance/profit`, `/finance/currency`,
`/finance/report`, `/finance/roi`.

`CostEstimationService` composes freight, insurance, duty, and tax into a full
`FinanceReport`. `ReportService` accepts an optional `selling_price` to also
compute estimated profit. Test coverage: `pytest tests -v` (15 passing as of
last update, covering all services including edge cases like zero total cost
in ROI calculation).

Known limitations:
- Freight/insurance rates are seeded for a small set of routes (India-USA,
  India-Germany, China-USA); unseeded routes fall back to a flat estimated
  rate rather than a verified quote.
- Duty is computed independently of Trader Agent's HS-code-based rate unless
  called through the orchestrator, which reconciles the two.