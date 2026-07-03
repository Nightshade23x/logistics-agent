from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

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


def main():
    test_cbm_calculation()
    test_container_recommendation()
    test_full_logistics_plan()
    test_loading_sequence()
    print("All logistics agent tests passed.")


if __name__ == "__main__":
    main()
