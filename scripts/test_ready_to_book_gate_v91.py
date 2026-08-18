from app.booking_readiness_advisor import build_booking_readiness


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS - {message}")


def review(**sections):
    payload = {"detected_intent": "logistics"}
    payload.update(sections)
    return build_booking_readiness(payload)


# 1. Informational warnings must not block booking readiness.
result = review(
    trade_terms_advice={
        "status": "review_required",
        "warnings": [
            "No known free trade agreement between India and Germany on file.",
            "Gemini reasoning was unavailable; deterministic fallback was used.",
        ],
    }
)
check(result["ready_for_booking"] is True, "informational FTA/Gemini warnings do not block Ready to book")
check(not result["booking_requirements"], "informational warnings create no booking requirements")


# 2. Document-pack items are follow-up, not pre-booking blockers.
result = review(
    document_requirements_advice={
        "status": "needs_more_information",
        "missing_or_unconfirmed_documents": [
            "Commercial invoice",
            "Packing list",
            "Bill of lading or airway bill",
        ],
    }
)
check(result["ready_for_booking"] is True, "document-pack items do not block Ready to book")
check(len(result["pre_dispatch_items"]) >= 3, "document-pack items remain visible as pre-dispatch follow-up")


# 3. Declared/procurement value remains a real booking requirement.
result = review(
    landed_cost_advice={
        "status": "blocked",
        "blockers": ["Procurement value or declared value is missing."],
        "missing_cost_inputs": ["procurement_value_usd"],
    }
)
check(result["ready_for_booking"] is False, "missing declared/procurement value blocks Ready to book")
check(result["ready_for_first_pass"] is True, "missing cargo value does not block Ready for review")
check(result["booking_missing_items"], "missing cargo value appears in booking requirements")


# 4. Full landed-cost workflows require their finance inputs.
payload = {
    "detected_intent": "finance",
    "request_metadata": {"input_source": "Estimate landed cost for this shipment."},
    "landed_cost_advice": {
        "status": "needs_more_information",
        "missing_cost_inputs": ["freight_quote_usd", "insurance_premium_usd"],
    },
}
result = build_booking_readiness(payload)
check(result["ready_for_booking"] is False, "landed-cost workflow requires missing finance inputs")
check(len(result["booking_missing_items"]) >= 2, "missing finance inputs are named")


# 5. Genuine compliance blockers remain hard blockers.
result = review(
    trade_compliance_readiness={
        "status": "blocked",
        "blockers": ["Restricted cargo requires an import permit before movement."],
    }
)
check(result["ready_for_booking"] is False, "hard compliance blocker prevents Ready to book")
check(result["ready_for_first_pass"] is False, "hard compliance blocker prevents Ready for review")
check(result["hard_blockers"], "hard blocker is explicitly exposed")


# 6. HS-code uncertainty remains a booking-critical specialist check.
result = review(
    trade_compliance_readiness={
        "status": "review_required",
        "warnings": ["Product could not be automatically classified into an HS code; default duty rate was used."],
    }
)
check(result["ready_for_booking"] is False, "HS-code uncertainty still requires confirmation before Ready to book")
check(result["ready_for_first_pass"] is True, "HS-code uncertainty still allows Ready for review")
check(result["booking_review_items"], "HS-code review is named as a booking review item")


# 7. A clear shipment reaches the final gate.
result = review(
    logistics_quality_review={"status": "clear"},
    trade_terms_advice={"status": "clear"},
    trade_compliance_readiness={"status": "clear"},
)
check(result["ready_for_booking"] is True, "fully clear shipment reaches Ready to book")
check(result["status"] == "ready_for_booking_review", "final booking status is explicit")

print("All V91 ready-to-book gate backend tests passed.")
