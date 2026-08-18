from app.frontend_response_cleanup import cleanup_frontend_response


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS - {message}")


def base_payload():
    return {
        "detected_intent": "logistics",
        "status": "review_required",
        "decision": "review_required",
        "logistics_quality_review": {"status": "clear"},
        "trade_terms_advice": {"status": "clear", "incoterm": "FOB"},
        "insurance_advice": {"status": "review_required", "warnings": []},
        "document_requirements_advice": {
            "status": "needs_more_information",
            "missing_or_unconfirmed_documents": [
                "Commercial invoice",
                "Packing list",
                "Bill of lading or airway bill",
            ],
        },
        "landed_cost_advice": {
            "status": "blocked",
            "known_inputs": {},
            "missing_cost_inputs": ["procurement_value_usd", "freight_quote_usd"],
            "blockers": ["Procurement value or declared value is missing."],
            "warnings": [],
        },
        "trade_compliance_readiness": {
            "status": "blocked",
            "blockers": [
                "Product ceramic tiles could not be classified into an HS code; the default duty rate was used instead."
            ],
            "warnings": ["No known free trade agreement between India and Germany on file."],
            "missing_information": [],
            "user_questions": [],
        },
        "clarification_questions": [],
    }


payload = cleanup_frontend_response(
    base_payload(),
    "Ship 10 crates of ceramic tiles from India to Germany. Declared value is 5000 USD. Use FOB incoterm.",
)
booking = payload["booking_readiness"]
check(
    not any("procurement" in str(x).lower() and "missing" in str(x).lower()
            for x in booking.get("booking_requirements", [])),
    "Declared value sentence clears stale procurement-value booking requirement",
)
check(booking["ready_for_first_pass"] is True, "soft HS classification issue still allows Ready for review")
check(booking["ready_for_booking"] is False, "HS classification fallback still prevents Ready to book until HS code is supplied")


payload = cleanup_frontend_response(
    base_payload(),
    "Ship 10 crates of ceramic tiles from India to Germany. Declared value is 5000 USD. Use FOB incoterm. Use HS code 6907.",
)
booking = payload["booking_readiness"]
check(payload.get("hs_code") == "6907", "Explicit HS code is captured")
check(booking["ready_for_booking"] is True, "Declared value + explicit HS code can reach Ready to book when no hard blocker remains")


radioactive = base_payload()
radioactive["landed_cost_advice"] = {
    "status": "review_required",
    "known_inputs": {"procurement_value_usd": 10000},
    "missing_cost_inputs": [],
    "blockers": [],
    "warnings": [],
}
radioactive["trade_compliance_readiness"] = {
    "status": "blocked",
    "blockers": [
        "Radioactive Class 7 cargo is blocked pending competent-authority approval, certified packaging, security controls, and carrier acceptance."
    ],
    "warnings": [],
    "missing_information": [],
    "user_questions": [],
}

payload = cleanup_frontend_response(
    radioactive,
    "Ship radioactive laboratory material from India to Germany. Declared value is 10000 USD. Use FOB incoterm.",
)
booking = payload["booking_readiness"]
check(booking["ready_for_booking"] is False, "Radioactive compliance blocker prevents Ready to book")
check(booking["ready_for_first_pass"] is False, "Radioactive compliance blocker prevents Ready for review")
check(booking.get("hard_blockers"), "Radioactive blocker remains explicitly classified as hard")

print("All V92 readiness reconciliation backend tests passed.")
