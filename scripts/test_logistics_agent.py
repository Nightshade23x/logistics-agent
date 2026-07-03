from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.item_resolver import resolve_items
from app.logistics_agent import CargoItem, build_logistics_plan, calculate_total_cbm, recommend_container


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


def main():
    test_cbm_calculation()
    test_container_recommendation()
    test_full_logistics_plan()
    test_loading_sequence()
    test_logistics_risk_assessment()
    test_item_resolver_uses_catalog()
    test_container_strategy()
    test_route_advisor_for_perishable_cargo()
    print("All logistics agent tests passed.")


if __name__ == "__main__":
    main()
