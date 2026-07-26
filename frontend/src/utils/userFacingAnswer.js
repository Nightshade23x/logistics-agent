function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeAnswerValue(value) {
  if (!value) return "";

  if (typeof value === "string") {
    return value.trim();
  }

  if (typeof value === "object") {
    const parts = [];

    if (isNonEmptyString(value.headline)) {
      parts.push(value.headline.trim());
    }

    if (isNonEmptyString(value.answer_text)) {
      parts.push(value.answer_text.trim());
    }

    if (isNonEmptyString(value.summary)) {
      parts.push(value.summary.trim());
    }

    if (isNonEmptyString(value.text)) {
      parts.push(value.text.trim());
    }

    if (isNonEmptyString(value.message)) {
      parts.push(value.message.trim());
    }

    return parts.filter(Boolean).join("\n\n").trim();
  }

  return "";
}

function looksLikeUsefulAnswer(text) {
  if (!isNonEmptyString(text)) return false;

  const lower = text.toLowerCase();

  const weakOnly =
    lower.startsWith("decision:") ||
    lower.startsWith("status:") ||
    lower === "needs_more_information" ||
    lower === "review_required" ||
    lower === "blocked";

  return !weakOnly;
}

export function pickUserFacingAnswer(result) {
  if (!result) return "";

  const candidates = [
    result.display_answer,
    result.frontend_answer,
    result.user_facing_answer,
    result.answer,
    result.response_text,
    result.final_answer,
    result.report,
    result.summary,
    result.short_answer,
    result?.ui_sections?.find?.((section) => section?.section_id === "answer")?.summary,
    result?.ui_sections?.[0]?.summary,
    result?.final_answer?.answer_text,
    result?.final_answer?.headline,
    result?.executive_summary?.headline,
  ];

  for (const candidate of candidates) {
    const text = normalizeAnswerValue(candidate);

    if (looksLikeUsefulAnswer(text)) {
      return text;
    }
  }

  return "";
}

export function getAnswerStatus(result) {
  return (
    result?.final_answer?.status ||
    result?.decision ||
    result?.status ||
    result?.executive_summary?.status ||
    "review_required"
  );
}

export function getAgentSummaryFallback(result) {
  const summaries = Array.isArray(result?.agent_summaries) ? result.agent_summaries : [];

  return summaries
    .filter((summary) => summary?.summary)
    .map((summary) => `${summary.agent_name || "agent"}: ${summary.summary}`)
    .join("\n\n");
}

export function getAnswerActions(result) {
  const actionPlanQuestions = Array.isArray(result?.action_plan?.user_questions)
    ? result.action_plan.user_questions
    : [];

  const clarificationQuestions = Array.isArray(result?.clarification_questions)
    ? result.clarification_questions
    : [];

  const finalAnswerActions = Array.isArray(result?.final_answer?.next_actions)
    ? result.final_answer.next_actions
    : [];

  const executiveActions = Array.isArray(result?.executive_summary?.top_next_actions)
    ? result.executive_summary.top_next_actions
    : [];

  const actions = [
    ...clarificationQuestions,
    ...actionPlanQuestions,
    ...finalAnswerActions,
    ...executiveActions,
  ];

  const seen = new Set();
  const unique = [];

  for (const action of actions) {
    if (!isNonEmptyString(action)) continue;

    const key = action.trim().toLowerCase();

    if (seen.has(key)) continue;

    seen.add(key);
    unique.push(action.trim());
  }

  return unique;
}
