from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path
from typing import Any


CONTAINER_SPECS = {
    "20ft": {
        "name": "20ft Standard Container",
        "length_m": 5.90,
        "width_m": 2.35,
        "height_m": 2.39,
        "safe_capacity_cbm": 28.0,
    },
    "40ft": {
        "name": "40ft Standard Container",
        "length_m": 12.03,
        "width_m": 2.35,
        "height_m": 2.39,
        "safe_capacity_cbm": 58.0,
    },
    "40ft_hc": {
        "name": "40ft High Cube Container",
        "length_m": 12.03,
        "width_m": 2.35,
        "height_m": 2.69,
        "safe_capacity_cbm": 66.0,
    },
}


def _get_nested(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _as_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(str(value).replace(",", "").strip())
    except Exception:
        return default


def _as_int(value: Any, default: int = 1) -> int:
    try:
        if value is None or value == "":
            return default
        return max(1, int(float(str(value).replace(",", "").strip())))
    except Exception:
        return default


def _normalise_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _visualizer_section(payload: dict[str, Any]) -> dict[str, Any]:
    visualizer = payload.get("logistics_visualizer")
    if isinstance(visualizer, dict):
        return visualizer

    raw_visualizer = _get_nested(payload, "_raw_user_agent_response", "logistics_visualizer")
    if isinstance(raw_visualizer, dict):
        return raw_visualizer

    specialist_visualizer = _get_nested(
        payload,
        "_raw_user_agent_response",
        "specialist_response",
        "logistics_visualizer",
    )
    if isinstance(specialist_visualizer, dict):
        return specialist_visualizer

    return {}


def _infer_container(payload: dict[str, Any]) -> dict[str, Any]:
    visualizer = _visualizer_section(payload)
    container_data = visualizer.get("container") if isinstance(visualizer, dict) else {}
    if not isinstance(container_data, dict):
        container_data = {}

    selected = (
        container_data.get("selected_container")
        or container_data.get("recommended_container")
        or payload.get("recommended_container")
        or _get_nested(payload, "logistics_metrics", "recommended_container")
        or ""
    )

    selected_text = str(selected).lower()

    if "40" in selected_text and ("high" in selected_text or "hc" in selected_text or "cube" in selected_text):
        base = dict(CONTAINER_SPECS["40ft_hc"])
    elif "40" in selected_text:
        base = dict(CONTAINER_SPECS["40ft"])
    else:
        base = dict(CONTAINER_SPECS["20ft"])

    base["name"] = str(selected or base["name"])

    # Respect explicit container dimensions if backend provides them.
    for key in ["length_m", "width_m", "height_m", "safe_capacity_cbm"]:
        val = _as_float(container_data.get(key), None)
        if val is not None and val > 0:
            base[key] = val

    return base


def _extract_tags(item: dict[str, Any]) -> list[str]:
    tags = (
        item.get("category_tags")
        or item.get("cargo_categories")
        or item.get("tags")
        or item.get("labels")
        or []
    )

    if isinstance(tags, str):
        tags = re.split(r"[,/|]+", tags)

    if not isinstance(tags, list):
        tags = []

    result = []
    for tag in tags:
        clean = str(tag).strip()
        if clean:
            result.append(clean)

    name_text = _normalise_text(
        item.get("item_name")
        or item.get("name")
        or item.get("item")
        or item.get("product")
        or ""
    )

    inferred = []

    if any(word in name_text for word in ["glass", "bottle", "tv", "television", "mirror", "ceramic"]):
        inferred.append("fragile")

    if any(word in name_text for word in ["scooter", "battery", "lithium", "electric"]):
        inferred.extend(["hazardous", "battery"])

    if any(word in name_text for word in ["mattress", "sofa", "dining", "furniture"]):
        inferred.append("bulky")

    if any(word in name_text for word in ["machinery", "engine", "tiles", "ceramic tiles"]):
        inferred.append("heavy")

    existing = {_normalise_text(tag).replace(" ", "_") for tag in result}
    for tag in inferred:
        if _normalise_text(tag).replace(" ", "_") not in existing:
            result.append(tag)

    return result


def _has_tag(tags: list[str], *needles: str) -> bool:
    normalised = {_normalise_text(tag).replace(" ", "_") for tag in tags}
    for needle in needles:
        n = _normalise_text(needle).replace(" ", "_")
        if n in normalised:
            return True
    return False


def _parse_dimension_string(text: str) -> tuple[float, float, float] | None:
    # Supports strings like "120 x 20 x 80 cm", "1.2m x 0.2m x 0.8m", "48 x 8 x 32 inches".
    if not text:
        return None

    lower = text.lower()
    numbers = re.findall(r"\d+(?:\.\d+)?", lower)
    if len(numbers) < 3:
        return None

    vals = [float(x) for x in numbers[:3]]

    if "cm" in lower:
        vals = [v / 100.0 for v in vals]
    elif "mm" in lower:
        vals = [v / 1000.0 for v in vals]
    elif "inch" in lower or "inches" in lower or " in" in lower:
        vals = [v * 0.0254 for v in vals]
    elif "ft" in lower or "feet" in lower:
        vals = [v * 0.3048 for v in vals]

    return tuple(vals)  # type: ignore[return-value]


def _heuristic_dimensions(name: str, tags: list[str]) -> tuple[float, float, float, str]:
    text = _normalise_text(name)

    # These are fallback packed dimensions only.
    # Real logistics_agent dimensions always override these.
    rules = [
        (["electric scooter", "scooter"], (1.80, 0.70, 1.10), "fallback:scooter"),
        (["tv", "television"], (1.20, 0.20, 0.80), "fallback:tv"),
        (["mattress"], (2.00, 0.35, 1.00), "fallback:mattress-packed"),
        (["pillow"], (0.50, 0.35, 0.20), "fallback:pillow"),
        (["glass bottle", "bottle"], (0.40, 0.30, 0.30), "fallback:bottle-carton"),
        (["ceramic tile", "tiles", "tile"], (0.60, 0.40, 0.25), "fallback:tile-carton"),
        (["dining set", "dining", "table", "chair"], (1.50, 0.80, 0.70), "fallback:dining-set"),
        (["sofa", "couch"], (1.80, 0.90, 0.80), "fallback:sofa"),
        (["furniture", "cabinet", "wardrobe"], (1.20, 0.80, 0.80), "fallback:furniture"),
    ]

    for keywords, dims, source in rules:
        if any(keyword in text for keyword in keywords):
            return dims[0], dims[1], dims[2], source

    if _has_tag(tags, "heavy"):
        return 1.00, 0.80, 0.70, "fallback:heavy-cargo"

    if _has_tag(tags, "fragile"):
        return 0.80, 0.50, 0.50, "fallback:fragile-cargo"

    if _has_tag(tags, "bulky"):
        return 1.20, 0.80, 0.80, "fallback:bulky-cargo"

    return 0.80, 0.60, 0.60, "fallback:general-cargo"


def _extract_dimensions(item: dict[str, Any], name: str, tags: list[str], quantity: int) -> tuple[float, float, float, str]:
    dims_m = item.get("dimensions_m")
    if isinstance(dims_m, dict):
        l = _as_float(dims_m.get("length"), None)
        w = _as_float(dims_m.get("width"), None)
        h = _as_float(dims_m.get("height"), None)
        if l and w and h:
            return l, w, h, "backend:dimensions_m"

    dims_cm = item.get("dimensions_cm")
    if isinstance(dims_cm, dict):
        l = _as_float(dims_cm.get("length"), None)
        w = _as_float(dims_cm.get("width"), None)
        h = _as_float(dims_cm.get("height"), None)
        if l and w and h:
            return l / 100.0, w / 100.0, h / 100.0, "backend:dimensions_cm"

    direct_l = _as_float(item.get("length_m"), None)
    direct_w = _as_float(item.get("width_m"), None)
    direct_h = _as_float(item.get("height_m"), None)
    if direct_l and direct_w and direct_h:
        return direct_l, direct_w, direct_h, "backend:length_width_height_m"

    for key in ["dimensions", "packed_dimensions", "unit_dimensions", "size"]:
        val = item.get(key)
        if isinstance(val, str):
            parsed = _parse_dimension_string(val)
            if parsed:
                return parsed[0], parsed[1], parsed[2], f"backend:{key}"

    unit_cbm = (
        _as_float(item.get("unit_cbm"), None)
        or _as_float(item.get("cbm_per_unit"), None)
        or _as_float(item.get("volume_cbm_per_unit"), None)
    )

    total_cbm = (
        _as_float(item.get("total_cbm"), None)
        or _as_float(item.get("cbm"), None)
        or _as_float(item.get("volume_cbm"), None)
    )

    if unit_cbm is None and total_cbm is not None and quantity > 0:
        unit_cbm = total_cbm / quantity

    if unit_cbm and unit_cbm > 0:
        # Convert volume-only info into a neutral box.
        # This is only for visualization when dimensions are missing.
        side = max(0.25, unit_cbm ** (1.0 / 3.0))
        return side * 1.25, side, side * 0.80, "estimated:from_cbm"

    return _heuristic_dimensions(name, tags)


def _category_color(tags: list[str], name: str) -> str:
    if _has_tag(tags, "hazardous", "battery"):
        return "#ff6b4a"
    if _has_tag(tags, "fragile"):
        return "#4cc9f0"
    if _has_tag(tags, "heavy"):
        return "#ffd166"
    if _has_tag(tags, "bulky"):
        return "#b388ff"

    text = _normalise_text(name)
    if "mattress" in text or "furniture" in text or "dining" in text:
        return "#b388ff"

    return "#80ed99"


def _normalise_cargo_mix(payload: dict[str, Any]) -> list[dict[str, Any]]:
    visualizer = _visualizer_section(payload)

    cargo_mix = visualizer.get("cargo_mix")
    if not isinstance(cargo_mix, list):
        cargo_mix = _get_nested(payload, "_raw_user_agent_response", "specialist_response", "plan", "item_breakdown")

    if not isinstance(cargo_mix, list):
        cargo_mix = _get_nested(payload, "specialist_response", "plan", "item_breakdown")

    if not isinstance(cargo_mix, list):
        cargo_mix = []

    normalised: list[dict[str, Any]] = []

    for idx, item in enumerate(cargo_mix):
        if not isinstance(item, dict):
            continue

        name = (
            item.get("item_name")
            or item.get("name")
            or item.get("item")
            or item.get("product")
            or item.get("cargo_type")
            or f"cargo item {idx + 1}"
        )

        quantity = _as_int(item.get("quantity") or item.get("qty") or item.get("count"), 1)
        tags = _extract_tags(item)
        length_m, width_m, height_m, dimension_source = _extract_dimensions(item, str(name), tags, quantity)

        explicit_stackable = item.get("stackable")
        if isinstance(explicit_stackable, bool):
            stackable = explicit_stackable
        else:
            stackable = not _has_tag(tags, "non_stackable", "hazardous", "battery")

        normalised.append(
            {
                "name": str(name),
                "quantity": quantity,
                "length_m": max(0.05, float(length_m)),
                "width_m": max(0.05, float(width_m)),
                "height_m": max(0.05, float(height_m)),
                "tags": tags,
                "color": _category_color(tags, str(name)),
                "stackable": stackable,
                "dimension_source": dimension_source,
                "original_index": idx,
            }
        )

    return normalised


def _extract_loading_sequence(payload: dict[str, Any]) -> list[str]:
    visualizer = _visualizer_section(payload)

    candidates = [
        visualizer.get("loading_sequence"),
        visualizer.get("load_sequence"),
        visualizer.get("packing_sequence"),
        _get_nested(payload, "loading_sequence"),
        _get_nested(payload, "logistics_plan", "loading_sequence"),
        _get_nested(payload, "_raw_user_agent_response", "specialist_response", "plan", "loading_sequence"),
    ]

    names: list[str] = []

    def add_from_entry(entry: Any) -> None:
        if isinstance(entry, str):
            clean = entry.strip()
            if clean:
                names.append(clean)
            return

        if isinstance(entry, dict):
            for key in ["item_name", "name", "item", "cargo", "cargo_type", "load", "description"]:
                val = entry.get(key)
                if isinstance(val, str) and val.strip():
                    names.append(val.strip())
                    return

            for key in ["items", "cargo_items"]:
                val = entry.get(key)
                if isinstance(val, list):
                    for nested in val:
                        add_from_entry(nested)
                    return

    for candidate in candidates:
        if isinstance(candidate, list):
            for entry in candidate:
                add_from_entry(entry)

    seen = set()
    unique = []
    for name in names:
        norm = _normalise_text(name)
        if norm and norm not in seen:
            unique.append(name)
            seen.add(norm)

    return unique


def _order_cargo_by_backend_sequence(payload: dict[str, Any], cargo_mix: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str], bool]:
    sequence = _extract_loading_sequence(payload)

    if not sequence:
        return cargo_mix, [item["name"] for item in cargo_mix], False

    sequence_norm = [_normalise_text(x) for x in sequence]

    def match_index(item: dict[str, Any]) -> int:
        name_norm = _normalise_text(item["name"])

        for idx, seq_name in enumerate(sequence_norm):
            if not seq_name:
                continue
            if name_norm == seq_name or name_norm in seq_name or seq_name in name_norm:
                return idx

        return 10_000 + int(item.get("original_index", 0))

    ordered = sorted(cargo_mix, key=match_index)
    return ordered, sequence, True


