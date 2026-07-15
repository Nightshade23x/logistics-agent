from fastapi import FastAPI

from finance_agent.finance_agent.models.shipment import Shipment
from finance_agent.finance_agent.routers.finance_router import FinanceRouter
from finance_agent.finance_agent.models.finance_report import FinanceReport
from finance_agent.finance_agent.schemas.currency import CurrencyConversionRequest


app = FastAPI(title="Finance Agent")

router = FinanceRouter()


@app.get("/")
def home():
    return {"agent": "Finance Agent", "status": "running"}


@app.post("/finance/import-duty")
def import_duty(shipment: Shipment):
    return {"import_duty": router.get_import_duty(shipment)}


@app.post("/finance/tax")
def tax(shipment: Shipment):
    return {"tax": router.get_tax(shipment)}


@app.post("/finance/freight")
def freight(shipment: Shipment):
    return {"freight": router.get_freight_cost(shipment)}


@app.post("/finance/insurance")
def insurance(shipment: Shipment):
    return {"insurance": router.get_insurance_cost(shipment)}



@app.post("/finance/landed-cost")
def landed_cost(report: FinanceReport):
    return {"landed_cost": router.get_landed_cost(report)}

@app.post("/finance/profit")
def profit(
    report: FinanceReport,
    selling_price: float
):
    return {
        "profit": router.get_profit(report, selling_price)
    }

@app.post("/finance/currency")
def currency(request: CurrencyConversionRequest):
    return {
        "converted_value": router.convert_currency(request)
    }


@app.post("/finance/report")
def report(shipment: Shipment, selling_price: float | None = None):
    return router.generate_report(shipment, selling_price)

@app.post("/finance/roi")
def roi(
    report: FinanceReport,
    selling_price: float
):
    return {
        "roi_percent": router.get_roi(report, selling_price)
    }

@app.get("/health")
def health():
    """Simple liveness check for orchestration and monitoring."""
    return {"status": "ok", "agent": "finance_agent"}