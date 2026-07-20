from __future__ import annotations

from itertools import combinations_with_replacement
from typing import Any


CONTAINER_SPECS = [
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


def _summarize_combo(combo: tuple[dict[str, Any], ...]) -> str:
    counts: dict[str, int] = {}

    for container in combo:
        counts[container["name"]] = counts.get(container["name"], 0) + 1

    return " + ".join(
        f"{count} x {name}" if count > 1 else name
        for name, count in counts.items()
    )


def generate_container_options(
    total_cbm: float,
    total_weight_kg: float,
    max_containers: int = 3,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Generates practical container alternatives.

    This is not a full commercial freight optimizer. It gives useful options
    based on safe CBM capacity and payload limits.
    """
    options: list[dict[str, Any]] = []

    for container_count in range(1, max_containers + 1):
        for combo in combinations_with_replacement(CONTAINER_SPECS, container_count):
            total_capacity = sum(container["capacity_cbm"] for container in combo)
            total_safe_cbm = sum(
                container["capacity_cbm"] * container["safe_utilization"]
                for container in combo
            )
            total_payload = sum(container["max_payload_kg"] for container in combo)

            if total_cbm <= total_safe_cbm and total_weight_kg <= total_payload:
                unused_safe_cbm = round(total_safe_cbm - total_cbm, 2)
                utilization_percent = round((total_cbm / total_capacity) * 100, 2)

                options.append(
                    {
                        "option_name": _summarize_combo(combo),
                        "container_count": container_count,
                        "total_capacity_cbm": round(total_capacity, 2),
                        "total_safe_cbm": round(total_safe_cbm, 2),
                        "total_payload_kg": total_payload,
                        "estimated_utilization_percent": utilization_percent,
                        "unused_safe_cbm": unused_safe_cbm,
                        "reason": "Fits within safe CBM and payload limits.",
                    }
                )

    options.sort(
        key=lambda option: (
            option["container_count"],
            option["unused_safe_cbm"],
            -option["total_payload_kg"],
        )
    )

    if not options:
        return [
            {
                "option_name": "Specialist multi-container planning required",
                "container_count": None,
                "total_capacity_cbm": None,
                "total_safe_cbm": None,
                "total_payload_kg": None,
                "estimated_utilization_percent": None,
                "unused_safe_cbm": None,
                "reason": "Cargo exceeds the tested standard container combinations.",
            }
        ]

    return options[:limit]
