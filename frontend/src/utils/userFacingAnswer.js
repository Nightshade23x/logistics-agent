function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeAnswerValue(value) {
  if (!value) {
    return "";
  }

  if (typeof value === "string") {
    return value.trim();
  }

  if (typeof value === "object") {
    var parts = [];
    var keys = ["headline", "answer_text", "summary", "text", "message"];

    for (var i = 0; i < keys.length; i += 1) {
      var key = keys[i];

      if (isNonEmptyString(value[key])) {
        parts.push(value[key].trim());
      }
    }

    return parts.filter(Boolean).join("\n\n").trim();
  }

  return "";
}

function looksLikeUsefulAnswer(text) {
  if (!isNonEmptyString(text)) {
    return false;
  }

  var lower = text.toLowerCase().trim();

  if (
    lower === "needs_more_information" ||
    lower === "review_required" ||
    lower === "blocked" ||
    lower === "clear"
  ) {
    return false;
  }

  if (lower.indexOf("decision:") === 0 && lower.length < 120) {
    return false;
  }

  return true;
}

function stripBulletPrefix(line) {
  var text = String(line || "").trim();

  while (
    text.indexOf("- ") === 0 ||
    text.indexOf("* ") === 0 ||
    text.indexOf("• ") === 0 ||
    text.indexOf("—") === 0
  ) {
    if (text.indexOf("—") === 0) {
      text = text.slice(1).trim();
    } else {
      text = text.slice(2).trim();
    }
  }

  return text;
}

export function pickUserFacingAnswer(result) {
  if (!result) {
    return "";
  }

  var answerSection = null;

  if (Array.isArray(result.ui_sections)) {
    for (var i = 0; i < result.ui_sections.length; i += 1) {
      var section = result.ui_sections[i];

      if (section && section.section_id === "answer") {
        answerSection = section;
        break;
      }
    }
  }

  var candidates = [
    result.display_answer,
    result.frontend_answer,
    result.user_facing_answer,
    result.answer,
    result.response_text,
    result.final_answer,
    result.report,
    answerSection ? answerSection.summary : null,
    result.summary,
    result.short_answer,
    result.final_answer && result.final_answer.answer_text,
    result.final_answer && result.final_answer.headline,
    result.executive_summary && result.executive_summary.headline
  ];

  for (var j = 0; j < candidates.length; j += 1) {
    var text = normalizeAnswerValue(candidates[j]);

    if (looksLikeUsefulAnswer(text)) {
      return text;
    }
  }

  return "";
}

export function getAnswerStatus(result) {
  return (
    (result && result.final_answer && result.final_answer.status) ||
    (result && result.decision) ||
    (result && result.status) ||
    (result && result.executive_summary && result.executive_summary.status) ||
    "review_required"
  );
}

export function getAgentSummaryFallback(result) {
  var summaries = Array.isArray(result && result.agent_summaries) ? result.agent_summaries : [];
  var lines = [];

  for (var i = 0; i < summaries.length; i += 1) {
    var summary = summaries[i];

    if (summary && summary.summary) {
      lines.push((summary.agent_name || "agent") + ": " + summary.summary);
    }
  }

  return lines.join("\n\n");
}

function cleanAction(action) {
  if (!isNonEmptyString(action)) {
    return null;
  }

  var text = action.trim();
  var lower = text.toLowerCase();

  var genericBad = [
    "answer the clarification questions shown in the payload",
    "answer missing-information questions before booking",
    "review warnings before booking",
    "shopping review requires checking",
    "logistics review requires checking",
    "what is the origin country or supplier country?"
  ];

  for (var i = 0; i < genericBad.length; i += 1) {
    if (lower.indexOf(genericBad[i]) >= 0) {
      return null;
    }
  }

  return text;
}

export function getAnswerActions(result) {
  var clarificationQuestions = Array.isArray(result && result.clarification_questions)
    ? result.clarification_questions
    : [];

  var actionPlanQuestions =
    result && result.action_plan && Array.isArray(result.action_plan.user_questions)
      ? result.action_plan.user_questions
      : [];

  var finalAnswerActions =
    result && result.final_answer && Array.isArray(result.final_answer.next_actions)
      ? result.final_answer.next_actions
      : [];

  var executiveActions =
    result && result.executive_summary && Array.isArray(result.executive_summary.top_next_actions)
      ? result.executive_summary.top_next_actions
      : [];

  var rawActions = clarificationQuestions.length
    ? clarificationQuestions
    : actionPlanQuestions.concat(finalAnswerActions).concat(executiveActions);

  var seen = {};
  var unique = [];

  for (var i = 0; i < rawActions.length; i += 1) {
    var action = cleanAction(rawActions[i]);

    if (!action) {
      continue;
    }

    var key = action.toLowerCase();

    if (seen[key]) {
      continue;
    }

    seen[key] = true;
    unique.push(action);
  }

  return unique;
}

