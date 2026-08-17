import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const wizardPath = path.join(root, "src", "components", "GuidedShipmentWizard.jsx");
const dashboardPath = path.join(root, "src", "pages", "Dashboard.jsx");

const wizard = fs.readFileSync(wizardPath, "utf8");
const dashboard = fs.readFileSync(dashboardPath, "utf8");

function requireCheck(condition, message) {
  if (!condition) {
    console.error(`FAIL - ${message}`);
    process.exit(1);
  }
  console.log(`PASS - ${message}`);
}

requireCheck(
  wizard.includes("MENTOR WORKFLOW UX V89"),
  "V89 guided-workflow marker is installed"
);

const dimensionUnit = wizard.indexOf('htmlFor="wizard-dimensionUnit"');
const length = wizard.indexOf('htmlFor="wizard-length"');
const width = wizard.indexOf('htmlFor="wizard-width"');
const height = wizard.indexOf('htmlFor="wizard-height"');

requireCheck(
  dimensionUnit >= 0 && dimensionUnit < length && dimensionUnit < width && dimensionUnit < height,
  "Dimension unit appears before Length, Width and Height"
);

const weightRowStart = wizard.indexOf('className="wizard-grid two wizard-weight-row"');
const weightUnit = wizard.indexOf('htmlFor="wizard-weightUnit"', weightRowStart);
const weightPerPackage = wizard.indexOf('htmlFor="wizard-weightPerPackage"', weightRowStart);

requireCheck(
  weightRowStart >= 0 && weightUnit > weightRowStart && weightPerPackage > weightUnit,
  "Weight unit appears before Weight of one package"
);

requireCheck(
  wizard.includes("export const GUIDED_GOAL_OPTIONS") &&
  wizard.includes("buildGuidedShipmentRequestForGoal") &&
  wizard.includes('sessionStorage.setItem(SESSION_KEY, JSON.stringify(draft))'),
  "guided draft can be rebuilt for another goal while preserving shipment details"
);

requireCheck(
  dashboard.includes("MENTOR WORKFLOW QUICK GOALS V89") &&
  dashboard.includes("GUIDED_GOAL_OPTIONS") &&
  dashboard.includes("runGuidedGoal") &&
  dashboard.includes(".filter((option) => option.value !== getGuidedShipmentGoal())"),
  "Dashboard exposes the other guided goals after a completed result"
);

const clearAllIndex = dashboard.indexOf("Clear all");
const quickGoalsIndex = dashboard.indexOf("GUIDED_GOAL_OPTIONS", clearAllIndex);

requireCheck(
  clearAllIndex >= 0 && quickGoalsIndex > clearAllIndex,
  "quick goal buttons are rendered after Clear all in the action row"
);

requireCheck(
  dashboard.includes("clearCurrent();") &&
  dashboard.includes("clearAll();") &&
  dashboard.includes("resetDashboardDraft();"),
  "existing Clear current / Clear all reset behavior remains present"
);

console.log("All V89 mentor workflow frontend tests passed.");
