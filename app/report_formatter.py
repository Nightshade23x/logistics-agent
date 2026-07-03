from __future__ import annotations

from typing import Any


def format_logistics_plan(plan: dict[str, Any], shipment_info: dict[str, Any] | None = None) -> str:
    lines: list[str] = []

    if shipment_info:
        lines.append("LOGISTICS SHIPMENT PLAN")
        lines.append("=" * 30)
        lines.append(f"Shipment ID: {shipment_info.get('shipment_id', 'N/A')}")
        lines.append(f"Customer: {shipment_info.get('customer', 'N/A')}")
        lines.append(f"Origin: {shipment_info.get('origin', 'N/A')}")
        lines.append(f"Destination: {shipment_info.get('destination', 'N/A')}")

        notes = shipment_info.get("notes")
        if notes:
            lines.append(f"Notes: {notes}")

        lines.append("")

    input_resolution = plan.get("input_resolution")
    if input_resolution:
        lines.append("INPUT ASSUMPTIONS & MISSING INFO")
        lines.append("-" * 30)

        issues = input_resolution.get("issues", [])
        unresolved_items = input_resolution.get("unresolved_items", [])

        if issues:
            for issue in issues:
                lines.append(f"- {issue}")
        else:
            lines.append("- No input assumptions were needed.")

        if unresolved_items:
            lines.append("")
            lines.append("Unresolved items:")
            for item in unresolved_items:
                lines.append(f"- {item.get('name', 'Unknown item')}")

        lines.append("")

    summary = plan["shipment_summary"]
    container = plan["container_recommendation"]

    lines.append("SHIPMENT SUMMARY")
    lines.append("-" * 30)
    lines.append(f"Total item units: {summary['total_items']}")
    lines.append(f"Total CBM: {summary['total_cbm']}")
    lines.append(f"Total weight: {summary['total_weight_kg']} kg")
    lines.append("")

    lines.append("CONTAINER RECOMMENDATION")
    lines.append("-" * 30)
    lines.append(f"Recommended container: {container['container_name']}")

    if container["capacity_cbm"] is not None:
        lines.append(f"Container capacity: {container['capacity_cbm']} CBM")
        lines.append(f"Safe CBM limit: {container['safe_cbm_limit']} CBM")
        lines.append(f"Max payload: {container['max_payload_kg']} kg")
        lines.append(f"Estimated utilization: {container['estimated_utilization_percent']}%")

    lines.append(f"Reason: {container['reason']}")
    lines.append("")

    container_strategy = plan.get("container_strategy")
    if container_strategy:
        lines.append("CONTAINER STRATEGY")
        lines.append("-" * 30)
        lines.append(f"Strategy type: {container_strategy['strategy_type']}")
        lines.append(f"Priority: {container_strategy['priority'].upper()}")
        lines.append("")
        lines.append("Warnings:")
        for warning in container_strategy["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")
        lines.append("Recommendations:")
        for recommendation in container_strategy["recommendations"]:
            lines.append(f"- {recommendation}")
        lines.append("")

    risk = plan.get("logistics_risk")
    if risk:
        lines.append("OPERATIONAL WARNINGS & REQUIREMENTS")
        lines.append("-" * 30)
        lines.append(f"Risk level: {risk['risk_level'].upper()}")
        lines.append(f"Risk score: {risk['risk_score']}")
        lines.append("")
        lines.append("Warnings:")
        for warning in risk["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")
        lines.append("Requirements:")
        for requirement in risk["requirements"]:
            lines.append(f"- {requirement}")
        lines.append("")

    route_plan = plan.get("route_plan")
    if route_plan:
        lines.append("ROUTE & HANDLING ADVISOR")
        lines.append("-" * 30)
        lines.append(f"Route type: {route_plan['route_type']}")
        lines.append(f"Priority: {route_plan['priority'].upper()}")
        lines.append(f"Summary: {route_plan['summary']}")
        lines.append("")

        lines.append("Route warnings:")
        for warning in route_plan["route_warnings"]:
            lines.append(f"- {warning}")

        lines.append("")
        lines.append("Handling priorities:")
        for priority_item in route_plan["handling_priorities"]:
            lines.append(f"- {priority_item}")

        lines.append("")
        lines.append("Route planning checkpoints:")
        for checkpoint in route_plan["checkpoints"]:
            lines.append(f"- {checkpoint}")

        lines.append("")
        lines.append("Missing information:")
        for missing in route_plan["missing_info"]:
            lines.append(f"- {missing}")

        lines.append("")

    lines.append("ITEM BREAKDOWN")
    lines.append("-" * 30)

    for item in plan["item_breakdown"]:
        categories = ", ".join(item["cargo_categories"])

        lines.append(f"- {item['name']} x {item['quantity']}")
        lines.append(f"  Unit CBM: {item['unit_cbm']}")
        lines.append(f"  Total CBM: {item['total_cbm']}")
        lines.append(f"  Total weight: {item['total_weight_kg']} kg")
        lines.append(f"  Categories: {categories}")

    lines.append("")
    lines.append("SUGGESTED LOADING SEQUENCE")
    lines.append("-" * 30)

    for item in plan.get("loading_sequence", []):
        categories = ", ".join(item["categories"])
        lines.append(f"{item['sequence_number']}. {item['item_name']} x {item['quantity']}")
        lines.append(f"   Zone: {item['suggested_zone']}")
        lines.append(f"   Categories: {categories}")
        lines.append(f"   Reason: {item['reason']}")

    lines.append("")
    lines.append("LOADING ADVICE")
    lines.append("-" * 30)

    for index, advice in enumerate(plan["loading_advice"], start=1):
        lines.append(f"{index}. {advice}")

    return "\n".join(lines)
