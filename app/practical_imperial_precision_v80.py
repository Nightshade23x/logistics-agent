from __future__ import annotations

import re
from typing import Any


TOTAL_TOLERANCE_KG = 0.01
MATCH_TOLERANCE_KG = 0.02


def _number(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _validation_quantity(payload: dict[str, Any]) -> float | None:
    validation = payload.get("input_validation_v44")
    if not isinstance(validation, dict):
        return None

    facts = validation.get("authoritative_facts")
    if not isinstance(facts, dict):
        return None

    return _number(facts.get("quantity"))


def _has_nonpositive_quantity_error(payload: dict[str, Any]) -> bool:
    quantity = _validation_quantity(payload)
    if quantity is None or quantity > 0:
        return False

    validation = payload.get("input_validation_v44")
    errors = validation.get("errors") if isinstance(validation, dict) else None
    if not isinstance(errors, list):
        return False

    error_text = " ".join(str(error) for error in errors).lower()
    return "quantity must be greater than zero" in error_text


def _explicit_total_lb(text: str) -> float | None:
    match = re.search(
        r"(?i)\btotal(?:\s+(?:shipment|cargo|load))?\s+weight"
        r"\s*(?:is|=|:)?\s*([0-9][0-9,.]*)\s*"
        r"(?:lb|lbs?|llb|llbs?|pounds?)\b",
        text,
    )
    if not match:
        return None

    return _number(match.group(1).replace(",", ""))


def _per_unit_lb(text: str) -> float | None:
    patterns = (
        r"(?i)\beach\b[^.;\n]{0,400}?"
        r"\b(?:weighs?|weight\s*(?:is|=|:))\s*"
        r"([0-9][0-9,.]*)\s*(?:lb|lbs?|llb|llbs?|pounds?)\b",
        r"(?i)\bper\s+(?:item|unit|package|crate|pallet|box)\b"
        r"[^.;\n]{0,200}?\b(?:weight\s*(?:is|=|:)?\s*)?"
        r"([0-9][0-9,.]*)\s*(?:lb|lbs?|llb|llbs?|pounds?)\b",
    )

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _number(match.group(1).replace(",", ""))

    return None


def _canonical_measurements(
    payload: dict[str, Any],
    original_text: str,
) -> dict[str, float | int | str] | None:
    explicit_total = _explicit_total_lb(original_text)
    per_unit = _per_unit_lb(original_text)
    quantity = _validation_quantity(payload)

    if explicit_total is not None and explicit_total > 0:
        exact_total_kg = explicit_total * 0.45359237
        canonical_total = round(exact_total_kg)

        if abs(exact_total_kg - canonical_total) <= TOTAL_TOLERANCE_KG:
            return {
                "source": "explicit_total_lb",
                "display_total_lb": explicit_total,
                "exact_total_kg": exact_total_kg,
                "canonical_total_kg": int(canonical_total),
            }

    if (
        per_unit is not None
        and per_unit > 0
        and quantity is not None
        and quantity > 0
    ):
        exact_unit_kg = per_unit * 0.45359237
        exact_total_kg = exact_unit_kg * quantity
        canonical_unit = round(exact_unit_kg)
        canonical_total = round(exact_total_kg)

        if (
            abs(exact_unit_kg - canonical_unit) <= TOTAL_TOLERANCE_KG
            and abs(exact_total_kg - canonical_total) <= TOTAL_TOLERANCE_KG
        ):
            return {
                "source": "per_unit_lb",
                "display_unit_lb": per_unit,
                "quantity": int(quantity) if quantity.is_integer() else quantity,
                "exact_unit_kg": exact_unit_kg,
                "canonical_unit_kg": int(canonical_unit),
                "exact_total_kg": exact_total_kg,
                "canonical_total_kg": int(canonical_total),
            }

    return None


def _replace_matching_weights(
    value: Any,
    *,
    exact_total_kg: float,
    canonical_total_kg: int,
    exact_unit_kg: float | None,
    canonical_unit_kg: int | None,
) -> None:
    if isinstance(value, dict):
        for key, child in list(value.items()):
            number = _number(child)

            if key in {
                "total_weight_kg",
                "derived_total_weight_kg",
                "explicit_total_weight_kg",
            }:
                if (
                    number is not None
                    and abs(number - exact_total_kg) <= MATCH_TOLERANCE_KG
                ):
                    value[key] = canonical_total_kg
                    continue

            if (
                exact_unit_kg is not None
                and canonical_unit_kg is not None
                and key in {
                    "unit_weight_kg",
                    "per_unit_weight_kg",
                    "weight_kg",
                }
                and number is not None
                and abs(number - exact_unit_kg) <= MATCH_TOLERANCE_KG
            ):
                value[key] = canonical_unit_kg
                continue

            _replace_matching_weights(
                child,
                exact_total_kg=exact_total_kg,
                canonical_total_kg=canonical_total_kg,
                exact_unit_kg=exact_unit_kg,
                canonical_unit_kg=canonical_unit_kg,
            )

    elif isinstance(value, list):
        for child in value:
            _replace_matching_weights(
                child,
                exact_total_kg=exact_total_kg,
                canonical_total_kg=canonical_total_kg,
                exact_unit_kg=exact_unit_kg,
                canonical_unit_kg=canonical_unit_kg,
            )


def apply_practical_imperial_precision(
    payload: Any,
    original_text: str | None,
) -> Any:
    if not isinstance(payload, dict):
        return payload

    if _has_nonpositive_quantity_error(payload):
        return payload

    text = original_text if isinstance(original_text, str) else ""
    measurements = _canonical_measurements(payload, text)
    if not measurements:
        return payload

    exact_total = float(measurements["exact_total_kg"])
    canonical_total = int(measurements["canonical_total_kg"])

    exact_unit = _number(measurements.get("exact_unit_kg"))
    canonical_unit_value = measurements.get("canonical_unit_kg")
    canonical_unit = (
        int(canonical_unit_value)
        if canonical_unit_value is not None
        else None
    )

    _replace_matching_weights(
        payload,
        exact_total_kg=exact_total,
        canonical_total_kg=canonical_total,
        exact_unit_kg=exact_unit,
        canonical_unit_kg=canonical_unit,
    )

    metadata = payload.setdefault("request_metadata", {})
    if isinstance(metadata, dict):
        metadata["practical_imperial_precision_v80"] = {
            "status": "applied",
            **{
                key: (
                    round(value, 6)
                    if isinstance(value, float)
                    else value
                )
                for key, value in measurements.items()
            },
            "tolerance_kg": TOTAL_TOLERANCE_KG,
        }

    return payload


def apply_practical_imperial_precision_to_result(
    result: Any,
    original_text: str | None,
) -> Any:
    if isinstance(result, dict):
        return apply_practical_imperial_precision(
            result,
            original_text,
        )

    if isinstance(result, tuple):
        for item in result:
            if isinstance(item, dict):
                apply_practical_imperial_precision(
                    item,
                    original_text,
                )
        return result

    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict):
                apply_practical_imperial_precision(
                    item,
                    original_text,
                )
        return result

    return result


