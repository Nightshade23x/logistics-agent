import assert from "node:assert/strict";
import { createServer } from "vite";

function bounds(box) {
  return {
    minX: box.x - box.length / 2,
    maxX: box.x + box.length / 2,
    minY: box.y - box.height / 2,
    maxY: box.y + box.height / 2,
    minZ: box.z - box.width / 2,
    maxZ: box.z + box.width / 2,
  };
}

function assertInside(layout, label) {
  const c = layout.container;
  const eps = 0.0005;

  for (const box of layout.boxes) {
    const b = bounds(box);
    assert.ok(b.minX >= -c.length_m / 2 - eps, `${label}: ${box.name} outside minX`);
    assert.ok(b.maxX <= c.length_m / 2 + eps, `${label}: ${box.name} outside maxX`);
    assert.ok(b.minY >= -eps, `${label}: ${box.name} below floor`);
    assert.ok(b.maxY <= c.height_m + eps, `${label}: ${box.name} above roof`);
    assert.ok(b.minZ >= -c.width_m / 2 - eps, `${label}: ${box.name} outside minZ`);
    assert.ok(b.maxZ <= c.width_m / 2 + eps, `${label}: ${box.name} outside maxZ`);
  }
}

function overlaps(first, second) {
  const a = bounds(first);
  const b = bounds(second);
  const eps = 0.0005;

  return !(
    a.maxX <= b.minX + eps ||
    a.minX >= b.maxX - eps ||
    a.maxY <= b.minY + eps ||
    a.minY >= b.maxY - eps ||
    a.maxZ <= b.minZ + eps ||
    a.minZ >= b.maxZ - eps
  );
}

function assertNoOverlap(layout, label) {
  for (let i = 0; i < layout.boxes.length; i += 1) {
    for (let j = i + 1; j < layout.boxes.length; j += 1) {
      assert.equal(
        overlaps(layout.boxes[i], layout.boxes[j]),
        false,
        `${label}: ${layout.boxes[i].name} overlaps ${layout.boxes[j].name}`
      );
    }
  }
}

function makeResult(cargoMix, { cbm, weight, utilization, fit = "fits_selected_container", readiness = "ready_for_standard_review" }) {
  return {
    logistics_metrics: {
      total_cbm: cbm,
      total_weight_kg: weight,
      recommended_container:
        fit === "payload_limit_exceeded"
          ? "Multiple containers or specialist heavy-cargo planning required"
          : "20ft Standard Container",
      readiness_status: readiness,
    },
    logistics_visualizer: {
      status: "available",
      container: {
        selected_container: "20ft Standard Container",
        length_m: 5.9,
        width_m: 2.35,
        height_m: 2.39,
        total_cbm: cbm,
        capacity_cbm: 33.2,
      },
      cargo_mix: cargoMix,
      fit_check: { status: fit },
      display_metrics: {
        loaded_cbm: cbm,
        container_cbm: 33.2,
        remaining_cbm: Math.max(0, 33.2 - cbm),
        utilization_percent: utilization,
      },
    },
  };
}

const vite = await createServer({
  root: process.cwd(),
  appType: "custom",
  logLevel: "error",
  server: { middlewareMode: true },
});