def _fit_orientation(length_m: float, width_m: float, container_length: float, container_width: float) -> tuple[float, float, bool]:
    # Rotate on floor if it helps fit across width/length.
    margin = 0.12

    normal_fits = length_m <= container_length - margin and width_m <= container_width - margin
    rotated_fits = width_m <= container_length - margin and length_m <= container_width - margin

    if normal_fits:
        return length_m, width_m, False

    if rotated_fits:
        return width_m, length_m, True

    # For wide items, choose orientation with smaller width demand.
    if length_m < width_m:
        return width_m, length_m, True

    return length_m, width_m, False


def _cargo_priority(item: dict[str, Any]) -> tuple[int, float, int]:
    """Lower priority number loads earlier."""
    tags = item.get("tags", [])
    volume = float(item["length_m"]) * float(item["width_m"]) * float(item["height_m"])

    if _has_tag(tags, "hazardous", "battery"):
        base = 0
    elif _has_tag(tags, "heavy"):
        base = 1
    elif not item.get("stackable", True):
        base = 2
    elif _has_tag(tags, "bulky"):
        base = 3
    elif _has_tag(tags, "fragile"):
        base = 4
    else:
        base = 5

    # Bigger items first inside the same category.
    return (base, -volume, int(item.get("original_index", 0)))


