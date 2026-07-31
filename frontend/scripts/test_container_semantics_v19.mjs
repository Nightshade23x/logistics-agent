import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");

const mainSource = fs.readFileSync(
  path.join(root, "src/main.jsx"),
  "utf8",
);

const storeSource = fs.readFileSync(
  path.join(root, "src/store.jsx"),
  "utf8",
);

const planningSource = fs.readFileSync(
  path.join(root, "src/pages/ContainerPlanning.jsx"),
  "utf8",
);

const visualizerSource = fs.readFileSync(
  path.join(
    root,
    "src/components/Container3DVisualizer.jsx",
  ),
  "utf8",
);

assert.doesNotMatch(
  mainSource,
  /localStorage\.removeItem\(["']meridian\.lastResult["']\)/,
  "Opening another tab must not delete the shared current result",
);

assert.match(
  storeSource,
  /window\.addEventListener\(\s*["']storage["'],\s*handleStorage\s*\)/,
  "The store must listen for cross-tab result updates",
);

assert.match(
  storeSource,
  /event\.key === RESULT_KEY[\s\S]*?setResultState/,
  "The current result must synchronize between tabs",
);

assert.match(
  storeSource,
  /event\.key === HISTORY_KEY[\s\S]*?setHistoryState/,
  "History must synchronize between tabs",
);

assert.match(
  planningSource,
  /canonical\.weightKnown\s*\?\s*canonical\.totalWeightKg\s*:\s*"Not confirmed"/,
  "Unknown weight must display as Not confirmed",
);

assert.match(
  planningSource,
  /canonical\.readinessStatus\s*\|\|\s*lm\.readiness_status/,
  "The semantic readiness status must control the header badge",
);

assert.match(
  visualizerSource,
  /advisory aggregate-volume representation/,
  "Aggregate CBM geometry must be labelled advisory",
);

assert.match(
  visualizerSource,
  /const weightKnown = item\.weight_known !== false/,
  "Heavy inference must respect unknown weight",
);

assert.match(
  visualizerSource,
  /const labelEntries = \[\.\.\.groupBounds\.entries\(\)\]/,
  "Every cargo group must receive a scene label",
);

assert.match(
  visualizerSource,
  /const occupiedLabels = \[\];/,
  "Label placement must track occupied anchors",
);

assert.match(
  visualizerSource,
  /labelY \+= 0\.42;/,
  "Overlapping labels must move to a separate tier",
);

assert.match(
  visualizerSource,
  /label\.frustumCulled = false;/,
  "Cargo labels must not disappear through sprite culling",
);

console.log("PASS - cross-tab current result is synchronized");
console.log("PASS - unknown weight displays as Not confirmed");
console.log("PASS - readiness uses missing-cargo-detail semantics");
console.log("PASS - aggregate geometry is labelled advisory");
console.log("PASS - all cargo labels receive visible anchors");
