from __future__ import annotations

import re
from pathlib import Path
from typing import Any


FIELD_PATTERNS = {
    "bill_of_lading_number": r"Bill of Lading Number:\s*(.+)",
    "certificate_number": r"Certificate Number:\s*(.+)",
    "shipper": r"Shipper:\s*(.+)",
    "consignee": r"Consignee:\s*(.+)",
    "exporter": r"Exporter:\s*(.+)",
    "importer": r"Importer:\s*(.+)",
    "port_of_loading": r"Port of Loading:\s*(.+)",
    "port_of_discharge": r"Port of Discharge:\s*(.+)",
    "vessel": r"Vessel:\s*(.+)",
    "container_number": r"Container Number:\s*(.+)",
    "seal_number": r"Seal Number:\s*(.+)",
    "invoice_number": r"Invoice Number:\s*(.+)",
    "packing_list_number": r"Packing List Number:\s*(.+)",
    "supplier": r"Supplier:\s*(.+)",
    "buyer": r"Buyer:\s*(.+)",
    "origin_country": r"Origin Country:\s*(.+)",
    "destination_country": r"Destination Country:\s*(.+)",
    "currency": r"Currency:\s*(.+)",
    "total_value": r"Total Value:\s*([0-9,.]+)",
    "total_weight_kg": r"^Total Weight:\s*([0-9,.]+)\s*kg",
}


ITEM_LINE_PATTERN = re.compile(
    r"^\s*\d+\.\s*(?P<name>.+?)\s*\|\s*Quantity:\s*(?P<quantity>\d+)"
    r"(?:\s*\|\s*Length:\s*(?P<length>[0-9.]+)\s*(?P<length_unit>cm|m|mm|in|ft))?"
    r"(?:\s*\|\s*Width:\s*(?P<width>[0-9.]+)\s*(?P<width_unit>cm|m|mm|in|ft))?"
    r"(?:\s*\|\s*Height:\s*(?P<height>[0-9.]+)\s*(?P<height_unit>cm|m|mm|in|ft))?"
    r"(?:\s*\|\s*(?:Unit Weight|Weight):\s*(?P<weight>[0-9.]+)\s*(?P<weight_unit>kg|g|lb|lbs))?"
    r"(?:\s*\|\s*Total Weight:\s*(?P<total_weight>[0-9.]+)\s*(?P<total_weight_unit>kg|g|lb|lbs))?",
    re.IGNORECASE,
)


def read_document_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


def _extract_field(text: str, pattern: str) -> str | float | None:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)

    if not match:
        return None

    value = match.group(1).strip()

    if value.replace(",", "").replace(".", "").isdigit():
        return float(value.replace(",", ""))

    return value


def extract_header_fields(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}

    for field_name, pattern in FIELD_PATTERNS.items():
        value = _extract_field(text, pattern)

        if value is not None:
            fields[field_name] = value

    return fields


def extract_items(text: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for line in text.splitlines():
        match = ITEM_LINE_PATTERN.match(line)

        if not match:
            continue

        data = match.groupdict()
        item: dict[str, Any] = {
            "name": data["name"].strip(),
            "quantity": int(data["quantity"]),
        }

        if data.get("length") and data.get("width") and data.get("height"):
            item.update(
                {
                    "length": float(data["length"]),
                    "width": float(data["width"]),
                    "height": float(data["height"]),
                    "dimension_unit": data.get("length_unit") or "m",
                }
            )

        if data.get("weight"):
            item["weight"] = float(data["weight"])
            item["weight_unit"] = data.get("weight_unit") or "kg"

        if data.get("total_weight"):
            item["total_weight"] = float(data["total_weight"])
            item["total_weight_unit"] = data.get("total_weight_unit") or "kg"

        items.append(item)

    return items


def detect_document_type(text: str) -> str:
    lowered = text.lower()

    if "packing list" in lowered:
        return "packing_list"

    if "invoice" in lowered:
        return "invoice"

    if "bill of lading" in lowered:
        return "bill_of_lading"

    if "certificate of origin" in lowered:
        return "certificate_of_origin"

    return "unknown"


def parse_trade_document(text: str) -> dict[str, Any]:
    document_type = detect_document_type(text)
    fields = extract_header_fields(text)
    items = extract_items(text)

    return {
        "document_type": document_type,
        "fields": fields,
        "items": items,
    }
