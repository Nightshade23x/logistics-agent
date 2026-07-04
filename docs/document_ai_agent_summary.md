# Document AI Agent Summary

## Current Version

Document AI Agent V1.3 is complete.

The Document AI Agent extracts and validates trade/shipping document information. It follows the shared multi-agent contract and prepares handoff data for Logistics, Finance, Compliance, and User Agent.

## Main Capabilities

- Detects document type:
  - invoice
  - packing list
  - bill of lading
  - certificate of origin
  - unknown

- Extracts key fields:
  - invoice number
  - packing list number
  - bill of lading number
  - certificate number
  - supplier / shipper / exporter
  - buyer / consignee / importer
  - origin country
  - destination country
  - port of loading
  - port of discharge
  - container number
  - seal number
  - currency
  - total value
  - total weight

- Extracts item data:
  - product name
  - quantity
  - dimensions
  - unit weight
  - total weight

- Validates single documents.
- Compares invoice and packing list consistency.
- Detects quantity, item, weight, supplier, origin, and destination mismatches.
- Checks whether required shipping documents are present.
- Routes automatically based on uploaded documents:
  - one document: single document extraction
  - invoice + packing list: pair validation
  - multiple documents: document set completeness check

## Main Files

- app/document_parser.py: Parses document text and extracts fields/items.
- app/document_validator.py: Validates a single document.
- app/document_consistency.py: Compares invoice and packing list.
- app/document_pair_service.py: Runs invoice vs packing list validation.
- app/document_set_service.py: Checks required document completeness.
- app/document_ai_router.py: Main router for Document AI.
- app/document_service.py: Main single-document service.
- scripts/run_document_agent.py: Runs one document.
- scripts/run_document_pair_agent.py: Runs invoice + packing list.
- scripts/run_document_set_agent.py: Runs document set completeness check.
- scripts/run_document_ai.py: Main automatic router runner.
- scripts/test_document_agent.py: Tests Document AI features.
- data/documents/: Sample trade/shipping documents.

## How to Run Tests

```powershell
python scripts\test_document_agent.py
