from pprint import pprint

from app.logistics_agent import build_logistics_plan


def main():
    sample_items = [
        {
            "name": "TV",
            "quantity": 50,
            "length_m": 1.2,
            "width_m": 0.2,
            "height_m": 0.8,
            "weight_kg": 12,
            "fragile": True,
            "stackable": False,
        },
        {
            "name": "Scooter",
            "quantity": 5,
            "length_m": 1.8,
            "width_m": 0.7,
            "height_m": 1.1,
            "weight_kg": 90,
            "stackable": False,
        },
        {
            "name": "Pillows",
            "quantity": 100,
            "length_m": 0.5,
            "width_m": 0.4,
            "height_m": 0.2,
            "weight_kg": 1,
        },
        {
            "name": "Glass bottles",
            "quantity": 20,
            "length_m": 0.3,
            "width_m": 0.3,
            "height_m": 0.4,
            "weight_kg": 2,
            "fragile": True,
        },
    ]

    plan = build_logistics_plan(sample_items)
    pprint(plan)


if __name__ == "__main__":
    main()
