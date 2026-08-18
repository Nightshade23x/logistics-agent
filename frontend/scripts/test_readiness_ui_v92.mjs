import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const progress = fs.readFileSync(path.join(root, "src", "components", "ShipmentProgress.jsx"), "utf8");
const overview = fs.readFileSync(path.join(root, "src", "components", "SimpleResultOverview.jsx"), "utf8");
const dashboard = fs.readFileSync(path.join(root, "src", "pages", "Dashboard.jsx"), "utf8");

function check(condition, message) {
  if (!condition) {
    console.error(`FAIL - ${message}`);
    process.exit(1);
  }
  console.log(`PASS - ${message}`);
}

check(progress.includes("HARD_BLOCKER_PROGRESS_V92"), "V92 hard-blocker progress authority is installed");

const readyToBook = progress.indexOf("if (readyToBook) return 4;");
const hard = progress.indexOf("if (hasHardBlocker) return 2;");
const review = progress.indexOf("if (readyForFirstPass) return 3;");
check(
  readyToBook >= 0 && hard > readyToBook && review > hard,
  "hard blockers are evaluated before Ready for review"
);

check(
  progress.includes("must be resolved before Ready for review"),
  "progress explains why a critical shipment cannot advance"
);

check(
  overview.includes("BOOKING_STATUS_MEANING_V92"),
  "simple-result wording now uses booking readiness rather than stale global status"
);

check(
  dashboard.includes("FREE_TEXT_QUICK_GOALS_V92") &&
    dashboard.includes('simpleInputMode === "guided" || simpleInputMode === "free"'),
  "quick-goal buttons appear for Describe it myself as well as guided mode"
);

check(
  dashboard.includes("runReusableGoal(option.value)"),
  "quick-goal buttons reuse the current shipment in either mode"
);

console.log("All V92 readiness UI source tests passed.");