def _expand_items_for_visualizer(cargo_mix: list[dict[str, Any]], max_units: int = 220) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Expand cargo into drawable units while guaranteeing that every requested
    cargo type appears in the 3D visual.

    The first pass adds one representative unit per cargo type.
    The second pass fills remaining units round-robin, so high-quantity cargo
    like pillows cannot hide later cargo such as glass bottles.
    """
    units: list[dict[str, Any]] = []
    notes: list[str] = []

    if not cargo_mix:
        return units, notes

    drawn_by_name: dict[str, int] = {str(item["name"]): 0 for item in cargo_mix}

    for item in cargo_mix:
        if len(units) >= max_units:
            break

        quantity = int(item["quantity"])
        if quantity <= 0:
            continue

        unit = dict(item)
        unit["copy"] = 1
        unit["representative"] = True
        units.append(unit)
        drawn_by_name[str(item["name"])] += 1

    keep_going = True
    while keep_going and len(units) < max_units:
        keep_going = False

        for item in cargo_mix:
            if len(units) >= max_units:
                break

            name = str(item["name"])
            quantity = int(item["quantity"])
            already = drawn_by_name.get(name, 0)

            if already >= quantity:
                continue

            unit = dict(item)
            unit["copy"] = already + 1
            unit["representative"] = False
            units.append(unit)

            drawn_by_name[name] = already + 1
            keep_going = True

    for item in cargo_mix:
        name = str(item["name"])
        quantity = int(item["quantity"])
        drawn = drawn_by_name.get(name, 0)

        if drawn < quantity:
            notes.append(f"{name}: showing {drawn} of {quantity}; remaining units summarized.")

    if len(units) >= max_units:
        notes.append("Visualizer reached max drawable unit count; additional units are summarized only.")

    return units, notes


def _boxes_overlap(a: dict[str, Any], b: dict[str, Any], clearance: float = 0.006) -> bool:
    return not (
        a["max_x"] + clearance <= b["min_x"]
        or a["min_x"] >= b["max_x"] + clearance
        or a["max_y"] + clearance <= b["min_y"]
        or a["min_y"] >= b["max_y"] + clearance
        or a["max_z"] + clearance <= b["min_z"]
        or a["min_z"] >= b["max_z"] + clearance
    )


def _can_stack_visual_unit(unit: dict[str, Any], base: dict[str, Any]) -> bool:
    unit_tags = unit.get("tags", [])
    base_tags = base.get("tags", [])

    if _has_tag(unit_tags, "hazardous", "battery", "non_stackable"):
        return False

    if _has_tag(base_tags, "hazardous", "battery", "non_stackable", "fragile"):
        return False

    if unit["name"] == base["name"]:
        return True

    if _has_tag(unit_tags, "soft", "stackable") and not _has_tag(base_tags, "fragile"):
        return True

    return False


def _candidate_positions(placed: list[dict[str, Any]], unit: dict[str, Any], margin: float, gap: float) -> list[tuple[float, float, float, str]]:
    candidates: list[tuple[float, float, float, str]] = [(margin, margin, 0.0, "front-left-floor")]

    xs = {margin}
    zs = {margin}

    for b in placed:
        xs.add(round(b["min_x"], 4))
        xs.add(round(b["max_x"] + gap, 4))
        zs.add(round(b["min_z"], 4))
        zs.add(round(b["max_z"] + gap, 4))

        candidates.append((b["max_x"] + gap, b["min_z"], 0.0, "after-existing-length"))
        candidates.append((b["min_x"], b["max_z"] + gap, 0.0, "beside-existing-width"))
        candidates.append((b["max_x"] + gap, b["max_z"] + gap, 0.0, "corner-gap"))

        if _can_stack_visual_unit(unit, b):
            candidates.append((b["min_x"], b["min_z"], b["max_y"], "stack-on-compatible-cargo"))

    for x in sorted(xs):
        for z in sorted(zs):
            candidates.append((x, z, 0.0, "edge-grid-gap"))

    seen = set()
    unique: list[tuple[float, float, float, str]] = []

    for x, z, y, reason in candidates:
        key = (round(x, 3), round(z, 3), round(y, 3))
        if key not in seen:
            unique.append((x, z, y, reason))
            seen.add(key)

    return unique


def _try_place_unit(
    unit: dict[str, Any],
    placed: list[dict[str, Any]],
    container_length: float,
    container_width: float,
    container_height: float,
    margin: float,
    gap: float,
) -> dict[str, Any] | None:
    raw_l = float(unit["length_m"])
    raw_w = float(unit["width_m"])
    raw_h = float(unit["height_m"])

    orientations = []

    l1, w1, rotated1 = _fit_orientation(raw_l, raw_w, container_length, container_width)
    orientations.append((l1, w1, rotated1))

    if abs(raw_l - raw_w) > 0.001:
        orientations.append((raw_w, raw_l, True))

    best: tuple[tuple[float, float, float, float, float], dict[str, Any]] | None = None

    for l, w, rotated in orientations:
        if l <= 0 or w <= 0 or raw_h <= 0:
            continue

        for x, z, y in [(c[0], c[1], c[2]) for c in _candidate_positions(placed, unit, margin, gap)]:
            candidate = {
                "min_x": x,
                "max_x": x + l,
                "min_y": y,
                "max_y": y + raw_h,
                "min_z": z,
                "max_z": z + w,
            }

            if candidate["min_x"] < margin or candidate["min_z"] < margin:
                continue

            if candidate["max_x"] > container_length - margin:
                continue

            if candidate["max_z"] > container_width - margin:
                continue

            if candidate["max_y"] > container_height - margin:
                continue

            if any(_boxes_overlap(candidate, other) for other in placed):
                continue

            current_max_x = max([b["max_x"] for b in placed], default=margin)
            current_max_z = max([b["max_z"] for b in placed], default=margin)
            current_max_y = max([b["max_y"] for b in placed], default=0.0)

            new_max_x = max(current_max_x, candidate["max_x"])
            new_max_z = max(current_max_z, candidate["max_z"])
            new_max_y = max(current_max_y, candidate["max_y"])

            extends_length = max(0.0, new_max_x - current_max_x)
            extends_width = max(0.0, new_max_z - current_max_z)
            extends_height = max(0.0, new_max_y - current_max_y)

            score = (
                extends_length * 10.0 + extends_width * 4.0 + extends_height * 1.5,
                new_max_x * new_max_z * max(new_max_y, 0.01),
                x,
                z,
                y,
            )

            placed_candidate = {
                **candidate,
                "name": unit["name"],
                "copy": unit.get("copy", 1),
                "quantity": unit["quantity"],
                "x": x + l / 2 - container_length / 2,
                "y": y + raw_h / 2,
                "z": z + w / 2 - container_width / 2,
                "length": l,
                "width": w,
                "height": raw_h,
                "color": unit["color"],
                "tags": unit["tags"],
                "overflow": False,
                "stack_level": 1,
                "stack_count_at_position": 1,
                "notes": ["placed"] + (["rotated_on_floor"] if rotated else []),
            }

            if best is None or score < best[0]:
                best = (score, placed_candidate)

    return best[1] if best else None


def _pack_units_shelf_3d(
    units: list[dict[str, Any]],
    container_length: float,
    container_width: float,
    container_height: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    margin = 0.12
    gap = 0.025

    placed: list[dict[str, Any]] = []
    notes: list[str] = []
    overflow_count = 0

    for unit in units:
        placed_unit = _try_place_unit(
            unit=unit,
            placed=placed,
            container_length=container_length,
            container_width=container_width,
            container_height=container_height,
            margin=margin,
            gap=gap,
        )

        if placed_unit is not None:
            placed.append(placed_unit)
            continue

        raw_l = float(unit["length_m"])
        raw_w = float(unit["width_m"])
        raw_h = float(unit["height_m"])
        l, w, rotated = _fit_orientation(raw_l, raw_w, container_length, container_width)

        x = max(margin, container_length - margin - l)
        z = max(margin, container_width - margin - w)

        overflow_count += 1
        placed.append(
            {
                "min_x": x,
                "max_x": x + l,
                "min_y": 0.0,
                "max_y": min(raw_h, container_height - margin),
                "min_z": z,
                "max_z": z + w,
                "name": unit["name"],
                "copy": unit.get("copy", 1),
                "quantity": unit["quantity"],
                "x": x + l / 2 - container_length / 2,
                "y": min(raw_h, container_height - margin) / 2,
                "z": z + w / 2 - container_width / 2,
                "length": l,
                "width": w,
                "height": min(raw_h, container_height - margin),
                "color": unit["color"],
                "tags": unit["tags"],
                "overflow": True,
                "representative_preview": True,
                "stack_level": 1,
                "stack_count_at_position": 1,
                "notes": ["overflow"] + (["rotated_on_floor"] if rotated else []),
            }
        )

    requested_names = []
    for unit in units:
        name = str(unit["name"])
        if name not in requested_names:
            requested_names.append(name)

    visible_names = {str(box["name"]) for box in placed}
    missing_names = [name for name in requested_names if name not in visible_names]

    if missing_names:
        preview_z = margin

        for missing_name in missing_names:
            source_unit = next(unit for unit in units if str(unit["name"]) == missing_name)

            raw_l = float(source_unit["length_m"])
            raw_w = float(source_unit["width_m"])
            raw_h = float(source_unit["height_m"])
            l, w, rotated = _fit_orientation(raw_l, raw_w, container_length, container_width)

            x = max(margin, container_length - margin - l)
            z = min(max(margin, preview_z), max(margin, container_width - margin - w))
            preview_z += w + gap

            placed.append(
                {
                    "min_x": x,
                    "max_x": x + l,
                    "min_y": 0.0,
                    "max_y": min(raw_h, container_height - margin),
                    "min_z": z,
                    "max_z": z + w,
                    "name": source_unit["name"],
                    "copy": 1,
                    "quantity": source_unit["quantity"],
                    "x": x + l / 2 - container_length / 2,
                    "y": min(raw_h, container_height - margin) / 2,
                    "z": z + w / 2 - container_width / 2,
                    "length": l,
                    "width": w,
                    "height": min(raw_h, container_height - margin),
                    "color": source_unit["color"],
                    "tags": source_unit["tags"],
                    "overflow": True,
                    "representative_preview": True,
                    "stack_level": 1,
                    "stack_count_at_position": 1,
                    "notes": ["forced-visible-preview"] + (["rotated_on_floor"] if rotated else []),
                }
            )

        notes.append(
            "Forced visible preview added for: "
            + ", ".join(missing_names)
            + ". Exact dimensions may be needed to place these cleanly inside the container."
        )

    if overflow_count:
        notes.append(
            f"Overflow preview: {overflow_count} visual unit(s) could not be placed by the browser layout. "
            "Verify with exact carton dimensions before final booking."
        )

    return placed, notes
def _layout_utilization(boxes: list[dict[str, Any]], container: dict[str, Any]) -> dict[str, Any]:
    container_cbm = float(container["length_m"]) * float(container["width_m"]) * float(container["height_m"])

    active_boxes = [b for b in boxes if not b.get("overflow")]

    if not active_boxes:
        return {
            "used_length_m": 0,
            "used_width_m": 0,
            "used_height_m": 0,
            "visualized_cbm": 0,
            "container_cbm": round(container_cbm, 2),
            "remaining_cbm": round(container_cbm, 2),
            "utilization_percent": 0,
            "remaining_percent": 100,
            "free_visual_envelope_cbm": round(container_cbm, 2),
        }

    min_x = min(b["x"] - b["length"] / 2 for b in active_boxes)
    max_x = max(b["x"] + b["length"] / 2 for b in active_boxes)
    min_z = min(b["z"] - b["width"] / 2 for b in active_boxes)
    max_z = max(b["z"] + b["width"] / 2 for b in active_boxes)
    max_y = max(b["y"] + b["height"] / 2 for b in active_boxes)

    visualized_cbm = sum(
        float(b["length"]) * float(b["width"]) * float(b["height"])
        for b in active_boxes
    )

    utilization_percent = (visualized_cbm / container_cbm) * 100 if container_cbm else 0
    remaining_cbm = max(0.0, container_cbm - visualized_cbm)
    remaining_percent = max(0.0, 100.0 - utilization_percent)

    used_length = max_x - min_x
    used_width = max_z - min_z
    used_height = max_y
    used_envelope_cbm = max(0.0, used_length * used_width * used_height)
    free_visual_envelope_cbm = max(0.0, container_cbm - used_envelope_cbm)

    return {
        "used_length_m": round(used_length, 2),
        "used_width_m": round(used_width, 2),
        "used_height_m": round(used_height, 2),
        "visualized_cbm": round(visualized_cbm, 2),
        "container_cbm": round(container_cbm, 2),
        "remaining_cbm": round(remaining_cbm, 2),
        "utilization_percent": round(utilization_percent, 1),
        "remaining_percent": round(remaining_percent, 1),
        "free_visual_envelope_cbm": round(free_visual_envelope_cbm, 2),
    }
def build_layout(payload: dict[str, Any]) -> dict[str, Any]:
    container = _infer_container(payload)
    cargo_mix = _normalise_cargo_mix(payload)
    ordered_cargo, loading_sequence, used_backend_sequence = _order_cargo_by_backend_sequence(payload, cargo_mix)

    # If backend has no explicit loading sequence, use a safe logistics default:
    # hazardous/heavy/non-stackable/bulky first, then fragile/general.
    if not used_backend_sequence:
        ordered_cargo = sorted(ordered_cargo, key=_cargo_priority)

    container_length = float(container["length_m"])
    container_width = float(container["width_m"])
    container_height = float(container["height_m"])

    units, expansion_notes = _expand_items_for_visualizer(ordered_cargo)
    boxes, packing_notes = _pack_units_shelf_3d(units, container_length, container_width, container_height)
    utilization = _layout_utilization(boxes, container)

    notes: list[str] = []

    if used_backend_sequence:
        notes.append("Placement follows the logistics agent loading order.")
    else:
        notes.append("No explicit loading order was found, so the visualizer used safety priority: hazardous, heavy, and non-stackable cargo first.")

    fallback_items = [
        str(item["name"])
        for item in ordered_cargo
        if str(item.get("dimension_source", "")).startswith("fallback")
    ]

    if fallback_items:
        notes.append(
            "Estimated packed sizes were used for "
            + ", ".join(fallback_items)
            + ". Replace these with supplier carton dimensions before final booking."
        )

    notes.extend(expansion_notes)
    notes.extend(packing_notes)
    notes.append("This is an advisory loading view, not a certified stuffing plan.")
    notes.append("Before booking, confirm carton dimensions, lashing, axle/load distribution, carrier limits, and dangerous-goods rules.")

    return {
        "container": container,
        "cargo_mix": ordered_cargo,
        "boxes": boxes,
        "loading_sequence": loading_sequence,
        "used_backend_sequence": used_backend_sequence,
        "utilization": utilization,
        "notes": notes,
    }
def _side_panel_html(data: dict[str, Any]) -> str:
    container = data["container"]
    cargo_mix = data["cargo_mix"]
    utilization = data.get("utilization", {})

    legend_rows = []
    for item in cargo_mix:
        tags = ", ".join(item.get("tags", [])) or "general cargo"
        stackable = "stackable" if item.get("stackable") else "floor-loaded / non-stackable"
        dimension_source = item.get("dimension_source", "unknown")
        dims = f'{item["length_m"]:.2f}m × {item["width_m"]:.2f}m × {item["height_m"]:.2f}m'

        legend_rows.append(
            f"""
            <div class="legend-row">
              <span class="swatch" style="background:{html.escape(item['color'])}"></span>
              <div>
                <div><b>{html.escape(item['name'])}</b> × {item['quantity']}</div>
                <div class="muted">{html.escape(tags)} • {html.escape(stackable)}</div>
                <div class="muted">{html.escape(dims)} • {html.escape(dimension_source)}</div>
              </div>
            </div>
            """
        )

    used_percent = float(utilization.get("utilization_percent", 0) or 0)
    remaining_percent = float(utilization.get("remaining_percent", 100) or 100)

    space_html = f"""
      <h2>Container space</h2>
      <div class="space-card">
        <div class="space-head">
          <div>
            <div class="space-title">{used_percent:.1f}% used</div>
            <div class="muted">Based on visualized packed volume</div>
          </div>
          <div class="space-badge">{remaining_percent:.1f}% free</div>
        </div>

        <div class="space-bar">
          <div class="space-fill" style="width:{min(100, max(0, used_percent)):.1f}%"></div>
        </div>

        <div class="metric-grid">
          <div class="metric">
            <span>Loaded</span>
            <b>{float(utilization.get("visualized_cbm", 0) or 0):.2f} CBM</b>
          </div>
          <div class="metric">
            <span>Remaining</span>
            <b>{float(utilization.get("remaining_cbm", 0) or 0):.2f} CBM</b>
          </div>
          <div class="metric">
            <span>Container</span>
            <b>{float(utilization.get("container_cbm", 0) or 0):.2f} CBM</b>
          </div>
          <div class="metric">
            <span>Used envelope</span>
            <b>{float(utilization.get("used_length_m", 0) or 0):.2f}m × {float(utilization.get("used_width_m", 0) or 0):.2f}m × {float(utilization.get("used_height_m", 0) or 0):.2f}m</b>
          </div>
        </div>
      </div>
    """

    sequence_html = ""
    if data.get("loading_sequence"):
        rows = ""
        for idx, item in enumerate(data["loading_sequence"], start=1):
            rows += f"""
            <div class="order-step">
              <span class="order-number">{idx}</span>
              <span>{html.escape(str(item))}</span>
            </div>
            """

        sequence_html = f"""
        <h2>Loading order</h2>
        <div class="order-list">{rows}</div>
        """

    notes_html = "".join(f'<div class="interpretation-row"><span class="interpretation-dot"></span><span>{html.escape(str(note))}</span></div>' for note in data.get("notes", []) if note)

    return f"""
    <aside id="panel">
      <h1>3D Container Loading View</h1>
      <div class="sub">Container: {html.escape(str(container["name"]))}</div>
      <div class="sub">
        {container["length_m"]:.2f}m L × {container["width_m"]:.2f}m W × {container["height_m"]:.2f}m H
      </div>

      <h2>Cargo legend</h2>
      {''.join(legend_rows) or '<div class="sub">No cargo boxes available.</div>'}

      {space_html}

      {sequence_html}

      <div class="note">
        <div class="note-title">Loading interpretation</div>
        <div class="interpretation-list">{notes_html}</div>
      </div>
    </aside>
    """
def build_container_3d_html(payload: dict[str, Any]) -> str:
    data = build_layout(payload)
    data_json = json.dumps(data)
    panel_html = _side_panel_html(data)

    template = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Container 3D Load Viewer</title>
  <style>
    body {
      margin: 0;
      background: #07111f;
      color: #e9eef7;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif;
      overflow: hidden;
    }
    #wrap {
      display: grid;
      grid-template-columns: 1fr 380px;
      height: 100vh;
      width: 100vw;
    }
    #scene {
      position: relative;
      min-width: 0;
    }
    #panel {
      border-left: 1px solid rgba(255,255,255,0.12);
      background: rgba(8, 17, 31, 0.96);
      padding: 18px;
      overflow: auto;
    }
    h1 {
      font-size: 18px;
      margin: 0 0 8px;
    }
    h2 {
      font-size: 15px;
      margin: 20px 0 8px;
    }
    .sub {
      color: #9fb0c7;
      font-size: 13px;
      margin-bottom: 8px;
    }
    .muted {
      color: #9fb0c7;
      font-size: 12px;
      line-height: 1.35;
      margin-top: 2px;
    }
    .legend-row {
      display: flex;
      gap: 10px;
      align-items: flex-start;
      padding: 10px 0;
      border-bottom: 1px solid rgba(255,255,255,0.08);
      font-size: 13px;
    }
    .swatch {
      width: 16px;
      height: 16px;
      border-radius: 4px;
      flex: 0 0 auto;
      margin-top: 3px;
      box-shadow: 0 0 0 1px rgba(255,255,255,0.35);
    }
    .sequence {
      color: #cbd6e6;
      font-size: 13px;
      padding-left: 20px;
      line-height: 1.45;
    }
    .space-card {
      margin-top: 10px;
      padding: 14px;
      border-radius: 14px;
      background: rgba(76, 201, 240, 0.08);
      border: 1px solid rgba(76, 201, 240, 0.24);
    }
    .space-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }
    .space-title {
      font-size: 22px;
      font-weight: 800;
      color: #eaf7ff;
      line-height: 1.1;
    }
    .space-badge {
      flex: 0 0 auto;
      border-radius: 999px;
      padding: 6px 10px;
      background: rgba(128, 237, 153, 0.12);
      border: 1px solid rgba(128, 237, 153, 0.35);
      color: #9dffb5;
      font-size: 12px;
      font-weight: 800;
    }
    .space-bar {
      height: 10px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(255,255,255,0.11);
      margin-bottom: 12px;
    }
    .space-fill {
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #4cc9f0, #80ed99);
    }
    .metric-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .metric {
      padding: 9px 10px;
      border-radius: 10px;
      background: rgba(255,255,255,0.055);
      border: 1px solid rgba(255,255,255,0.08);
    }
    .metric span {
      display: block;
      color: #9fb0c7;
      font-size: 11px;
      margin-bottom: 4px;
    }
    .metric b {
      display: block;
      color: #ffffff;
      font-size: 13px;
      line-height: 1.25;
    }
    .order-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 10px;
    }
    .order-step {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 10px;
      border-radius: 11px;
      background: rgba(255,255,255,0.055);
      border: 1px solid rgba(255,255,255,0.08);
      font-size: 13px;
      color: #e9eef7;
    }
    .order-number {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: rgba(122,162,255,0.18);
      border: 1px solid rgba(122,162,255,0.35);
      color: #dbe6ff;
      font-size: 12px;
      font-weight: 800;
      flex: 0 0 auto;
    }
    .note {
      margin-top: 18px;
      padding: 14px;
      background: rgba(255, 209, 102, 0.10);
      border: 1px solid rgba(255, 209, 102, 0.35);
      border-radius: 14px;
      font-size: 13px;
      line-height: 1.45;
    }
    .note-title {
      font-weight: 850;
      color: #fff7df;
      margin-bottom: 10px;
      font-size: 15px;
    }
    .interpretation-list {
      display: flex;
      flex-direction: column;
      gap: 9px;
    }
    .interpretation-row {
      display: grid;
      grid-template-columns: 8px 1fr;
      gap: 10px;
      align-items: start;
      padding: 9px 10px;
      border-radius: 10px;
      background: rgba(255,255,255,0.045);
      border: 1px solid rgba(255,255,255,0.06);
      color: #e9eef7;
    }
    .interpretation-dot {
      width: 7px;
      height: 7px;
      margin-top: 7px;
      border-radius: 50%;
      background: #ffd166;
      box-shadow: 0 0 0 3px rgba(255, 209, 102, 0.12);
    }
    li {
      margin-bottom: 8px;
    }
    #hint {
      position: absolute;
      left: 14px;
      bottom: 14px;
      padding: 10px 12px;
      background: rgba(0,0,0,0.45);
      border-radius: 10px;
      font-size: 12px;
      color: #cbd6e6;
    }
  </style>
</head>
<body>
  <div id="wrap">
    <div id="scene">
      <div id="hint">Drag to rotate • Scroll to zoom • Right-click drag to pan</div>
    </div>
    __PANEL_HTML__
  </div>

  <script type="module">
    import * as THREE from "https://esm.sh/three@0.160.0";
    import { OrbitControls } from "https://esm.sh/three@0.160.0/examples/jsm/controls/OrbitControls.js";

    const data = __DATA_JSON__;
    const container = data.container;
    const boxes = data.boxes || [];

    const sceneDiv = document.getElementById("scene");
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07111f);

    const camera = new THREE.PerspectiveCamera(45, sceneDiv.clientWidth / sceneDiv.clientHeight, 0.1, 100);
    camera.position.set(7.5, 4.5, 7.5);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(sceneDiv.clientWidth, sceneDiv.clientHeight);
    sceneDiv.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.8, 0);
    controls.enableDamping = true;

    scene.add(new THREE.AmbientLight(0xffffff, 0.75));

    const directional = new THREE.DirectionalLight(0xffffff, 1.1);
    directional.position.set(3, 7, 5);
    scene.add(directional);

    const L = container.length_m || 5.9;
    const W = container.width_m || 2.35;
    const H = container.height_m || 2.39;

    const floor = new THREE.Mesh(
      new THREE.BoxGeometry(L, 0.035, W),
      new THREE.MeshStandardMaterial({ color: 0x16263d, roughness: 0.8 })
    );
    floor.position.set(0, -0.017, 0);
    scene.add(floor);

    const containerBox = new THREE.BoxGeometry(L, H, W);

    const transparentShell = new THREE.Mesh(
      containerBox,
      new THREE.MeshStandardMaterial({
        color: 0x1d3557,
        transparent: true,
        opacity: 0.06,
        roughness: 0.7,
        metalness: 0.0
      })
    );
    transparentShell.position.set(0, H / 2, 0);
    scene.add(transparentShell);

    const edges = new THREE.EdgesGeometry(containerBox);
    const wire = new THREE.LineSegments(
      edges,
      new THREE.LineBasicMaterial({ color: 0x7aa2ff, transparent: true, opacity: 0.9 })
    );
    wire.position.set(0, H / 2, 0);
    scene.add(wire);

    const grid = new THREE.GridHelper(Math.max(L, 7), Math.max(10, Math.round(L * 2)), 0x315070, 0x1c314f);
    grid.position.y = 0.002;
    scene.add(grid);

    function makeBoxLabel(text, cargoColor) {
      const canvas = document.createElement("canvas");
      canvas.width = 640;
      canvas.height = 150;

      const context = canvas.getContext("2d");
      const color = cargoColor || "#ffffff";

      context.clearRect(0, 0, canvas.width, canvas.height);

      // Label background.
      context.fillStyle = "rgba(8, 17, 31, 0.90)";
      roundRect(context, 0, 0, canvas.width, canvas.height, 18);
      context.fill();

      // Cargo-color stripe. This makes the label match the cargo visually.
      context.fillStyle = color;
      roundRect(context, 0, 0, 22, canvas.height, 12);
      context.fill();

      // Soft border.
      context.strokeStyle = color;
      context.lineWidth = 5;
      roundRect(context, 2, 2, canvas.width - 4, canvas.height - 4, 18);
      context.stroke();

      context.fillStyle = "#ffffff";
      context.font = "bold 46px system-ui";
      context.fillText(String(text).slice(0, 20), 42, 92);

      const texture = new THREE.CanvasTexture(canvas);
      texture.needsUpdate = true;

      const material = new THREE.SpriteMaterial({
        map: texture,
        transparent: true,
        depthTest: false,
        depthWrite: false
      });

      const sprite = new THREE.Sprite(material);
      sprite.scale.set(1.45, 0.34, 1);
      return sprite;
    }

    function roundRect(context, x, y, width, height, radius) {
      const r = Math.min(radius, width / 2, height / 2);
      context.beginPath();
      context.moveTo(x + r, y);
      context.arcTo(x + width, y, x + width, y + height, r);
      context.arcTo(x + width, y + height, x, y + height, r);
      context.arcTo(x, y + height, x, y, r);
      context.arcTo(x, y, x + width, y, r);
      context.closePath();
    }

    function addLabelPointerLine(start, end, color) {
      const points = [
        new THREE.Vector3(start.x, start.y, start.z),
        new THREE.Vector3(end.x, end.y, end.z)
      ];

      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const material = new THREE.LineBasicMaterial({
        color: new THREE.Color(color || "#ffffff"),
        transparent: true,
        opacity: 0.95,
        depthTest: false,
        depthWrite: false
      });

      const line = new THREE.Line(geometry, material);
      line.renderOrder = 998;
      scene.add(line);
    }

    const groupBounds = new Map();

    function updateGroupBounds(box) {
      if (!groupBounds.has(box.name)) {
        groupBounds.set(box.name, {
          minX: Infinity,
          maxX: -Infinity,
          minY: Infinity,
          maxY: -Infinity,
          minZ: Infinity,
          maxZ: -Infinity,
          color: box.color || "#ffffff"
        });
      }

      const bounds = groupBounds.get(box.name);
      bounds.minX = Math.min(bounds.minX, box.x - box.length / 2);
      bounds.maxX = Math.max(bounds.maxX, box.x + box.length / 2);
      bounds.minY = Math.min(bounds.minY, box.y - box.height / 2);
      bounds.maxY = Math.max(bounds.maxY, box.y + box.height / 2);
      bounds.minZ = Math.min(bounds.minZ, box.z - box.width / 2);
      bounds.maxZ = Math.max(bounds.maxZ, box.z + box.width / 2);
    }

    boxes.forEach((box) => {
      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(box.color || "#80ed99"),
        roughness: 0.55,
        metalness: 0.05,
        transparent: Boolean(box.overflow),
        opacity: box.overflow ? 0.42 : 0.92
      });

      const geometry = new THREE.BoxGeometry(box.length, box.height, box.width);
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(box.x, box.y, box.z);
      scene.add(mesh);

      const outline = new THREE.LineSegments(
        new THREE.EdgesGeometry(geometry),
        new THREE.LineBasicMaterial({ color: 0x06111f, transparent: true, opacity: 0.55 })
      );
      outline.position.copy(mesh.position);
      scene.add(outline);

      if (!box.overflow) {
        updateGroupBounds(box);
      }
    });

    groupBounds.forEach((bounds, cargoName) => {
      const centerX = (bounds.minX + bounds.maxX) / 2;
      const centerZ = (bounds.minZ + bounds.maxZ) / 2;
      const cargoColor = bounds.color || "#ffffff";

      const anchor = {
        x: centerX,
        y: bounds.maxY + 0.03,
        z: centerZ
      };

      const labelPosition = {
        x: centerX,
        y: bounds.maxY + 0.58,
        z: centerZ
      };

      const label = makeBoxLabel(cargoName, cargoColor);
      label.position.set(labelPosition.x, labelPosition.y, labelPosition.z);
      label.renderOrder = 999;
      label.material.depthTest = false;
      label.material.depthWrite = false;
      scene.add(label);

      // Pointer line removes ambiguity when labels overlap in perspective view.
      addLabelPointerLine(anchor, {
        x: labelPosition.x,
        y: labelPosition.y - 0.17,
        z: labelPosition.z
      }, cargoColor);
    });

    function animate() {
      controls.update();
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    }

    window.addEventListener("resize", () => {
      camera.aspect = sceneDiv.clientWidth / sceneDiv.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(sceneDiv.clientWidth, sceneDiv.clientHeight);
    });

    animate();
  </script>
</body>
</html>
"""

    return template.replace("__DATA_JSON__", data_json).replace("__PANEL_HTML__", panel_html)


def write_container_3d_html(payload: dict[str, Any], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_container_3d_html(payload), encoding="utf-8")
    return path
