import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const progress = fs.readFileSync(
  path.join(root, "src", "components", "ShipmentProgress.jsx"),
  "utf8"
);
const overview = fs.readFileSync(
  path.join(root, "src", "components", "SimpleResultOverview.jsx"),
  "utf8"
);

function check(condition, message) {
  if (!condition) {
    console.error(`FAIL - ${message}`);
    process.exit(1);
  }
  console.log(`PASS - ${message}`);
}

check(
  progress.includes("READY_TO_BOOK_COUNT_V91"),
  "V91 progress count logic is installed"
);

check(
  progress.includes("booking.booking_requirements"),
  "progress uses explicit booking requirements"
);

check(
  !progress.includes("...asList(booking.review_items),"),
  "generic review items are no longer counted as booking requirements"
);

check(
  progress.includes("required item") &&
    progress.includes("remain before Ready to book"),
  "progress explains exact Ready-to-book gate"
);

check(
  overview.includes("SIMPLE_BOOKING_REQUIREMENTS_V91"),
  "simple overview uses booking-critical requirements"
);

check(
  overview.includes("No booking-critical requirements remain."),
  "simple result clearly identifies a cleared booking gate"
);

console.log("All V91 ready-to-book frontend source tests passed.");
