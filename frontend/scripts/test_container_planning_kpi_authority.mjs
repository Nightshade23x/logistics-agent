import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const sourcePath = path.resolve(
  here,
  "../src/pages/ContainerPlanning.jsx",
);

const source = fs.readFileSync(sourcePath, "utf8");

assert.match(
  source,
  /const pattern =\s*\/\(\[0-9\]\[0-9,\]\*\(\?:\\\.\[0-9\]\+\)\?\)\\s\*CBM[\s\S]*?\\s\*kg\\b\/gi;/,
  "Frontend multi-item parser must use complete clause matching",
);

assert.doesNotMatch(
  source,
  /directMultiItemTotals[\s\S]*?\(\?=/,
  "Frontend multi-item parser must not use the old lookahead",
);

assert.match(
  source,
  /const cbm = Number\(match\[1\]\.replaceAll\(",", ""\)\);/,
  "CBM parser must support comma-formatted numbers",
);

assert.match(
  source,
  /const weightKg = Number\(match\[3\]\.replaceAll\(",", ""\)\);/,
  "Weight parser must support comma-formatted numbers",
);

assert.match(
  source,
  /<Kpi label="Total CBM" value=\{canonical\.totalCbm\}/,
  "Total CBM KPI must use canonical totals",
);

assert.match(
  source,
  /<Kpi label="Total Weight" value=\{canonical\.totalWeightKg\}/,
  "Total Weight KPI must use canonical totals",
);

assert.doesNotMatch(
  source,
  /<Kpi label="Total CBM" value=\{c\?\.total_cbm/,
  "Stale container CBM must not override canonical totals",
);

assert.doesNotMatch(
  source,
  /<Kpi label="Total Weight" value=\{c\?\.total_weight_kg/,
  "Stale container weight must not override canonical totals",
);

const prompt =
  "Ship 2 CBM pumps weighing 500 kg, " +
  "3 CBM valves weighing 300 kg and " +
  "1 CBM seals weighing 50 kg from India to USA.";

const pattern =
  /([0-9][0-9,]*(?:\.[0-9]+)?)\s*CBM\s+(?:of\s+)?(.*?)\s+weigh(?:ing|s)?\s+([0-9][0-9,]*(?:\.[0-9]+)?)\s*kg\b/gi;

const items = [...prompt.matchAll(pattern)].map((match) => ({
  cbm: Number(match[1].replaceAll(",", "")),
  name: match[2].trim(),
  weightKg: Number(match[3].replaceAll(",", "")),
}));

assert.deepEqual(
  items.map((item) => item.name),
  ["pumps", "valves", "seals"],
);

assert.equal(
  items.reduce((sum, item) => sum + item.cbm, 0),
  6,
);

assert.equal(
  items.reduce((sum, item) => sum + item.weightKg, 0),
  850,
);

console.log("PASS - frontend parser finds pumps, valves, and seals separately");
console.log("PASS - canonical totals are 6 CBM and 850 kg");
console.log("PASS - KPI cards use canonical totals");
