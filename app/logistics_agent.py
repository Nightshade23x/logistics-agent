from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.loading_planner import generate_loading_sequence
from app.logistics_risk import assess_logistics_risk


@dataclass(frozen=True)
class CargoItem:
    name: str
    quantity: int
    length_m: float
    width_m: float
    height_m: float
    weight_kg: float = 0.0
    fragile: bool = False
    perishable: bool = False
    hazardous: bool = False
    radioactive: bool = False
    stackable: bool = True
    unload_priority: int = 3

    @property
    def unit_cbm(self) -> float:
        return round(self.length_m * self.width_m * self.height_m, 4)

    @property
    def total_cbm(self) -> float:
        return round(self.unit_cbm * self.quantity, 4)

    @property
    def total_weight_kg(self) -> float:
        return round(self.weight_kg * self.quantity, 2)


CONTAINERS = [
    {
        "name": "20ft Standard Container",
        "capacity_cbm": 33.2,
        "max_payload_kg": 28200,
        "safe_utilization": 0.85,
    },
    {
        "name": "40ft Standard Container",
        "capacity_cbm": 67.7,
        "max_payload_kg": 26700,
        "safe_utilization": 0.85,
    },
    {
        "name": "40ft High Cube Container",
        "capacity_cbm": 76.4,
        "max_payload_kg": 26500,
        "safe_utilization": 0.85,
    },
]


FRAGILE_KEYWORDS = {
    "glass",
    "bottle",
    "bottles",
    "tv",
    "television",
    "mirror",
    "ceramic",
    "tiles",
}

HEAVY_KEYWORDS = {
    "tiles",
    "tile",
    "scooter",
    "scooters",
    "machine",
    "machinery",
    "dining",
    "furniture",
    "mattress",
    "mattresses",
}

PERISHABLE_KEYWORDS = {
    "food",
    "fruit",
    "vegetable",
    "medicine",
    "flowers",
    "fish",
    "meat",
}

HAZARDOUS_KEYWORDS = {
    "battery",
    "batteries",
    "chemical",
    "fuel",
    "paint",
    "aerosol",
    "radioactive",
}


def validate_item(item: CargoItem) -> None:
    if item.quantity <= 0:
        raise ValueError(f"{item.name}: quantity must be greater than 0.")

    dimensions = [item.length_m, item.width_m, item.height_m]
    if any(value <= 0 for value in dimensions):
        raise ValueError(f"{item.name}: all dimensions must be greater than 0.")

    if item.weight_kg < 0:
        raise ValueError(f"{item.name}: weight cannot be negative.")


def calculate_total_cbm(items: list[CargoItem]) -> float:
    for item in items:
        validate_item(item)

    return round(sum(item.total_cbm for item in items), 4)


def calculate_total_weight(items: list[CargoItem]) -> float:
    for item in items:
        validate_item(item)

    return round(sum(item.total_weight_kg for item in items), 2)


def classify_cargo(item: CargoItem) -> list[str]:
    name_words = set(item.name.lower().replace("-", " ").split())
    categories: list[str] = []

    if item.fragile or name_words.intersection(FRAGILE_KEYWORDS):
        categories.append("fragile")

    if item.perishable or name_words.intersection(PERISHABLE_KEYWORDS):
        categories.append("perishable")

    if item.hazardous or name_words.intersection(HAZARDOUS_KEYWORDS):
        categories.append("hazardous")

    if item.radioactive or "radioactive" in name_words:
        categories.append("radioactive")

    if item.weight_kg >= 30 or name_words.intersection(HEAVY_KEYWORDS):
        categories.append("heavy")

    if not item.stackable:
        categories.append("non_stackable")

    if not categories:
        categories.append("general_cargo")

    return categories


def recommend_container(items: list[CargoItem]) -> dict[str, Any]:
    total_cbm = calculate_total_cbm(items)
    total_weight = calculate_total_weight(items)

    for container in CONTAINERS:
        safe_cbm_limit = container["capacity_cbm"] * container["safe_utilization"]

        if total_cbm <= safe_cbm_limit and total_weight <= container["max_payload_kg"]:
            utilization_percent = round((total_cbm / container["capacity_cbm"]) * 100, 2)

            return {
                "container_name": container["name"],
                "capacity_cbm": container["capacity_cbm"],
                "safe_cbm_limit": round(safe_cbm_limit, 2),
                "max_payload_kg": container["max_payload_kg"],
                "estimated_utilization_percent": utilization_percent,
                "reason": "This is the smallest listed container that fits the cargo within the safe utilization limit.",
            }

    return {
        "container_name": "Multiple containers or specialist planning required",
        "capacity_cbm": None,
        "safe_cbm_limit": None,
        "max_payload_kg": None,
        "estimated_utilization_percent": None,
        "reason": "The shipment exceeds the safe CBM or payload limit of the listed containers.",
    }


def generate_loading_advice(items: list[CargoItem]) -> list[str]:
    advice: list[str] = []

    classified_items = [
        {
            "item": item,
            "categories": classify_cargo(item),
        }
        for item in items
    ]

    if any("heavy" in entry["categories"] for entry in classified_items):
        advice.append(
            "Load heavy cargo first and place it at the bottom to keep the container stable."
        )

    if any("fragile" in entry["categories"] for entry in classified_items):
        advice.append(
            "Keep fragile items away from heavy cargo and protect them with cushioning or crates."
        )

    if any("non_stackable" in entry["categories"] for entry in classified_items):
        advice.append(
            "Do not stack cargo marked as non-stackable; reserve floor space for these items."
        )

    if any("perishable" in entry["categories"] for entry in classified_items):
        advice.append(
            "Perishable cargo may require temperature-controlled handling or a refrigerated container."
        )

    if any("hazardous" in entry["categories"] for entry in classified_items):
        advice.append(
            "Hazardous cargo must be checked for special packing, labelling, documentation, and segregation rules."
        )

    if any("radioactive" in entry["categories"] for entry in classified_items):
        advice.append(
            "Radioactive cargo requires specialist regulatory clearance and must not be handled as normal cargo."
        )

    if any(item.unload_priority == 1 for item in items):
        advice.append(
            "Items needed first at destination should be loaded closer to the container door."
        )

    advice.append(
        "Distribute weight evenly from left to right and front to back to reduce transport risk."
    )

    advice.append(
        "Leave enough access space near the door so unloading is not unnecessarily difficult."
    )

    return advice


def build_logistics_plan(raw_items: list[dict[str, Any]]) -> dict[str, Any]:
    items = [CargoItem(**raw_item) for raw_item in raw_items]

    item_breakdown = []
    for item in items:
        validate_item(item)
        item_breakdown.append(
            {
                **asdict(item),
                "unit_cbm": item.unit_cbm,
                "total_cbm": item.total_cbm,
                "total_weight_kg": item.total_weight_kg,
                "cargo_categories": classify_cargo(item),
            }
        )

    total_cbm = calculate_total_cbm(items)
    total_weight = calculate_total_weight(items)
    container_recommendation = recommend_container(items)
    loading_advice = generate_loading_advice(items)
    loading_sequence = generate_loading_sequence(item_breakdown)
    logistics_risk = assess_logistics_risk(item_breakdown, container_recommendation)

    return {
        "shipment_summary": {
            "total_items": sum(item.quantity for item in items),
            "total_cbm": total_cbm,
            "total_weight_kg": total_weight,
        },
        "item_breakdown": item_breakdown,
        "container_recommendation": container_recommendation,
        "logistics_risk": logistics_risk,
        "loading_sequence": loading_sequence,
        "loading_advice": loading_advice,
    }
