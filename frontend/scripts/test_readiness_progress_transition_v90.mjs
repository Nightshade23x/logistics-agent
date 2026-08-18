import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const progressPath = path.join(root, "src", "components", "ShipmentProgress.jsx");
const needInfoPath = path.join(root, "src", "components", "NeedMoreInfoCard.jsx");

const progress = fs.readFileSync(progressPath, "utf8");
const needInfo = fs.readFileSync(needInfoPath, "utf8");

function requireCheck(condition, message) {
  if (!condition) {
    console.error(`FAIL - ${message}`);
    process.exit(1);
  }
  console.log(`PASS - ${message}`);
}

requireCheck(
  progress.includes("READINESS_PROGRESS_TRANSITION_V90"),
  "V90 readiness progress logic is installed"
);

const readyToBookBranch = progress.indexOf("if (readyToBook) return 4;");
const activeQuestionBranch = progress.indexOf("if (activeQuestions.length) return 2;");
const readyFirstPassBranch = progress.indexOf("if (readyForFirstPass) return 3;");
const genericMissingBranch = progress.indexOf(
  'if (status.includes("missing") || status.includes("blocked")) return 2;'
);

requireCheck(
  readyToBookBranch >= 0 &&
    activeQuestionBranch > readyToBookBranch &&
    readyFirstPassBranch > activeQuestionBranch &&
    genericMissingBranch > readyFirstPassBranch,
  "progress order is Ready to book -> clarification -> Ready for review -> fallback missing"
);

requireCheck(
  progress.includes("booking.ready_for_first_pass === true"),
  "booking readiness first-pass flag is honored"
);

requireCheck(
  progress.includes("remain before Ready for review") &&
    progress.includes("remain before Ready to book"),
  "progress UI explains both readiness gates"
);

requireCheck(
  needInfo.includes("MISSING_INFO_SUPERSEDE_INCOTERM_V90"),
  "V90 corrected-Incoterm merge logic is installed"
);

requireCheck(
  needInfo.includes("function removePriorStandaloneIncotermAnswers") &&
    needInfo.includes("function buildUpdatedRequest"),
  "missing-info updates use the safe merge helpers"
);

requireCheck(
  needInfo.includes(".replace(/^\\s*Use\\s+[A-Za-z]{2,12}\\s+incoterm"),
  "prior standalone Use X incoterm lines are superseded"
);

requireCheck(
  needInfo.includes("baseText = removePriorStandaloneIncotermAnswers(baseText);"),
  "Incoterm correction removes the earlier standalone Incoterm answer"
);

requireCheck(
  !needInfo.includes('const combinedText = `${originalText}\\n\\n${allLines.join("\\n")}`;'),
  "old append-only request merge was removed"
);

requireCheck(
  needInfo.includes(
    "const combinedText = buildUpdatedRequest(originalText, questions, answers, extraLine);"
  ),
  "rerun now uses the superseding request builder"
);

console.log("All V90 readiness transition frontend source tests passed.");
