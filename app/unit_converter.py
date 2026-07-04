from __future__ import annotations

from typing import Any


LENGTH_TO_METRES = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "metre": 1.0,
    "metres": 1.0,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "centimetre": 0.01,
    "centimetres": 0.01,
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "millimetre": 0.001,
    "millimetres": 0.001,
    "in": 0.0254,
    "inch": 0.0254,
    "inches": 0.0254,
    "ft": 0.3048,
    "feet": 0.3048,
    "foot": 0.3048,
}

WEIGHT_TO_KG = {
    "kg": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,
    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
    "lb": 0.45359237,
    "lbs": 0.45359237,
    "pound": 0.45359237,
    "pounds": 0.45359237,
}

VOLUME_TO_CBM = {
    "cbm": 1.0,
    "m3": 1.0,
    "m^3": 1.0,
    "cubic meter": 1.0,
    "cubic meters": 1.0,
    "cubic metre": 1.0,
    "cubic metres": 1.0,
    "ft3": 0.028316846592,
    "ft^3": 0.028316846592,
    "cubic foot": 0.028316846592,
    "cubic feet": 0.028316846592,
}


def _normalize_unit(unit: str | None, default: str) -> str:
    return (unit or default).lower().strip().replace(".", "")


def convert_length_to_metres(value: float | int, unit: str | None = "m") -> float:
    normalized_unit = _normalize_unit(unit, "m")

    if normalized_unit not in LENGTH_TO_METRES:
        raise ValueError(f"Unsupported length unit: {unit}")

    return float(value) * LENGTH_TO_METRES[normalized_unit]


def convert_weight_to_kg(value: float | int, unit: str | None = "kg") -> float:
    normalized_unit = _normalize_unit(unit, "kg")

    if normalized_unit not in WEIGHT_TO_KG:
        raise ValueError(f"Unsupported weight unit: {unit}")

    return float(value) * WEIGHT_TO_KG[normalized_unit]


def convert_volume_to_cbm(value: float | int, unit: str | None = "cbm") -> float:
    normalized_unit = _normalize_unit(unit, "cbm")

    if normalized_unit not in VOLUME_TO_CBM:
        raise ValueError(f"Unsupported volume unit: {unit}")

    return float(value) * VOLUME_TO_CBM[normalized_unit]


def _get_dimension_from_unit_specific_key(raw_item: dict[str, Any], axis: str) -> float | None:
    for unit in LENGTH_TO_METRES:
        key = f"{axis}_{unit}"

        if key in raw_item and raw_item[key] not in {None, ""}:
            return convert_length_to_metres(raw_item[key], unit)

    return None


def _get_dimension_metres(raw_item: dict[str, Any], axis: str) -> float:
    metre_key = f"{axis}_m"

    if metre_key in raw_item and raw_item[metre_key] not in {None, ""}:
        return float(raw_item[metre_key])

    unit_specific_value = _get_dimension_from_unit_specific_key(raw_item, axis)
    if unit_specific_value is not None:
        return unit_specific_value

    dimensions = raw_item.get("dimensions")
    if isinstance(dimensions, dict) and axis in dimensions:
        unit = dimensions.get("unit", dimensions.get(f"{axis}_unit", "m"))
        return convert_length_to_metres(dimensions[axis], unit)

    if axis in raw_item and raw_item[axis] not in {None, ""}:
        unit = raw_item.get(f"{axis}_unit", raw_item.get("dimension_unit", "m"))
        return convert_length_to_metres(raw_item[axis], unit)

    raise ValueError(
        f"{raw_item.get('name', 'Unknown item')}: missing {axis} dimension."
    )


def _get_weight_kg(raw_item: dict[str, Any]) -> float:
    if "weight_kg" in raw_item and raw_item["weight_kg"] not in {None, ""}:
        return float(raw_item["weight_kg"])

    for unit in WEIGHT_TO_KG:
        key = f"weight_{unit}"

        if key in raw_item and raw_item[key] not in {None, ""}:
            return convert_weight_to_kg(raw_item[key], unit)

    if "weight" in raw_item and raw_item["weight"] not in {None, ""}:
        return convert_weight_to_kg(raw_item["weight"], raw_item.get("weight_unit", "kg"))

    return 0.0


def normalize_item_units(raw_item: dict[str, Any]) -> dict[str, Any]:
    """
    Converts item dimensions to metres and weight to kg.

    Supported input examples:
    - length_m, width_m, height_m
    - length, width, height, dimension_unit="cm"
    - length_cm, width_cm, height_cm
    - dimensions={"length": 120, "width": 20, "height": 80, "unit": "cm"}
    - weight_kg
    - weight, weight_unit="lb"
    - weight_lb
    """
    normalized = {
        "name": raw_item["name"],
        "quantity": int(raw_item.get("quantity", 1)),
        "length_m": round(_get_dimension_metres(raw_item, "length"), 6),
        "width_m": round(_get_dimension_metres(raw_item, "width"), 6),
        "height_m": round(_get_dimension_metres(raw_item, "height"), 6),
        "weight_kg": round(_get_weight_kg(raw_item), 6),
        "fragile": raw_item.get("fragile", False),
        "perishable": raw_item.get("perishable", False),
        "hazardous": raw_item.get("hazardous", False),
        "radioactive": raw_item.get("radioactive", False),
        "stackable": raw_item.get("stackable", True),
        "unload_priority": raw_item.get("unload_priority", 3),
    }

    return normalized
