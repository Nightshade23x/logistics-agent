from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.container_3d_visualizer import build_container_3d_html, build_layout, write_container_3d_html


tv_scooter_payload = {
    "logistics_visualizer": {
        "container": {
            "selected_container": "20ft Standard Container",
            "recommended_load_type": "fcl_preferred",
            "total_cbm": 16.53,
            "total_weight_kg": 1050,
        },
        "loading_sequence": [
            {"step": 1, "item_name": "Electric scooters", "instruction": "Load first against the front wall and keep separated."},
            {"step": 2, "item_name": "TVs", "instruction": "Load after scooters with fragile faces protected."},
        ],
        "cargo_mix": [
            {
                "item_name": "TVs",
                "quantity": 50,
                "dimensions_m": {"length": 1.2, "width": 0.2, "height": 0.8},
                "category_tags": ["fragile", "non_stackable"],
                "stackable": False,
            },
            {
                "item_name": "Electric scooters",
                "quantity": 5,
                "dimensions_m": {"length": 1.8, "width": 0.7, "height": 1.1},
                "category_tags": ["hazardous", "battery", "heavy", "non_stackable"],
                "stackable": False,
            },
        ],
    }
}


furniture_payload = {
    "logistics_visualizer": {
        "container": {
            "selected_container": "40ft Standard Container",
            "recommended_load_type": "fcl_preferred",
        },
        "loading_sequence": [
            "Dining sets",
            "Mattresses",
            "Pillows",
            "Glass bottles",
        ],
        "cargo_mix": [
            {"item_name": "Dining sets", "quantity": 10, "category_tags": ["bulky", "heavy"]},
            {"item_name": "Mattresses", "quantity": 5, "category_tags": ["bulky"], "stackable": True},
            {"item_name": "Pillows", "quantity": 100, "category_tags": ["soft", "stackable"], "stackable": True},
            {"item_name": "Glass bottles", "quantity": 30, "category_tags": ["fragile"], "stackable": True},
        ],
    }
}


def assert_every_cargo_type_is_visible(layout: dict) -> None:
    cargo_names = {item["name"] for item in layout["cargo_mix"]}
    box_names = {box["name"] for box in layout["boxes"]}
    missing = cargo_names - box_names

    print("cargo_names:", sorted(cargo_names))
    print("box_names:", sorted(box_names))
    print("missing:", sorted(missing))

    assert not missing, f"Missing cargo types from visual boxes: {missing}"


outputs = [
    ("demo_outputs/container_3d_visualizer_demo.html", tv_scooter_payload),
    ("demo_outputs/container_3d_furniture_demo.html", furniture_payload),
]

for output_path, payload in outputs:
    layout = build_layout(payload)
    html = build_container_3d_html(payload)

    print("")
    print("output:", output_path)
    print("container:", layout["container"]["name"])
    print("used_backend_sequence:", layout["used_backend_sequence"])
    print("loading_sequence:", layout["loading_sequence"])
    print("cargo_order:", [item["name"] for item in layout["cargo_mix"]])
    print("boxes_drawn:", len(layout["boxes"]))
    print("utilization:", layout["utilization"])

    assert_every_cargo_type_is_visible(layout)

    assert "Container space" in html
    assert "Remaining" in html
    assert layout["utilization"]["container_cbm"] > 0
    assert layout["utilization"]["remaining_cbm"] >= 0
    assert layout["utilization"]["remaining_percent"] >= 0

    out = write_container_3d_html(payload, Path(output_path))
    print("created:", out.resolve())
    print("exists:", out.exists())

    if not out.exists():
        raise SystemExit(f"Failed to create {output_path}")


tv_layout = build_layout(tv_scooter_payload)
assert tv_layout["used_backend_sequence"] is True
assert [item["name"] for item in tv_layout["cargo_mix"]][:2] == ["Electric scooters", "TVs"]
assert_every_cargo_type_is_visible(tv_layout)

furniture_layout = build_layout(furniture_payload)
assert furniture_layout["used_backend_sequence"] is True
assert [item["name"] for item in furniture_layout["cargo_mix"]][:4] == [
    "Dining sets",
    "Mattresses",
    "Pillows",
    "Glass bottles",
]
assert_every_cargo_type_is_visible(furniture_layout)

print("")
print("3D visualizer tests passed.")
