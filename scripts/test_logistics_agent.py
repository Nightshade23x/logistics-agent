from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.item_resolver import resolve_items
from app.logistics_agent import CargoItem, build_logistics_plan, calculate_total_cbm, recommend_container
from app.logistics_service import run_logistics_agent
from app.text_shipment_parser import parse_shipment_text


def test_cbm_calculation():
    items = [
        CargoItem(
            name="Test Box",
            quantity=10,
            length_m=1,
            width_m=1,
            height_m=1,
            weight_kg=5,
        )
    ]

    assert calculate_total_cbm(items) == 10


def test_container_recommendation():
    items = [
        CargoItem(
            name="Small Cargo",
            quantity=10,
            length_m=0.5,
            width_m=0.5,
            height_m=0.5,
            weight_kg=5,
        )
    ]

    recommendation = recommend_container(items)
    assert recommendation["container_name"] == "20ft Standard Container"


def test_full_logistics_plan():
    raw_items = [
        {
            "name": "Glass bottles",
            "quantity": 10,
            "length_m": 0.3,
            "width_m": 0.3,
            "height_m": 0.4,
            "weight_kg": 2,
            "fragile": True,
        }
    ]

    plan = build_logistics_plan(raw_items)

    assert plan["shipment_summary"]["total_cbm"] == 0.36
    assert "fragile" in plan["item_breakdown"][0]["cargo_categories"]
    assert len(plan["loading_advice"]) > 0



def test_loading_sequence():
    raw_items = [
        {
            "name": "Ceramic tiles",
            "quantity": 100,
            "length_m": 0.6,
            "width_m": 0.6,
            "height_m": 0.08,
            "weight_kg": 12,
            "fragile": True,
            "stackable": True,
            "unload_priority": 3,
        },
        {
            "name": "Pillows",
            "quantity": 100,
            "length_m": 0.5,
            "width_m": 0.4,
            "height_m": 0.2,
            "weight_kg": 1,
            "unload_priority": 1,
        },
    ]

    plan = build_logistics_plan(raw_items)

    assert "loading_sequence" in plan
    assert len(plan["loading_sequence"]) == 2
    assert plan["loading_sequence"][0]["item_name"] == "Ceramic tiles"
    assert plan["loading_sequence"][0]["sequence_number"] == 1



def test_logistics_risk_assessment():
    raw_items = [
        {
            "name": "Glass bottles",
            "quantity": 10,
            "length_m": 0.3,
            "width_m": 0.3,
            "height_m": 0.4,
            "weight_kg": 2,
            "fragile": True,
        },
        {
            "name": "Scooter",
            "quantity": 2,
            "length_m": 1.8,
            "width_m": 0.7,
            "height_m": 1.1,
            "weight_kg": 90,
            "stackable": False,
        },
    ]

    plan = build_logistics_plan(raw_items)

    assert "logistics_risk" in plan
    assert plan["logistics_risk"]["risk_level"] in {"moderate", "high", "critical"}
    assert len(plan["logistics_risk"]["warnings"]) > 0
    assert len(plan["logistics_risk"]["requirements"]) > 0



def test_item_resolver_uses_catalog():
    raw_items = [
        {
            "name": "TVs",
            "quantity": 5,
        }
    ]

    resolution = resolve_items(raw_items)

    assert len(resolution["resolved_items"]) == 1
    assert resolution["resolved_items"][0]["length_m"] == 1.2
    assert resolution["resolved_items"][0]["fragile"] is True
    assert len(resolution["issues"]) == 1



def test_container_strategy():
    raw_items = [
        {
            "name": "Frozen food",
            "quantity": 20,
            "length_m": 0.5,
            "width_m": 0.4,
            "height_m": 0.3,
            "weight_kg": 10,
            "perishable": True,
        }
    ]

    plan = build_logistics_plan(raw_items)

    assert "container_strategy" in plan
    assert plan["container_strategy"]["strategy_type"] == "refrigerated_or_temperature_controlled"
    assert plan["container_strategy"]["priority"] == "high"
    assert len(plan["container_strategy"]["recommendations"]) > 0



def test_route_advisor_for_perishable_cargo():
    raw_items = [
        {
            "name": "Fresh food",
            "quantity": 10,
            "length_m": 0.5,
            "width_m": 0.4,
            "height_m": 0.3,
            "weight_kg": 8,
            "perishable": True,
        }
    ]

    plan = build_logistics_plan(
        raw_items,
        shipment_context={
            "origin": "India",
            "destination": "USA",
        },
    )

    assert "route_plan" in plan
    assert plan["route_plan"]["route_type"] == "temperature_sensitive_route"
    assert plan["route_plan"]["priority"] == "high"
    assert plan["route_plan"]["origin"] == "India"
    assert plan["route_plan"]["destination"] == "USA"



def test_container_layout():
    raw_items = [
        {
            "name": "Scooter",
            "quantity": 2,
            "length_m": 1.8,
            "width_m": 0.7,
            "height_m": 1.1,
            "weight_kg": 90,
            "stackable": False,
        },
        {
            "name": "Glass bottles",
            "quantity": 10,
            "length_m": 0.3,
            "width_m": 0.3,
            "height_m": 0.4,
            "weight_kg": 2,
            "fragile": True,
            "unload_priority": 1,
        },
    ]

    plan = build_logistics_plan(raw_items)

    assert "container_layout" in plan
    assert plan["container_layout"]["layout_type"] == "rule_based_zone_layout"
    assert len(plan["container_layout"]["zones"]) > 0



