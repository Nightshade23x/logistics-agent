import assert from "node:assert/strict";
import { createServer } from "vite";

const vite = await createServer({
  root: process.cwd(),
  appType: "custom",
  logLevel: "error",
  server: { middlewareMode: true },
});

try {
  const module = await vite.ssrLoadModule(
    "/src/pages/ContainerPlanning.jsx"
  );

  const canonical = module.getContainerPlanningMetrics;
  const direct = module.directMultiItemTotals;

  assert.equal(typeof canonical, "function");
  assert.equal(typeof direct, "function");

  const prompt =
    "Ship 10 CBM ceramic tiles weighing 1200 kg and " +
    "4 CBM pillows weighing 350 kg from India to USA.";

  const explicit = direct({
    request_metadata: { input_source: prompt },
  });

  assert.deepEqual(explicit, {
    totalCbm: 14,
    totalWeightKg: 1550,
  });

  // Exact browser regression: item rows contain a stale 20,000 kg
  // tile value, but the explicit prompt says 1,200 kg + 350 kg.
  const n = canonical({
    request_metadata: { input_source: prompt },
    logistics_metrics: {
      total_cbm: 14,
      total_weight_kg: 20350,
    },
    handoff_payload: {
      total_cbm: 14,
      total_weight_kg: 1550,
    },
    logistics_quality_review: {
      total_cbm: 14,
      total_weight_kg: 1550,
    },
    logistics_visualizer: {
      display_metrics: {
        loaded_cbm: 14,
        utilization_percent: 42.17,
      },
      container: {
        total_cbm: 14,
        total_weight_kg: 1550,
        capacity_cbm: 33.2,
      },
      cargo_mix: [
        {
          item_name: "ceramic tiles",
          total_cbm: 10,
          total_weight_kg: 20000,
        },
        {
          item_name: "pillows",
          total_cbm: 4,
          total_weight_kg: 350,
        },
      ],
    },
  });

  assert.equal(n.totalCbm, 14);
  assert.equal(n.totalWeightKg, 1550);
  assert.equal(n.utilizationPercent, 42.17);
  console.log("PASS - explicit multi-item prompt prevents stale 20350 kg KPI");

  // When prompt text is unavailable, shipment/container totals still
  // outrank stale item-level estimates.
  const noPrompt = canonical({
    logistics_metrics: {
      total_cbm: 14,
      total_weight_kg: 20350,
    },
    logistics_visualizer: {
      display_metrics: {
        loaded_cbm: 14,
        utilization_percent: 42.17,
      },
      container: {
        total_cbm: 14,
        total_weight_kg: 1550,
        capacity_cbm: 33.2,
      },
      cargo_mix: [
        { total_cbm: 10, total_weight_kg: 20000 },
        { total_cbm: 4, total_weight_kg: 350 },
      ],
    },
  });

  assert.equal(noPrompt.totalWeightKg, 1550);
  console.log("PASS - authoritative container weight outranks stale cargo rows");

  const oversized = canonical({
    logistics_metrics: {
      total_cbm: 72,
      total_weight_kg: 9000,
    },
    logistics_visualizer: {
      display_metrics: {
        loaded_cbm: 72,
        utilization_percent: 216.87,
      },
      container: {
        total_cbm: 72,
        total_weight_kg: 9000,
        capacity_cbm: 33.2,
      },
      cargo_mix: [
        {
          item_name: "industrial machine",
          total_cbm: 72,
          total_weight_kg: 9000,
        },
      ],
    },
  });

  assert.equal(oversized.totalWeightKg, 9000);
  console.log("PASS - oversized cargo weight remains 9000 kg");

  console.log("ALL CONTAINER PLANNING WEIGHT CHECKS PASSED");
} finally {
  await vite.close();
}