# PRACTICAL IMPERIAL TEXT SYNCHRONISATION V81
# V80 canonicalises numeric fields. This final, narrow text pass keeps
# user-facing answer strings consistent by displaying a practical whole
# kilogram without a trailing ".0" or the raw conversion residue.
_PRACTICAL_IMPERIAL_TEXT_SYNC_V81_PREVIOUS = (
    apply_practical_imperial_precision
)


def _v81_weight_text_forms(value):
    number = _number(value)
    if number is None:
        return set()

    whole = int(round(number))
    forms = {
        str(whole),
        f"{whole}.0",
        f"{whole}.00",
        f"{whole:,}",
        f"{whole:,}.0",
        f"{whole:,}.00",
        f"{number:.6f}".rstrip("0").rstrip("."),
        f"{number:.4f}".rstrip("0").rstrip("."),
        f"{number:.3f}".rstrip("0").rstrip("."),
        f"{number:.2f}".rstrip("0").rstrip("."),
    }
    return {form for form in forms if form}


def _v81_sync_weight_text(text, measurements):
    if not isinstance(text, str) or not text:
        return text

    canonical_total = measurements.get("canonical_total_kg")
    exact_total = measurements.get("exact_total_kg")
    replacements = []

    if canonical_total is not None:
        replacements.append(
            (
                _v81_weight_text_forms(canonical_total)
                | _v81_weight_text_forms(exact_total),
                f"{int(round(float(canonical_total)))} kg",
            )
        )

    canonical_unit = measurements.get("canonical_unit_kg")
    exact_unit = measurements.get("exact_unit_kg")

    if canonical_unit is not None:
        replacements.append(
            (
                _v81_weight_text_forms(canonical_unit)
                | _v81_weight_text_forms(exact_unit),
                f"{int(round(float(canonical_unit)))} kg",
            )
        )

    updated = text

    for forms, replacement in replacements:
        ordered = sorted(forms, key=len, reverse=True)
        if not ordered:
            continue

        pattern = (
            r"(?<![0-9.])(?:"
            + "|".join(re.escape(form) for form in ordered)
            + r")\s*kg\b"
        )
        updated = re.sub(
            pattern,
            replacement,
            updated,
            flags=re.IGNORECASE,
        )

    return updated