def test_logistics_service_contract():
    shipment_data = {
        "shipment_id": "TEST-SERVICE-001",
        "customer": "Test Customer",
        "origin": "India",
        "destination": "USA",
        "items": [
            {
                "name": "TVs",
                "quantity": 5,
            }
        ],
    }

    response = run_logistics_agent(shipment_data)

    assert response["agent_name"] == "logistics_agent"
    assert response["status"] in {
        "ready_for_review",
        "review_required",
        "critical_review_required",
        "partial_plan_needs_more_information",
        "needs_more_information",
    }
    assert response["plan"] is not None
    assert "report" in response
    assert "handoff_requests" in response
    assert any(
        request["target_agent"] == "financial_agent"
        for request in response["handoff_requests"]
    )



def test_packaging_plan():
    raw_items = [
        {
            "name": "Glass bottles",
            "quantity": 10,
            "length_m": 0.3,
            "width_m": 0.3,
            "height_m": 0.4,
            "weight_kg": 2,
            "fragile": True,
        }
    ]

    plan = build_logistics_plan(raw_items)

    assert "packaging_plan" in plan
    assert plan["packaging_plan"]["packaging_risk_level"] in {"moderate", "high", "critical"}
    assert "FRAGILE" in plan["packaging_plan"]["recommended_labels"]


def test_readiness_checklist():
    raw_items = [
        {
            "name": "TV",
            "quantity": 5,
            "length_m": 1.2,
            "width_m": 0.2,
            "height_m": 0.8,
            "weight_kg": 12,
            "fragile": True,
            "stackable": False,
        }
    ]

    plan = build_logistics_plan(
        raw_items,
        shipment_context={
            "origin": "India",
            "destination": "USA",
        },
    )

    assert "readiness_checklist" in plan
    assert "readiness_status" in plan["readiness_checklist"]
    assert len(plan["readiness_checklist"]["sections"]) >= 3



def test_container_options():
    raw_items = [
        {
            "name": "Small Cargo",
            "quantity": 10,
            "length_m": 0.5,
            "width_m": 0.5,
            "height_m": 0.5,
            "weight_kg": 5,
        }
    ]

    plan = build_logistics_plan(raw_items)

    assert "container_options" in plan
    assert len(plan["container_options"]) > 0
    assert "option_name" in plan["container_options"][0]


def test_handoff_payload():
    shipment_data = {
        "shipment_id": "TEST-HANDOFF-001",
        "customer": "Test Customer",
        "origin": "India",
        "destination": "USA",
        "items": [
            {
                "name": "TVs",
                "quantity": 5,
            }
        ],
    }

    response = run_logistics_agent(shipment_data)

    assert "handoff_payload" in response
    assert response["handoff_payload"]["total_cbm"] is not None
    assert response["handoff_payload"]["recommended_container"] is not None
    assert "cargo_categories" in response["handoff_payload"]



def test_text_shipment_parser():
    parsed = parse_shipment_text("10 cubic meters of tiles, 50 TVs, 5 scooters")

    assert len(parsed["items"]) == 3
    assert parsed["items"][0]["name"] == "tiles"
    assert parsed["items"][0]["total_cbm"] == 10
    assert parsed["items"][1]["quantity"] == 50


def test_text_input_runs_through_logistics_agent():
    parsed = parse_shipment_text("10 cubic meters of tiles, 50 TVs, 5 scooters")

    shipment_data = {
        "shipment_id": "TEST-TEXT-001",
        "customer": "Test Customer",
        "origin": "India",
        "destination": "USA",
        "items": parsed["items"],
    }

    response = run_logistics_agent(shipment_data)

    assert response["plan"] is not None
    assert response["handoff_payload"]["total_cbm"] > 0
    assert response["status"] in {
        "ready_for_review",
        "review_required",
        "critical_review_required",
        "partial_plan_needs_more_information",
    }


def test_fuzzy_catalog_matching():
    resolution = resolve_items(
        [
            {
                "name": "televisions",
                "quantity": 2,
            }
        ]
    )

    assert len(resolution["resolved_items"]) == 1
    assert resolution["resolved_items"][0]["length_m"] == 1.2
    assert resolution["unresolved_items"] == []


def main():
    test_cbm_calculation()
    test_container_recommendation()
    test_full_logistics_plan()
    test_loading_sequence()
    test_logistics_risk_assessment()
    test_item_resolver_uses_catalog()
    test_container_strategy()
    test_route_advisor_for_perishable_cargo()
    test_container_layout()
    test_logistics_service_contract()
    test_packaging_plan()
    test_readiness_checklist()
    test_container_options()
    test_handoff_payload()
    test_text_shipment_parser()
    test_text_input_runs_through_logistics_agent()
    test_fuzzy_catalog_matching()
    print("All logistics agent tests passed.")


if __name__ == "__main__":
    main()
