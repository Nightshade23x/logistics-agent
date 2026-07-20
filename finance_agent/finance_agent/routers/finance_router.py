from finance_agent.finance_agent.container import (
    currency_service,
    freight_service,
    import_duty_service,
    insurance_service,
    landed_cost_service,
    profit_service,
    roi_service,
    tax_service,
    report_service)
from finance_agent.finance_agent.models import shipment


class FinanceRouter:
    """
    Entry point for the Finance Agent.
    """

    def get_freight_cost(self, shipment):
        return freight_service.execute(shipment)

    def get_insurance_cost(self, shipment):
        return insurance_service.execute(shipment)

    def get_import_duty(self, shipment):
        return import_duty_service.execute(shipment)

    def get_tax(self, shipment):
        return tax_service.execute(shipment)

    def convert_currency(self, request):
        return currency_service.execute(request)

    def get_landed_cost(self, report):
        return landed_cost_service.execute(report)

    def get_profit(self, report, selling_price):
        return profit_service.execute(report, selling_price)
    
    def generate_report(self, shipment, selling_price=None):
        return report_service.execute(shipment, selling_price)
    
    def get_roi(self, report, selling_price):
        return roi_service.execute(report, selling_price)