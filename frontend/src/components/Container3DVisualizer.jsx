import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

const UNIQUE_CARGO_COLORS = [
  "#ff6b4a",
  "#4cc9f0",
  "#ffd166",
  "#80ed99",
  "#b388ff",
  "#f72585",
  "#43aa8b",
  "#f8961e",
  "#90be6d",
  "#577590",
  "#e76f51",
  "#2a9d8f",
  "#e9c46a",
  "#a78bfa",
  "#06b6d4",
  "#f43f5e",
];

function cargoColorForItem(name, index) {
  return UNIQUE_CARGO_COLORS[index % UNIQUE_CARGO_COLORS.length];
}

const CONTAINER_SPECS = {
  "20ft": {
    name: "20ft Standard Container",
    length_m: 5.9,
    width_m: 2.35,
    height_m: 2.39,
    safe_capacity_cbm: 28,
  },
  "40ft": {
    name: "40ft Standard Container",
    length_m: 12.03,
    width_m: 2.35,
    height_m: 2.39,
    safe_capacity_cbm: 58,
  },
  "40ft_hc": {
    name: "40ft High Cube Container",
    length_m: 12.03,
    width_m: 2.35,
    height_m: 2.69,
    safe_capacity_cbm: 66,
  },
};

function asNumber(value, fallback = null) {
  const n = Number(String(value ?? "").replaceAll(",", "").trim());
  return Number.isFinite(n) ? n : fallback;
}

function asInt(value, fallback = 1) {
  const n = asNumber(value, fallback);
  return Math.max(1, Math.trunc(n));
}

