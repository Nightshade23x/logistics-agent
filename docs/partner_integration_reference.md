# Partner Agent Integration Reference

## Partner Agents

### Risk Agent
- Assesses country-level trade risk.
- Uses Transparency International CPI corruption risk.
- Checks sanctions status and active sanctions programs.
- Runs as an MCP server.

### Compliance Agent
- Checks whether a product is allowed, restricted, prohibited, or needs permits/certificates.
- Uses product hazard data, UN numbers, required documentation, and country-specific trade restrictions.
- Runs as an MCP server.

### Trader Agent
- Classifies products into HS codes.
- Estimates duty rates.
- Checks Free Trade Agreements.
- Suggests export strategy.
- Runs as an MCP server.

### Finance Agent
- Calculates freight cost, insurance, duty, taxes, landed cost, and ROI.
- Runs as a REST API.

## Integration Notes

Our side currently has:
- User Agent
- Shopping Agent
- Document AI Agent
- Logistics Agent

Partner side has:
- Risk Agent
- Compliance Agent
- Trader Agent
- Finance Agent

Risk, Compliance, and Trader should be called through MCP clients.
Finance should be called through a REST client.

## Future Adapter Files

Possible adapter structure:
- app/partner_adapters/risk_client.py
- app/partner_adapters/compliance_client.py
- app/partner_adapters/trader_client.py
- app/partner_adapters/finance_client.py

The User Agent should call these adapters, not directly mix partner code into our agents.

## Future Flow

User request
-> User Agent
-> Shopping / Document AI / Logistics
-> Risk / Compliance / Trader / Finance
-> Final combined answer

## Key Rule

Frontend is only the interface.
User Agent is the orchestrator.
Specialist agents should stay focused on their own domain.