try {
  const module = await vite.ssrLoadModule("/src/components/Container3DVisualizer.jsx");
  const build = module.buildLayout;
  assert.equal(typeof build, "function");

  const prompt3 = makeResult(
    [{
      item_name: "glass jars",
      quantity: 8,
      dimensions_m: { length: 1.2, width: 1.0, height: 1.5 },
      total_cbm: 14.4,
      total_weight_kg: 1440,
      category_tags: ["fragile"],
    }],
    { cbm: 14.4, weight: 1440, utilization: 43.37 }
  );
  const prompt3Layout = build(prompt3);
  assert.equal(prompt3Layout.boxes.length, 8);
  assertInside(prompt3Layout, "Prompt 3");
  assertNoOverlap(prompt3Layout, "Prompt 3");
  assert.equal(prompt3Layout.utilization.loaded_cbm, 14.4);
  console.log("PASS - Prompt 3 bounded pallet layout");

  const n = makeResult(
    [
      {
        item_name: "ceramic tiles",
        quantity: 1,
        total_cbm: 10,
        unit_cbm: 10,
        total_weight_kg: 1200,
        aggregate_volume_only: true,
        dimensions_are_aggregate: true,
      },
      {
        item_name: "pillows",
        quantity: 1,
        total_cbm: 4,
        unit_cbm: 4,
        total_weight_kg: 350,
        aggregate_volume_only: true,
        dimensions_are_aggregate: true,
      },
    ],
    { cbm: 14, weight: 1550, utilization: 42.17 }
  );
  const nLayout = build(n);
  assert.ok(nLayout.boxes.length > 2);
  assertInside(nLayout, "N");
  assertNoOverlap(nLayout, "N");
  assert.equal(nLayout.packing_summary.rejected_out_of_bounds, 0);
  assert.equal(nLayout.packing_summary.omitted_units, 0);
  assert.equal(nLayout.utilization.loaded_cbm, 14);
  assert.deepEqual(nLayout.loading_sequence, ["ceramic tiles", "pillows"]);
  assert.ok(
    nLayout.notes.every((note) => !String(note).includes("invented carton"))
  );
  assert.ok(
    nLayout.notes.some((note) =>
      String(note).includes("bounded volume cells in this advisory layout")
    )
  );
  console.log("PASS - N aggregate layout bounded");

  const p = makeResult(
    [{
      item_name: "steel parts",
      quantity: 1,
      total_cbm: 20,
      unit_cbm: 20,
      total_weight_kg: 40000,
      aggregate_volume_only: true,
      dimensions_are_aggregate: true,
    }],
    {
      cbm: 20,
      weight: 40000,
      utilization: 60.24,
      fit: "payload_limit_exceeded",
      readiness: "not_ready_payload_limit_exceeded",
    }
  );
  // CONTAINER_LAYOUT_POLISH_TEST_V5
  p.payload_constraint = {
    applicable: true,
    status: "blocked",
    shipment_weight_kg: 40000,
    reference_payload_kg: 28200,
    payload_overage_kg: 11800,
  };
  const pLayout = build(p);
  assert.equal(pLayout.payload_blocked, true);
  assert.equal(pLayout.layout_status, "reference_only_payload_blocked");
  assert.ok(pLayout.boxes.length > 1);
  assertInside(pLayout, "P");
  assertNoOverlap(pLayout, "P");
  assert.equal(pLayout.packing_summary.rejected_out_of_bounds, 0);
  assert.equal(pLayout.packing_summary.omitted_units, 0);
  assert.equal(pLayout.utilization.loaded_cbm, 20);
  assert.equal(pLayout.payload_usage_percent, 141.84);
  assert.deepEqual(pLayout.loading_sequence, ["steel parts"]);
  assert.ok(
    pLayout.notes.some((note) =>
      String(note).includes("split because of weight, not lack of space")
    )
  );
  assert.ok(
    pLayout.notes.some((note) =>
      String(note).includes("safety-prioritized loading order")
    )
  );
  console.log("PASS - P steel reference layout bounded");

  const oversized = makeResult(
    [{
      item_name: "oversized machine",
      quantity: 1,
      dimensions_m: { length: 8, width: 3, height: 3 },
      total_cbm: 72,
      total_weight_kg: 9000,
      stackable: false,
    }],
    { cbm: 72, weight: 9000, utilization: 216.87 }
  );
  const oversizedLayout = build(oversized);
  assert.equal(oversizedLayout.boxes.length, 0);
  assert.equal(oversizedLayout.packing_summary.omitted_units, 1);
  assert.equal(oversizedLayout.packing_summary.rejected_out_of_bounds, 0);
  console.log("PASS - genuine oversize omitted instead of rendered outside");

  console.log("");
  console.log("ALL CONTAINER LAYOUT REGRESSION CHECKS PASSED");
} finally {
  await vite.close();
}