function cleanText(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function hasTag(tags, ...needles) {
  const normalized = new Set((tags || []).map((t) => cleanText(t).replaceAll(" ", "_")));
  return needles.some((needle) => normalized.has(cleanText(needle).replaceAll(" ", "_")));
}

function getNested(obj, ...keys) {
  let current = obj;
  for (const key of keys) {
    if (!current || typeof current !== "object") return null;
    current = current[key];
  }
  return current;
}

function getVisualizer(result) {
  if (result?.logistics_visualizer && typeof result.logistics_visualizer === "object") {
    return result.logistics_visualizer;
  }

  return (
    getNested(result, "_raw_user_agent_response", "logistics_visualizer") ||
    getNested(result, "_raw_user_agent_response", "specialist_response", "logistics_visualizer") ||
    null
  );
}

export function hasContainer3DData(result) {
  if (!result || typeof result !== "object") return false;
  if (result.detected_intent === "booking_information") return false;
  if (result.status === "needs_more_information") return false;

  const visualizer = getVisualizer(result);
  const cargoMix = visualizer?.cargo_mix;

  return Array.isArray(cargoMix) && cargoMix.some((item) => item && typeof item === "object");
}

function inferContainer(result) {
  const visualizer = getVisualizer(result) || {};
  const c = visualizer.container || {};
  const selected =
    c.selected_container ||
    c.recommended_container ||
    result?.recommended_container ||
    result?.logistics_metrics?.recommended_container ||
    "";

  const selectedText = String(selected).toLowerCase();

  let base;
  if (selectedText.includes("40") && (selectedText.includes("high") || selectedText.includes("hc") || selectedText.includes("cube"))) {
    base = { ...CONTAINER_SPECS["40ft_hc"] };
  } else if (selectedText.includes("40")) {
    base = { ...CONTAINER_SPECS["40ft"] };
  } else {
    base = { ...CONTAINER_SPECS["20ft"] };
  }

  base.name = selected || base.name;

  for (const key of ["length_m", "width_m", "height_m", "safe_capacity_cbm"]) {
    const val = asNumber(c[key], null);
    if (val && val > 0) base[key] = val;
  }

  return base;
}

function extractTags(item) {
  let tags = item.category_tags || item.cargo_categories || item.tags || item.labels || [];
  if (typeof tags === "string") tags = tags.split(/[,/|]+/);
  if (!Array.isArray(tags)) tags = [];

  const result = tags.map((t) => String(t).trim()).filter(Boolean);
  const nameText = cleanText(item.item_name || item.name || item.item || item.product || "");

  const inferred = [];
  if (["glass", "bottle", "tv", "television", "mirror", "ceramic"].some((w) => nameText.includes(w))) inferred.push("fragile");
  if (["scooter", "battery", "lithium", "electric"].some((w) => nameText.includes(w))) inferred.push("hazardous", "battery");
  if (["mattress", "sofa", "dining", "furniture"].some((w) => nameText.includes(w))) inferred.push("bulky");
  const weightKnown = item.weight_known !== false &&
    item.measurement_status?.weight_known !== false;

  if (
    weightKnown &&
    ["machinery", "engine", "tiles"].some((w) => nameText.includes(w))
  ) inferred.push("heavy");

  const existing = new Set(result.map((t) => cleanText(t).replaceAll(" ", "_")));
  for (const tag of inferred) {
    const key = cleanText(tag).replaceAll(" ", "_");
    if (!existing.has(key)) result.push(tag);
  }

  return result;
}

function parseDimensionString(text) {
  if (!text) return null;
  const lower = String(text).toLowerCase();
  const nums = [...lower.matchAll(/\d+(?:\.\d+)?/g)].map((m) => Number(m[0]));
  if (nums.length < 3) return null;

  let vals = nums.slice(0, 3);
  if (lower.includes("cm")) vals = vals.map((v) => v / 100);
  else if (lower.includes("mm")) vals = vals.map((v) => v / 1000);
  else if (lower.includes("inch") || lower.includes(" in")) vals = vals.map((v) => v * 0.0254);
  else if (lower.includes("ft") || lower.includes("feet")) vals = vals.map((v) => v * 0.3048);

  return vals;
}

function heuristicDimensions(name, tags) {
  const text = cleanText(name);
  const rules = [
    [["electric scooter", "scooter"], [1.8, 0.7, 1.1], "estimated scooter pack"],
    [["tv", "television"], [1.2, 0.2, 0.8], "estimated TV carton"],
    [["mattress"], [2.0, 0.35, 1.0], "estimated mattress pack"],
    [["pillow"], [0.5, 0.35, 0.2], "estimated pillow carton"],
    [["glass bottle", "bottle"], [0.4, 0.3, 0.3], "estimated bottle carton"],
    [["ceramic tile", "tiles", "tile"], [0.6, 0.4, 0.25], "estimated tile carton"],
    [["dining set", "dining", "table", "chair"], [1.5, 0.8, 0.7], "estimated dining set pack"],
    [["sofa", "couch"], [1.8, 0.9, 0.8], "estimated sofa pack"],
    [["furniture", "cabinet", "wardrobe"], [1.2, 0.8, 0.8], "estimated furniture pack"],
  ];

  for (const [keywords, dims, source] of rules) {
    if (keywords.some((k) => text.includes(k))) return [...dims, source];
  }

  if (hasTag(tags, "heavy")) return [1.0, 0.8, 0.7, "estimated heavy cargo"];
  if (hasTag(tags, "fragile")) return [0.8, 0.5, 0.5, "estimated fragile cargo"];
  if (hasTag(tags, "bulky")) return [1.2, 0.8, 0.8, "estimated bulky cargo"];

  return [0.8, 0.6, 0.6, "estimated general cargo"];
}

function extractDimensions(item, name, tags, quantity) {
  const aggregateOnly =
    item.aggregate_volume_only === true ||
    item.dimensions_are_aggregate === true ||
    item.display_dimensions_estimated === true ||
    item.packed_dimensions_known === false;

  if (aggregateOnly) {
    if (item.dimensions_m && typeof item.dimensions_m === "object") {
      const l = asNumber(item.dimensions_m.length, null);
      const w = asNumber(item.dimensions_m.width, null);
      const h = asNumber(item.dimensions_m.height, null);

      if (l && w && h) {
        return [
          l,
          w,
          h,
          "advisory aggregate-volume representation",
        ];
      }
    }

    const totalCbm = asNumber(
      item.total_cbm ?? item.cbm,
      null
    );

    if (totalCbm && totalCbm > 0) {
      const unitVolume =
        totalCbm / Math.max(1, quantity);
      const side = Math.cbrt(
        Math.max(unitVolume, 0.001)
      );

      return [
        side,
        side,
        side,
        "advisory aggregate-volume representation",
      ];
    }
  }

  if (item.dimensions_m && typeof item.dimensions_m === "object") {
    const l = asNumber(item.dimensions_m.length, null);
    const w = asNumber(item.dimensions_m.width, null);
    const h = asNumber(item.dimensions_m.height, null);
    if (l && w && h) return [l, w, h, "backend dimensions"];
  }

  if (item.dimensions_cm && typeof item.dimensions_cm === "object") {
    const l = asNumber(item.dimensions_cm.length, null);
    const w = asNumber(item.dimensions_cm.width, null);
    const h = asNumber(item.dimensions_cm.height, null);
    if (l && w && h) return [l / 100, w / 100, h / 100, "backend cm dimensions"];
  }

  const directL = asNumber(item.length_m, null);
  const directW = asNumber(item.width_m, null);
  const directH = asNumber(item.height_m, null);
  if (directL && directW && directH) return [directL, directW, directH, "backend dimensions"];

  for (const key of ["dimensions", "packed_dimensions", "unit_dimensions", "size"]) {
    if (typeof item[key] === "string") {
      const parsed = parseDimensionString(item[key]);
      if (parsed) return [...parsed, `backend ${key}`];
    }
  }

  let unitCbm = asNumber(item.unit_cbm ?? item.cbm_per_unit ?? item.volume_cbm_per_unit, null);
  const totalCbm = asNumber(item.total_cbm ?? item.cbm ?? item.volume_cbm, null);
  if (!unitCbm && totalCbm && quantity > 0) unitCbm = totalCbm / quantity;

  if (unitCbm && unitCbm > 0) {
    const side = Math.max(0.25, Math.cbrt(unitCbm));
    return [side * 1.25, side, side * 0.8, "estimated from CBM"];
  }

  return heuristicDimensions(name, tags);
}

function categoryColor(tags, name) {
  if (hasTag(tags, "hazardous", "battery")) return "#ff6b4a";
  if (hasTag(tags, "fragile")) return "#4cc9f0";
  if (hasTag(tags, "heavy")) return "#ffd166";
  if (hasTag(tags, "bulky")) return "#b388ff";

  const text = cleanText(name);
  if (text.includes("mattress") || text.includes("furniture") || text.includes("dining")) return "#b388ff";

  return "#80ed99";
}

function normalizeCargoMix(result) {
  const visualizer = getVisualizer(result) || {};
  let cargoMix = visualizer.cargo_mix;

  if (!Array.isArray(cargoMix)) {
    cargoMix = getNested(result, "_raw_user_agent_response", "specialist_response", "plan", "item_breakdown");
  }

  if (!Array.isArray(cargoMix)) cargoMix = [];

  return cargoMix
    .filter((item) => item && typeof item === "object")
    .map((item, idx) => {
      const name = item.item_name || item.name || item.item || item.product || item.cargo_type || `Cargo item ${idx + 1}`;
      const quantity = asInt(item.quantity || item.qty || item.count, 1);
      const tags = extractTags(item);
      const [length_m, width_m, height_m, dimension_source] = extractDimensions(item, name, tags, quantity);

      const stackable =
        typeof item.stackable === "boolean"
          ? item.stackable
          : !hasTag(tags, "non_stackable", "hazardous", "battery");

      return {
        name: String(name),
        quantity,
        length_m: Math.max(0.05, length_m),
        width_m: Math.max(0.05, width_m),
        height_m: Math.max(0.05, height_m),
        total_cbm: asNumber(item.total_cbm ?? item.cbm ?? item.volume_cbm, null),
        unit_cbm: asNumber(item.unit_cbm ?? item.cbm_per_unit ?? item.volume_cbm_per_unit, null),
        aggregate_volume_only: item.aggregate_volume_only === true,
        dimensions_are_aggregate: item.dimensions_are_aggregate === true,
        tags,
        color: cargoColorForItem(name, idx),
        stackable,
        dimension_source,
        original_index: idx,
      };
    });
}

function extractLoadingSequence(result) {
  const visualizer = getVisualizer(result) || {};
  const candidates = [
    visualizer.loading_sequence,
    visualizer.load_sequence,
    visualizer.packing_sequence,
    result?.loading_sequence,
    result?.logistics_plan?.loading_sequence,
    getNested(result, "_raw_user_agent_response", "specialist_response", "plan", "loading_sequence"),
  ];

  const names = [];

  const addEntry = (entry) => {
    if (typeof entry === "string" && entry.trim()) {
      names.push(entry.trim());
      return;
    }

    if (entry && typeof entry === "object") {
      for (const key of ["item_name", "name", "item", "cargo", "cargo_type", "load", "description"]) {
        if (typeof entry[key] === "string" && entry[key].trim()) {
          names.push(entry[key].trim());
          return;
        }
      }

      for (const key of ["items", "cargo_items"]) {
        if (Array.isArray(entry[key])) entry[key].forEach(addEntry);
      }
    }
  };

  candidates.forEach((candidate) => {
    if (Array.isArray(candidate)) candidate.forEach(addEntry);
  });

  const seen = new Set();
  const unique = [];

  for (const name of names) {
    const norm = cleanText(name);
    if (norm && !seen.has(norm)) {
      unique.push(name);
      seen.add(norm);
    }
  }

  return unique;
}

// CONTAINER_LAYOUT_POLISH_V5
function orderCargo(result, cargoMix) {
  const sequence = extractLoadingSequence(result);

  if (!sequence.length) {
    const priority = (item) => {
      const volume = item.length_m * item.width_m * item.height_m;
      let base = 5;
      if (hasTag(item.tags, "hazardous", "battery")) base = 0;
      else if (hasTag(item.tags, "heavy")) base = 1;
      else if (!item.stackable) base = 2;
      else if (hasTag(item.tags, "bulky")) base = 3;
      else if (hasTag(item.tags, "fragile")) base = 4;
      return [base, -volume, item.original_index];
    };

    const sortedCargo = [...cargoMix].sort((a, b) => {
      const aa = priority(a);
      const bb = priority(b);
      return aa[0] - bb[0] || aa[1] - bb[1] || aa[2] - bb[2];
    });

    return {
      cargo: sortedCargo,
      loading_order_source: "safety_generated",
      sequence: sortedCargo.map((item) => item.name),
      usedBackendSequence: false,
    };
  }

  const normSeq = sequence.map(cleanText);

  const matchIndex = (item) => {
    const itemName = cleanText(item.name);
    const idx = normSeq.findIndex(
      (seqName) =>
        itemName === seqName ||
        itemName.includes(seqName) ||
        seqName.includes(itemName)
    );
    return idx >= 0 ? idx : 10000 + item.original_index;
  };

  const sortedCargo = [...cargoMix].sort((a, b) => matchIndex(a) - matchIndex(b));

  return {
    cargo: sortedCargo,
    loading_order_source: "backend_sequence",
    sequence: sequence.length ? sequence : sortedCargo.map((item) => item.name),
    usedBackendSequence: true,
  };
}

function expandUnits(cargoMix, maxUnits = 220) {
  const units = [];
  const notes = [];
  const drawnByName = Object.fromEntries(cargoMix.map((item) => [item.name, 0]));

  for (const item of cargoMix) {
    if (units.length >= maxUnits) break;
    if (item.quantity <= 0) continue;

    units.push({ ...item, copy: 1, representative: true });
    drawnByName[item.name] += 1;
  }

  let keepGoing = true;
  while (keepGoing && units.length < maxUnits) {
    keepGoing = false;

    for (const item of cargoMix) {
      if (units.length >= maxUnits) break;

      const already = drawnByName[item.name] || 0;
      if (already >= item.quantity) continue;

      units.push({ ...item, copy: already + 1, representative: false });
      drawnByName[item.name] = already + 1;
      keepGoing = true;
    }
  }

  for (const item of cargoMix) {
    const drawn = drawnByName[item.name] || 0;
    if (drawn < item.quantity) notes.push(`${item.name}: showing ${drawn} of ${item.quantity}; remaining units summarized.`);
  }

  return { units, notes };
}

function fitOrientation(length_m, width_m, containerLength, containerWidth) {
  const margin = 0.12;
  const normalFits = length_m <= containerLength - margin && width_m <= containerWidth - margin;
  const rotatedFits = width_m <= containerLength - margin && length_m <= containerWidth - margin;

  if (normalFits) return [length_m, width_m, false];
  if (rotatedFits) return [width_m, length_m, true];
  if (length_m < width_m) return [width_m, length_m, true];

  return [length_m, width_m, false];
}

function boxesOverlap(a, b, clearance = 0.006) {
  return !(
    a.max_x + clearance <= b.min_x ||
    a.min_x >= b.max_x + clearance ||
    a.max_y + clearance <= b.min_y ||
    a.min_y >= b.max_y + clearance ||
    a.max_z + clearance <= b.min_z ||
    a.min_z >= b.max_z + clearance
  );
}

function canStack(unit, base) {
  // Aggregate preview blocks represent volume cells, not literal cartons.
  if (unit.aggregate_preview && base.aggregate_preview) return true;

  if (hasTag(unit.tags, "hazardous", "battery", "non_stackable")) return false;
  if (hasTag(base.tags, "hazardous", "battery", "non_stackable", "fragile")) return false;
  if (unit.name === base.name) return true;

  return hasTag(unit.tags, "soft", "stackable") && !hasTag(base.tags, "fragile");
}

function candidatePositions(placed, unit, margin, gap) {
  const candidates = [[margin, margin, 0]];
  const xs = new Set([margin]);
  const zs = new Set([margin]);

  for (const b of placed) {
    xs.add(Number(b.min_x.toFixed(4)));
    xs.add(Number((b.max_x + gap).toFixed(4)));
    zs.add(Number(b.min_z.toFixed(4)));
    zs.add(Number((b.max_z + gap).toFixed(4)));

    candidates.push([b.max_x + gap, b.min_z, 0]);
    candidates.push([b.min_x, b.max_z + gap, 0]);
    candidates.push([b.max_x + gap, b.max_z + gap, 0]);

    // Leave a real clearance between vertical layers. The old code used
    // b.max_y directly, so the overlap clearance rejected valid stacking.
    if (canStack(unit, b)) candidates.push([b.min_x, b.min_z, b.max_y + gap]);
  }

  for (const x of [...xs].sort((a, b) => a - b)) {
    for (const z of [...zs].sort((a, b) => a - b)) {
      candidates.push([x, z, 0]);
    }
  }

  const seen = new Set();
  return candidates.filter(([x, z, y]) => {
    const key = `${x.toFixed(3)}|${z.toFixed(3)}|${y.toFixed(3)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function tryPlaceUnit(unit, placed, containerLength, containerWidth, containerHeight, margin, gap) {
  const orientations = [];
  const [l1, w1, r1] = fitOrientation(unit.length_m, unit.width_m, containerLength, containerWidth);
  orientations.push([l1, w1, r1]);

  if (Math.abs(unit.length_m - unit.width_m) > 0.001) {
    orientations.push([unit.width_m, unit.length_m, true]);
  }

  let best = null;

  for (const [l, w, rotated] of orientations) {
    for (const [x, z, y] of candidatePositions(placed, unit, margin, gap)) {
      const candidate = {
        min_x: x,
        max_x: x + l,
        min_y: y,
        max_y: y + unit.height_m,
        min_z: z,
        max_z: z + w,
      };

      if (candidate.min_x < margin || candidate.min_z < margin) continue;
      if (candidate.max_x > containerLength - margin + 0.0001) continue;
      if (candidate.max_z > containerWidth - margin + 0.0001) continue;
      if (candidate.max_y > containerHeight - margin + 0.0001) continue;
      if (placed.some((other) => boxesOverlap(candidate, other))) continue;

      const currentMaxX = Math.max(margin, ...placed.map((b) => b.max_x));
      const currentMaxZ = Math.max(margin, ...placed.map((b) => b.max_z));
      const currentMaxY = Math.max(0, ...placed.map((b) => b.max_y));

      const newMaxX = Math.max(currentMaxX, candidate.max_x);
      const newMaxZ = Math.max(currentMaxZ, candidate.max_z);
      const newMaxY = Math.max(currentMaxY, candidate.max_y);

      const extendsLength = Math.max(0, newMaxX - currentMaxX);
      const extendsWidth = Math.max(0, newMaxZ - currentMaxZ);
      const extendsHeight = Math.max(0, newMaxY - currentMaxY);

      // Prefer the orientation that creates the most usable floor slots, then fill the floor before stacking.
      const lengthSlots = Math.max(1, Math.floor((containerLength - margin * 2 + gap) / (l + gap)));
      const widthSlots = Math.max(1, Math.floor((containerWidth - margin * 2 + gap) / (w + gap)));
      const orientationPenalty = 1000 / Math.max(1, lengthSlots * widthSlots);
      const score = y * 1000 + orientationPenalty + extendsLength * 10 + extendsWidth * 4 + extendsHeight * 20 + newMaxX * newMaxZ * Math.max(newMaxY, 0.01) * 0.01;

      const placedCandidate = {
        ...candidate,
        name: unit.name,
        copy: unit.copy || 1,
        quantity: unit.quantity,
        x: x + l / 2 - containerLength / 2,
        y: y + unit.height_m / 2,
        z: z + w / 2 - containerWidth / 2,
        length: l,
        width: w,
        height: unit.height_m,
        color: unit.color,
        tags: unit.tags,
        overflow: false,
        notes: rotated ? ["rotated_on_floor"] : [],
      };

      if (!best || score < best.score) best = { score, box: placedCandidate };
    }
  }

  return best?.box || null;
}

// BOUNDED_CONTAINER_LAYOUT_V4
//
// The visual preview must never create cargo geometry outside the physical
// reference container. Aggregate CBM is represented by bounded volume cells,
// not by one cube-root-derived fake carton.
function shouldUseAggregatePreview(unit) {
  const totalCbm = asNumber(unit.total_cbm, null);
  if (!(totalCbm > 0)) return false;

  if (unit.aggregate_volume_only === true || unit.dimensions_are_aggregate === true) return true;

  return (
    unit.quantity === 1 &&
    String(unit.dimension_source || "").toLowerCase() === "estimated from cbm" &&
    totalCbm > 1.5
  );
}

function makeAggregatePreviewUnits(unit, container, margin, gap, maxBlocks = 80) {
  const totalCbm = asNumber(unit.total_cbm, null);
  if (!(totalCbm > 0)) return [];

  const rows = container.length_m >= 9 ? 8 : 4;
  const columns = 2;
  const layers = 4;

  const usableLength = Math.max(0.2, container.length_m - margin * 2);
  const usableWidth = Math.max(0.2, container.width_m - margin * 2);
  const usableHeight = Math.max(0.2, container.height_m - margin);

  const blockLength = Math.max(0.05, (usableLength - gap * (rows - 1)) / rows);
  const blockWidth = Math.max(0.05, (usableWidth - gap * (columns - 1)) / columns);
  const blockHeight = Math.max(0.05, (usableHeight - gap * (layers - 1)) / layers);
  const fullBlockCbm = blockLength * blockWidth * blockHeight;

  if (!(fullBlockCbm > 0)) return [];

  const blockCount = Math.min(maxBlocks, Math.ceil(totalCbm / fullBlockCbm));
  const blocks = [];
  let remainingCbm = totalCbm;

  for (let index = 0; index < blockCount && remainingCbm > 0.0001; index += 1) {
    const targetCbm = Math.min(fullBlockCbm, remainingCbm);
    const currentHeight = Math.min(
      blockHeight,
      Math.max(0.01, targetCbm / (blockLength * blockWidth))
    );
    const representedCbm = blockLength * blockWidth * currentHeight;

    blocks.push({
      ...unit,
      copy: index + 1,
      representative: index === 0,
      aggregate_preview: true,
      length_m: blockLength,
      width_m: blockWidth,
      height_m: currentHeight,
      dimension_source: "aggregate CBM preview cell",
    });

    remainingCbm = Math.max(0, remainingCbm - representedCbm);
  }

  return blocks;
}

function boxInsideContainer(box, container, tolerance = 0.0001) {
  const minX = box.x - box.length / 2;
  const maxX = box.x + box.length / 2;
  const minY = box.y - box.height / 2;
  const maxY = box.y + box.height / 2;
  const minZ = box.z - box.width / 2;
  const maxZ = box.z + box.width / 2;

  return (
    minX >= -container.length_m / 2 - tolerance &&
    maxX <= container.length_m / 2 + tolerance &&
    minY >= -tolerance &&
    maxY <= container.height_m + tolerance &&
    minZ >= -container.width_m / 2 - tolerance &&
    maxZ <= container.width_m / 2 + tolerance
  );
}

function packUnits(units, container) {
  const margin = 0.12;
  const gap = 0.025;
  const queue = [];
  const notes = [];
  const expandedAggregateItems = new Set();

  for (const unit of units) {
    if (shouldUseAggregatePreview(unit)) {
      const aggregateKey = String(unit.original_index ?? unit.name);
      if (expandedAggregateItems.has(aggregateKey)) continue;
      expandedAggregateItems.add(aggregateKey);

      const blocks = makeAggregatePreviewUnits(unit, container, margin, gap);
      queue.push(...blocks);
      notes.push(
        `${unit.name}: ${unit.total_cbm} CBM is represented by ${blocks.length} bounded volume cells in this advisory layout.`
      );
      continue;
    }

    queue.push(unit);
  }

  const placed = [];
  let omittedCount = 0;

  for (const unit of queue) {
    const box = tryPlaceUnit(
      unit,
      placed,
      container.length_m,
      container.width_m,
      container.height_m,
      margin,
      gap
    );

    if (box) {
      placed.push({
        ...box,
        aggregate_preview: Boolean(unit.aggregate_preview),
      });
    } else {
      // Never fabricate an overflow mesh outside the reference container.
      omittedCount += 1;
    }
  }

  const boundedBoxes = placed.filter((box) => boxInsideContainer(box, container));
  const rejectedOutOfBounds = placed.length - boundedBoxes.length;

  if (omittedCount) {
    notes.push(
      `${omittedCount} visual unit(s) were omitted because no valid non-overlapping position remained inside the reference container.`
    );
  }

  if (rejectedOutOfBounds) {
    notes.push(`Safety guard rejected ${rejectedOutOfBounds} out-of-bounds visual unit(s).`);
  }

  return {
    boxes: boundedBoxes,
    notes,
    omittedCount,
    rejectedOutOfBounds,
  };
}

function utilization(boxes, container) {
  const containerCbm = container.length_m * container.width_m * container.height_m;
  const active = boxes.filter((b) => !b.overflow);

  if (!active.length) {
    return {
      visualized_cbm: 0,
      container_cbm: Number(containerCbm.toFixed(2)),
      remaining_cbm: Number(containerCbm.toFixed(2)),
      utilization_percent: 0,
      remaining_percent: 100,
    };
  }

  const visualized = active.reduce((sum, b) => sum + b.length * b.width * b.height, 0);
  const pct = containerCbm ? (visualized / containerCbm) * 100 : 0;

  return {
    visualized_cbm: Number(visualized.toFixed(2)),
    container_cbm: Number(containerCbm.toFixed(2)),
    remaining_cbm: Number(Math.max(0, containerCbm - visualized).toFixed(2)),
    utilization_percent: Number(pct.toFixed(1)),
    remaining_percent: Number(Math.max(0, 100 - pct).toFixed(1)),
  };
}

function preferBackendDisplayMetrics(result, fallback = {}) {
  const visualizer = getVisualizer(result) || {};

  // The backend already knows the canonical shipment CBM.
  //
  // The browser 3D algorithm is only a visual placement preview.
  // Some boxes can be marked as overflow when the browser layout
  // cannot place them, but that must NOT reduce the shipment CBM
  // shown to the user.
  const backend =
    (
      visualizer.display_metrics &&
      typeof visualizer.display_metrics === "object"
        ? visualizer.display_metrics
        : null
    ) ||
    (
      visualizer.utilization &&
      typeof visualizer.utilization === "object"
        ? visualizer.utilization
        : null
    );

  if (!backend) {
    return fallback;
  }

  const loadedCbm = asNumber(
    backend.loaded_cbm ??
      backend.total_cbm ??
      visualizer?.container?.total_cbm ??
      result?.logistics_metrics?.total_cbm,
    null
  );

  const containerCbm = asNumber(
    backend.container_cbm ??
      visualizer?.container?.capacity_cbm ??
      fallback?.container_cbm,
    null
  );

  if (!(loadedCbm > 0) || !(containerCbm > 0)) {
    return fallback;
  }

  const utilizationPercent = asNumber(
    backend.utilization_percent,
    (loadedCbm / containerCbm) * 100
  );

  const remainingCbm = asNumber(
    backend.remaining_cbm,
    Math.max(0, containerCbm - loadedCbm)
  );

  return {
    ...fallback,

    // Keep the browser-computed number for debugging if needed.
    browser_visualized_cbm:
      fallback?.visualized_cbm ?? null,

    // Existing frontend uses visualized_cbm for the "Loaded"
    // number. Make that field canonical for display purposes.
    visualized_cbm:
      Number(loadedCbm.toFixed(2)),

    loaded_cbm:
      Number(loadedCbm.toFixed(2)),

    container_cbm:
      Number(containerCbm.toFixed(2)),

    remaining_cbm:
      Number(
        Math.max(0, remainingCbm).toFixed(2)
      ),

    utilization_percent:
      Number(
        utilizationPercent.toFixed(2)
      ),

    remaining_percent:
      Number(
        Math.max(
          0,
          100 - utilizationPercent
        ).toFixed(2)
      ),

    basis:
      backend.basis ||
      "shipment_total_cbm",
  };
}


function isPayloadBlocked(result) {
  const visualizer = getVisualizer(result) || {};
  const readiness = String(result?.logistics_metrics?.readiness_status || "").toLowerCase();
  const fitStatus = String(visualizer?.fit_check?.status || "").toLowerCase();

  return (
    readiness === "not_ready_payload_limit_exceeded" ||
    fitStatus === "payload_limit_exceeded"
  );
}

export function buildLayout(result) {
  const container = inferContainer(result);
  const cargoMix = normalizeCargoMix(result);
  const ordered = orderCargo(result, cargoMix);
  const expanded = expandUnits(ordered.cargo);
  const packed = packUnits(expanded.units, container);
  const browserUtil = utilization(packed.boxes, container);
  const displayUtil = preferBackendDisplayMetrics(result, browserUtil);
  const payloadBlocked = isPayloadBlocked(result);

  const shipmentWeightKg = asNumber(
    result?.logistics_metrics?.total_weight_kg ??
      result?.logistics_visualizer?.container?.total_weight_kg,
    null
  );

  const referencePayloadKg = asNumber(
    result?.payload_constraint?.reference_payload_kg ??
      result?.logistics_visualizer?.fit_check?.reference_payload_kg ??
      result?.logistics_visualizer?.container?.max_payload_kg,
    null
  );

  const payloadUsagePercent =
    shipmentWeightKg > 0 && referencePayloadKg > 0
      ? Number(((shipmentWeightKg / referencePayloadKg) * 100).toFixed(2))
      : null;

  const estimatedItems = ordered.cargo
    .filter(
      (item) =>
        !shouldUseAggregatePreview(item) &&
        String(item.dimension_source || "").startsWith("estimated")
    )
    .map((item) => item.name);

  const notes = [];

  if (payloadBlocked) {
    notes.push(
      "Reference-only volume layout: the blocks show how much container space the shipment occupies, but the shipment exceeds the single-container payload limit."
    );

    if (payloadUsagePercent !== null) {
      notes.push(
        `Volume use is ${displayUtil.utilization_percent ?? 0}%, while reference payload use is ${payloadUsagePercent}% (${shipmentWeightKg} kg against ${referencePayloadKg} kg). The shipment must be split because of weight, not lack of space.`
      );
    }
  }

  notes.push(
    ordered.usedBackendSequence
      ? "Loading order follows the logistics agent sequence."
      : "A safety-prioritized loading order was generated from the cargo characteristics."
  );

  if (estimatedItems.length) {
    notes.push(
      `Estimated packed sizes were used for ${estimatedItems.join(", ")}. Replace these with supplier carton dimensions before final booking.`
    );
  }

  notes.push(...expanded.notes, ...packed.notes);
  notes.push("This is an advisory loading view, not a certified stuffing plan.");
  notes.push(
    "Before booking, confirm carton dimensions, lashing, axle/load distribution, carrier limits, and dangerous-goods rules."
  );

  return {
    container,
    cargo_mix: ordered.cargo,
    boxes: packed.boxes,
    loading_sequence: ordered.sequence,
    loading_order_source: ordered.loading_order_source,
    usedBackendSequence: ordered.usedBackendSequence,
    utilization: displayUtil,
    payload_blocked: payloadBlocked,
    payload_usage_percent: payloadUsagePercent,
    reference_payload_kg: referencePayloadKg,
    shipment_weight_kg: shipmentWeightKg,
    layout_status: payloadBlocked
      ? "reference_only_payload_blocked"
      : packed.omittedCount > 0
        ? "partial_bounded_preview"
        : "bounded_preview",
    packing_summary: {
      visual_units: packed.boxes.length,
      omitted_units: packed.omittedCount,
      rejected_out_of_bounds: packed.rejectedOutOfBounds,
    },
    notes,
  };
}

function makeLabelSprite(text, cargoColor) {
  const canvas = document.createElement("canvas");
  canvas.width = 640;
  canvas.height = 150;

  const ctx = canvas.getContext("2d");
  const color = cargoColor || "#ffffff";

  function roundRect(x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + width, y, x + width, y + height, r);
    ctx.arcTo(x + width, y + height, x, y + height, r);
    ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + width, y, r);
    ctx.closePath();
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "rgba(8, 17, 31, 0.90)";
  roundRect(0, 0, canvas.width, canvas.height, 18);
  ctx.fill();

  ctx.fillStyle = color;
  roundRect(0, 0, 22, canvas.height, 12);
  ctx.fill();

  ctx.strokeStyle = color;
  ctx.lineWidth = 5;
  roundRect(2, 2, canvas.width - 4, canvas.height - 4, 18);
  ctx.stroke();

  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 46px system-ui";
  ctx.fillText(String(text).slice(0, 20), 42, 92);

  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;

  const material = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
    depthWrite: false,
  });

  const sprite = new THREE.Sprite(material);
  sprite.scale.set(1.45, 0.34, 1);
  sprite.renderOrder = 999;
  return sprite;
}

function addPointerLine(scene, start, end, color) {
  const geometry = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(start.x, start.y, start.z),
    new THREE.Vector3(end.x, end.y, end.z),
  ]);

  const material = new THREE.LineBasicMaterial({
    color: new THREE.Color(color || "#ffffff"),
    transparent: true,
    opacity: 0.95,
    depthTest: false,
    depthWrite: false,
  });

  const line = new THREE.Line(geometry, material);
  line.renderOrder = 998;
  scene.add(line);
}

function ThreeScene({ layout }) {
  const mountRef = useRef(null);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;

    mount.innerHTML = "";

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x07111f);

    const width = mount.clientWidth || 900;
    const height = 620;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(7.5, 4.5, 7.5);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height);
    mount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0.8, 0);
    controls.enableDamping = true;

    scene.add(new THREE.AmbientLight(0xffffff, 0.75));

    const directional = new THREE.DirectionalLight(0xffffff, 1.1);
    directional.position.set(3, 7, 5);
    scene.add(directional);

    const c = layout.container;
    const L = c.length_m || 5.9;
    const W = c.width_m || 2.35;
    const H = c.height_m || 2.39;

    const floor = new THREE.Mesh(
      new THREE.BoxGeometry(L, 0.035, W),
      new THREE.MeshStandardMaterial({ color: 0x16263d, roughness: 0.8 })
    );
    floor.position.set(0, -0.017, 0);
    scene.add(floor);

    const containerBox = new THREE.BoxGeometry(L, H, W);

    const shell = new THREE.Mesh(
      containerBox,
      new THREE.MeshStandardMaterial({
        color: 0x1d3557,
        transparent: true,
        opacity: 0.06,
        roughness: 0.7,
      })
    );
    shell.position.set(0, H / 2, 0);
    scene.add(shell);

    const wire = new THREE.LineSegments(
      new THREE.EdgesGeometry(containerBox),
      new THREE.LineBasicMaterial({ color: 0x7aa2ff, transparent: true, opacity: 0.9 })
    );
    wire.position.set(0, H / 2, 0);
    scene.add(wire);

    const grid = new THREE.GridHelper(Math.max(L, 7), Math.max(10, Math.round(L * 2)), 0x315070, 0x1c314f);
    grid.position.y = 0.002;
    scene.add(grid);

    const groupBounds = new Map();

    function updateBounds(box) {
      if (!groupBounds.has(box.name)) {
        groupBounds.set(box.name, {
          minX: Infinity,
          maxX: -Infinity,
          minY: Infinity,
          maxY: -Infinity,
          minZ: Infinity,
          maxZ: -Infinity,
          color: box.color || "#ffffff",
        });
      }

      const b = groupBounds.get(box.name);
      b.minX = Math.min(b.minX, box.x - box.length / 2);
      b.maxX = Math.max(b.maxX, box.x + box.length / 2);
      b.minY = Math.min(b.minY, box.y - box.height / 2);
      b.maxY = Math.max(b.maxY, box.y + box.height / 2);
      b.minZ = Math.min(b.minZ, box.z - box.width / 2);
      b.maxZ = Math.max(b.maxZ, box.z + box.width / 2);
    }

    for (const box of layout.boxes || []) {
      const geometry = new THREE.BoxGeometry(box.length, box.height, box.width);
      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(box.color || "#80ed99"),
        roughness: 0.55,
        metalness: 0.05,
        transparent: Boolean(box.overflow),
        opacity: box.overflow ? 0.42 : 0.92,
      });

      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(box.x, box.y, box.z);
      scene.add(mesh);

      const outline = new THREE.LineSegments(
        new THREE.EdgesGeometry(geometry),
        new THREE.LineBasicMaterial({ color: 0x06111f, transparent: true, opacity: 0.55 })
      );
      outline.position.copy(mesh.position);
      scene.add(outline);

      updateBounds(box);
    }

    const labelEntries = [...groupBounds.entries()]
      .sort(([nameA], [nameB]) =>
        String(nameA).localeCompare(String(nameB))
      );
    const occupiedLabels = [];

    labelEntries.forEach(([cargoName, bounds], index) => {
      const centerX = (bounds.minX + bounds.maxX) / 2;
      const centerZ = (bounds.minZ + bounds.maxZ) / 2;
      const labelX =
        centerX + ((index % 3) - 1) * 0.38;
      const labelZ =
        centerZ + (index % 2 === 0 ? -0.18 : 0.18);
      let labelY = bounds.maxY + 0.58;
      const color = bounds.color || "#ffffff";

      for (const existing of occupiedLabels) {
        const horizontalDistance = Math.hypot(
          labelX - existing.x,
          labelZ - existing.z
        );

        while (
          horizontalDistance < 0.95 &&
          Math.abs(labelY - existing.y) < 0.36
        ) {
          labelY += 0.42;
        }
      }

      occupiedLabels.push({
        x: labelX,
        y: labelY,
        z: labelZ,
      });

      const label = makeLabelSprite(cargoName, color);
      label.frustumCulled = false;
      label.position.set(labelX, labelY, labelZ);
      scene.add(label);

      addPointerLine(
        scene,
        { x: centerX, y: bounds.maxY + 0.03, z: centerZ },
        { x: labelX, y: labelY - 0.17, z: labelZ },
        color
      );
    });

    let frameId;
    const animate = () => {
      controls.update();
      renderer.render(scene, camera);
      frameId = requestAnimationFrame(animate);
    };
    animate();

    const onResize = () => {
      const nextWidth = mount.clientWidth || width;
      camera.aspect = nextWidth / height;
      camera.updateProjectionMatrix();
      renderer.setSize(nextWidth, height);
    };

    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener("resize", onResize);
      controls.dispose();
      renderer.dispose();
      mount.innerHTML = "";
    };
  }, [layout]);

  return <div ref={mountRef} className="container3d-scene" />;
}

export default function Container3DVisualizer({ result }) {
  const layout = useMemo(() => buildLayout(result), [result]);

  if (!hasContainer3DData(result)) return null;

  const util = layout.utilization || {};

  return (
    <div className="container3d-card">
      <div className="container3d-scene-wrap">
        <ThreeScene layout={layout} />
        <div className="container3d-hint">Drag to rotate · Scroll to zoom · Right-click drag to pan</div>
      </div>

      <details className="container3d-panel">
        <summary className="container3d-panel-summary">
          <span>3D loading details</span>
          <small>
            {util.utilization_percent ?? 0}% volume used - {util.remaining_percent ?? 100}% volume free - {layout.boxes.length} visual units
          </small>
        </summary>
        <div className="container3d-panel-content">
        <div className="container3d-title">3D Container Loading View</div>
        <div className="container3d-sub">Container: {layout.container.name}</div>
        <div className="container3d-sub">
          {layout.container.length_m.toFixed(2)}m L × {layout.container.width_m.toFixed(2)}m W × {layout.container.height_m.toFixed(2)}m H
        </div>

        <div className="container3d-section-title">Cargo legend</div>
        <div className="container3d-legend">
          {layout.cargo_mix.map((item) => (
            <div className="container3d-legend-row" key={item.name}>
              <span className="container3d-swatch" style={{ background: item.color }} />
              <div>
                <div><b>{item.name}</b> × {item.quantity}</div>
                <div className="container3d-muted">{(item.tags || []).join(", ") || "general cargo"} · {item.stackable ? "stackable" : "floor-loaded / non-stackable"}</div>
                <div className="container3d-muted">
                  {item.length_m.toFixed(2)}m × {item.width_m.toFixed(2)}m × {item.height_m.toFixed(2)}m · {item.dimension_source}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="container3d-section-title">Container space</div>
        <div className="container3d-space-card">
          <div className="container3d-space-head">
            <div>
              <div className="container3d-space-title">{util.utilization_percent ?? 0}% used</div>
              <div className="container3d-muted">Based on total shipment CBM from backend</div>
            </div>
            <div className="container3d-space-badge">{util.remaining_percent ?? 100}% free</div>
          </div>

          <div className="container3d-space-bar">
            <div className="container3d-space-fill" style={{ width: `${Math.min(100, Math.max(0, util.utilization_percent || 0))}%` }} />
          </div>

          <div className="container3d-metric-grid">
            <div className="container3d-metric"><span>Loaded</span><b>{util.visualized_cbm ?? 0} CBM</b></div>
            <div className="container3d-metric"><span>Remaining</span><b>{util.remaining_cbm ?? 0} CBM</b></div>
            <div className="container3d-metric"><span>Container</span><b>{util.container_cbm ?? 0} CBM</b></div>
            <div className="container3d-metric"><span>Visual units</span><b>{layout.boxes.length}</b></div>
          </div>
        </div>

        <div className="container3d-section-title">Loading order</div>
        <div className="container3d-order-list">
          {(layout.loading_sequence || []).map((name, idx) => (
            <div className="container3d-order-step" key={`${name}-${idx}`}>
              <span className="container3d-order-number">{idx + 1}</span>
              <span>{name}</span>
            </div>
          ))}
        </div>

        <div className="container3d-note">
          <div className="container3d-note-title">Loading interpretation</div>
          <div className="container3d-interpretation-list">
            {layout.notes.map((note, idx) => (
              <div className="container3d-interpretation-row" key={idx}>
                <span className="container3d-interpretation-dot" />
                <span>{note}</span>
              </div>
            ))}
          </div>
        </div>
        </div>
      </details>
    </div>
  );
}