export function parseAnswerSections(answerText) {
  if (!isNonEmptyString(answerText)) {
    return [];
  }

  var rawLines = answerText.replace(/\r/g, "").split("\n");
  var lines = [];

  for (var i = 0; i < rawLines.length; i += 1) {
    var line = String(rawLines[i] || "").trim();

    if (line) {
      lines.push(line);
    }
  }

  var sections = [];
  var current = {
    title: "Overview",
    body: [],
    bullets: []
  };

  function pushCurrent() {
    if (current.body.length || current.bullets.length) {
      sections.push(current);
    }
  }

  for (var j = 0; j < lines.length; j += 1) {
    var currentLine = lines[j];
    var firstChar = currentLine.charAt(0);
    var isBullet =
      firstChar === "-" ||
      firstChar === "*" ||
      firstChar === "•" ||
      firstChar === "—";

    var isHeading =
      !isBullet &&
      currentLine.charAt(currentLine.length - 1) === ":" &&
      currentLine.length <= 90;

    if (isHeading) {
      pushCurrent();
      current = {
        title: currentLine.slice(0, -1),
        body: [],
        bullets: []
      };
      continue;
    }

    if (isBullet) {
      current.bullets.push(stripBulletPrefix(currentLine));
    } else {
      current.body.push(currentLine);
    }
  }

  pushCurrent();

  return sections;
}

export function buildNextStepFlow(result, actions) {
  var steps = [];
  var safeActions = Array.isArray(actions) ? actions : [];
  var realClarificationQuestions =
    result && Array.isArray(result.clarification_questions)
      ? result.clarification_questions
      : [];

  var realActionQuestions =
    result && result.action_plan && Array.isArray(result.action_plan.user_questions)
      ? result.action_plan.user_questions
      : [];

  var hasQuestions =
    realClarificationQuestions.length > 0 ||
    realActionQuestions.length > 0;
  var hasSuppliers =
    Array.isArray(result && result.supplier_options) ||
    Array.isArray(result && result.shortlisted_suppliers) ||
    Boolean(result && result.procurement_advice && result.procurement_advice.supplier_options_count > 0);

  var hasLogistics =
    Boolean(result && result.logistics_metrics && result.logistics_metrics.total_cbm) ||
    Boolean(result && result.logistics_metrics && result.logistics_metrics.total_weight_kg) ||
    Boolean(result && result.logistics_visualizer && result.logistics_visualizer.status === "available");

  var hasDocs =
    Boolean(result && result.document_requirements_advice) ||
    Boolean(result && result.trade_compliance_readiness) ||
    Boolean(result && result.document_quality_review && result.document_quality_review.applicable);

  var hasCosts =
    Boolean(result && result.landed_cost_advice) ||
    Boolean(result && result.finance_agent) ||
    Boolean(result && result.agents_called && result.agents_called.indexOf("finance_agent") >= 0);

  if (hasQuestions) {
    steps.push({
      label: "1",
      title: "Fill missing info",
      tab: "Dashboard",
      detail: "Use the form below the answer and submit all missing details together.",
      status: "now"
    });
  }

  if (hasSuppliers) {
    steps.push({
      label: String(steps.length + 1),
      title: "Review suppliers",
      tab: "Procurement",
      detail: "Compare shortlisted suppliers, price, lead time, payment terms, packaging, and reliability.",
      status: hasQuestions ? "next" : "now"
    });
  }

  if (hasLogistics) {
    steps.push({
      label: String(steps.length + 1),
      title: "Check shipment plan",
      tab: "Shipments",
      detail: "Review CBM, weight, recommended container, load type, and risk notes.",
      status: "next"
    });

    if (result && result.logistics_visualizer && result.logistics_visualizer.status === "available") {
      steps.push({
        label: String(steps.length + 1),
        title: "View loading layout",
        tab: "Container Planning",
        detail: "Check the visual container plan, cargo zones, and loading sequence.",
        status: "next"
      });
    }
  }

  if (hasDocs) {
    steps.push({
      label: String(steps.length + 1),
      title: "Confirm documents",
      tab: "Compliance & Docs",
      detail: "Check invoices, packing list, bill of lading, certificates, and compliance gaps.",
      status: "next"
    });
  }

  if (hasCosts) {
    steps.push({
      label: String(steps.length + 1),
      title:
        result &&
        result.landed_cost_advice &&
        (
          result.landed_cost_advice.status === "blocked" ||
          result.landed_cost_advice.status === "needs_more_information"
        )
          ? "Complete cost inputs"
          : "Review cost result",
      tab: "Reports",
      detail:
        result &&
        result.landed_cost_advice &&
        (
          result.landed_cost_advice.status === "blocked" ||
          result.landed_cost_advice.status === "needs_more_information"
        )
          ? "Add the missing commercial inputs before final landed cost, duty, tax, and booking review."
          : "Validate landed cost, insurance, duty, taxes, and final booking readiness.",
      status: "next"
    });
  }

  if (!steps.length) {
    steps.push({
      label: "1",
      title: "Review result",
      tab: "Reports",
      detail: "Open the full report for the detailed breakdown and next actions.",
      status: "now"
    });
  }

  return steps;
}