def _v81_sync_recursive(value, measurements):
    if isinstance(value, dict):
        for key, child in list(value.items()):
            value[key] = _v81_sync_recursive(child, measurements)
        return value

    if isinstance(value, list):
        for index, child in enumerate(value):
            value[index] = _v81_sync_recursive(child, measurements)
        return value

    if isinstance(value, tuple):
        return tuple(
            _v81_sync_recursive(child, measurements)
            for child in value
        )

    if isinstance(value, str):
        return _v81_sync_weight_text(value, measurements)

    return value


def apply_practical_imperial_precision(payload, original_text):
    payload = _PRACTICAL_IMPERIAL_TEXT_SYNC_V81_PREVIOUS(
        payload,
        original_text,
    )

    if not isinstance(payload, dict):
        return payload

    metadata = payload.get("request_metadata")
    if not isinstance(metadata, dict):
        return payload

    measurements = metadata.get("practical_imperial_precision_v80")
    if not isinstance(measurements, dict):
        return payload

    payload = _v81_sync_recursive(payload, measurements)

    metadata = payload.get("request_metadata")
    if isinstance(metadata, dict):
        metadata["practical_imperial_text_sync_v81"] = {
            "status": "applied",
            "canonical_total_weight_kg": measurements.get(
                "canonical_total_kg"
            ),
            "canonical_unit_weight_kg": measurements.get(
                "canonical_unit_kg"
            ),
        }

    return payload


# CANONICAL TOTAL WEIGHT LINE V82
# Adds the structured total-weight bullet required by the maintained
# answer contract after V80/V81 have established the canonical value.
_CANONICAL_TOTAL_WEIGHT_LINE_V82_PREVIOUS = (
    apply_practical_imperial_precision
)


def _v82_pretty_total_weight(total_kg):
    return str(int(round(float(total_kg))))


def _v82_append_total_weight_line(value, total_kg):
    expected_line = (
        f"- Total weight: {_v82_pretty_total_weight(total_kg)} kg"
    )

    if isinstance(value, str):
        if expected_line in value:
            return value
        stripped = value.rstrip()
        return expected_line if not stripped else stripped + "\n" + expected_line

    if isinstance(value, dict):
        for key in ("answer_text", "text", "summary"):
            if isinstance(value.get(key), str):
                value[key] = _v82_append_total_weight_line(
                    value[key],
                    total_kg,
                )
                return value

        value["answer_text"] = expected_line
        return value

    if value is None:
        return expected_line

    return value


def _v82_sync_contract_weight_lines(payload, measurements):
    total_kg = measurements.get("canonical_total_kg")
    if total_kg is None:
        return payload

    payload["final_answer"] = _v82_append_total_weight_line(
        payload.get("final_answer"),
        total_kg,
    )
    payload["display_answer"] = _v82_append_total_weight_line(
        payload.get("display_answer"),
        total_kg,
    )
    payload["frontend_answer"] = _v82_append_total_weight_line(
        payload.get("frontend_answer"),
        total_kg,
    )

    metadata = payload.get("request_metadata")
    if isinstance(metadata, dict):
        metadata["canonical_total_weight_line_v82"] = {
            "status": "applied",
            "total_weight_kg": int(round(float(total_kg))),
        }

    return payload


def apply_practical_imperial_precision(payload, original_text):
    payload = _CANONICAL_TOTAL_WEIGHT_LINE_V82_PREVIOUS(
        payload,
        original_text,
    )

    if not isinstance(payload, dict):
        return payload

    metadata = payload.get("request_metadata")
    if not isinstance(metadata, dict):
        return payload

    measurements = metadata.get("practical_imperial_precision_v80")
    if not isinstance(measurements, dict):
        return payload

    return _v82_sync_contract_weight_lines(
        payload,
        measurements,
    )
