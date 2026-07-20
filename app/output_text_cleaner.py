from __future__ import annotations

from typing import Any


TEXT_REPLACEMENTS = {
    "Trader,and": "Trader, and",
    "DAP,DDP": "DAP, DDP",
    "20ftStandard": "20ft Standard",
    "40ftStandard": "40ft Standard",
    "StandardContainer": "Standard Container",
    "beforebooking": "before booking",
    "reliableestimate": "reliable estimate",
    "calculatinglanded": "calculating landed",
    "transportdocument": "transport document",
    "beforetreating": "before treating",
    "reviewis": "review is",
    "modebefore": "mode before",
    "neededfor": "needed for",
    "especiallyfor": "especially for",
    "wereestimated": "were estimated",
    "propertieswere": "properties were",
    "abovenon-stackable": "above non-stackable",
    "cushioning,strong": "cushioning, strong",
    "IncotermFOB": "Incoterm FOB",
}


def clean_output_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value

    text = value

    for old, new in TEXT_REPLACEMENTS.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def clean_output_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: clean_output_payload(inner_value)
            for key, inner_value in value.items()
        }

    if isinstance(value, list):
        return [
            clean_output_payload(item)
            for item in value
        ]

    if isinstance(value, tuple):
        return tuple(clean_output_payload(item) for item in value)

    return clean_output_text(value)
