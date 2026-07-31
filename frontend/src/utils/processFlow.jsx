// DYNAMIC_PROCESS_FLOW_V62
// Structured payload fields are authoritative. Final-answer prose is never parsed.

function object(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function list(value) {
  if (!value) return [];
  return Array.isArray(value) ? value.filter(Boolean) : [value];
}

function cleanStatus(value, fallback = "review") {
  return String(value || fallback).trim().toLowerCase().replace(/\s+/g, "_");
}

function tone(value) {
  const status = cleanStatus(value);
  if (/blocked|critical|not_ready|needs_more/.test(status)) return "blocked";
  if (/available|ready|complete|calculated|fits/.test(status)) return "ready";
  if (/review|indicative|pending|unknown|not_confirmed/.test(status)) return "review";
  return "neutral";
}

function cargoFlags(result) {
  const visualizer = object(result.logistics_visualizer);
  const cargo = list(visualizer.cargo_mix);
  const text = cargo.map((item) => {
    const row = object(item);
    return [row.item_name, ...list(row.category_tags), ...list(row.tags)].join(" ");
  }).join(" ").toLowerCase();
  const radioactive = /\bradioactive|isotope|class\s*7\b/.test(text);
  const battery = /\blithium|battery|batteries|class\s*9\b/.test(text);
  const hazardous = cargo.some((item) => object(item).hazardous === true) || radioactive || battery;
  return { hazardous, radioactive, battery };
}

function fallbackNodes(steps) {
  return list(steps).map((step, index) => {
    const title = String(step?.title || `Step ${index + 1}`);
    const lower = title.toLowerCase();
    return {
      id: `fallback-${index}`,
      label: title,
      kind: lower.includes("document") ? "document" : lower.includes("confirm") ? "decision" : "process",
      status: cleanStatus(step?.status),
      tone: tone(step?.status),
      detail: String(step?.detail || ""),
      tab: step?.tab || null,
      source: "legacy_steps",
    };
  });
}

function documentDetail(advice) {
  const required = list(advice.required_documents).length;
  const conditional = list(advice.conditional_documents).length;
  const missing = list(advice.missing_or_unconfirmed_documents).length;
  const parts = [];
  if (required) parts.push(`${required} required`);
  if (conditional) parts.push(`${conditional} conditional`);
  if (missing) parts.push(`${missing} unconfirmed`);
  return parts.length ? `${parts.join(" · ")} document items` : "Review shipment and origin documents.";
}

export function deriveProcessFlow(result, fallbackSteps = []) {
  const payload = object(result);
  if (!Object.keys(payload).length) return fallbackNodes(fallbackSteps);

  const nodes = [];
  const add = (id, label, kind, status, detail, tab, source) => {
    if (nodes.some((node) => node.id === id)) return;
    nodes.push({ id, label, kind, status: cleanStatus(status), tone: tone(status), detail: detail || "", tab: tab || null, source });
  };

  add(
    "request",
    "Shipment request received",
    "terminal",
    "ready",
    "The request has been converted into structured shipment, route, compliance and cost inputs.",
    "Shipping Assistant",
    "request",
  );

  const verdictObject = object(payload.final_verdict);
  const decision = cleanStatus(payload.decision || verdictObject.verdict);
  const missingCount = Number(payload.missing_information_count || 0);
  const clarificationCount = list(payload.clarification_questions).length;
  const previewCount = list(payload.missing_information_preview).length;
  if (missingCount || clarificationCount || previewCount || decision.includes("needs_more")) {
    add(
      "clarify",
      "Are shipment details complete?",
      "decision",
      "blocked",
      `${Math.max(missingCount, clarificationCount, previewCount)} detail(s) need confirmation before planning can advance.`,
      "Shipping Assistant",
      "missing_information",
    );
  }

  const logistics = object(payload.logistics_metrics);
  if (Object.keys(logistics).length) {
    const details = [
      logistics.total_cbm != null ? `${logistics.total_cbm} CBM` : null,
      logistics.total_weight_kg != null ? `${logistics.total_weight_kg} kg` : null,
      logistics.recommended_container || null,
    ].filter(Boolean).join(" · ");
    add("plan", "Calculate shipment plan", "process", logistics.readiness_status || "review", details, "Shipments", "logistics_metrics");
  }

  const visualizer = object(payload.logistics_visualizer);
  if (visualizer.status === "available") {
    const container = object(visualizer.container);
    const details = [
      container.selected_container,
      container.utilization_percent != null ? `${container.utilization_percent}% utilized` : null,
    ].filter(Boolean).join(" · ");
    add("load", "Review container loading layout", "process", "ready", details, "Container Planning", "logistics_visualizer");
  }

  const route = object(payload.route_plan);
  if (route.applicable) {
    add(
      "route",
      route.inland_precarriage_required === true ? "Plan inland pre-carriage and ocean route" : "Confirm gateways and indicative route",
      "process",
      route.status || "review",
      route.indicative_corridor || "Review origin gateway, ocean corridor and destination gateway.",
      "Shipments",
      "route_plan",
    );
  }

  const flags = cargoFlags(payload);
  if (flags.hazardous) {
    add(
      "specialist",
      flags.radioactive ? "Are Class 7 specialist approvals complete?" : flags.battery ? "Are dangerous-goods carrier approvals complete?" : "Are specialist cargo approvals complete?",
      "decision",
      "blocked",
      flags.radioactive
        ? "Confirm radiation authority approvals, licensed carrier acceptance, shielding and emergency documentation."
        : flags.battery
          ? "Confirm UN classification, battery test evidence, dangerous-goods declaration and carrier acceptance."
          : "Confirm specialist handling, carrier acceptance and regulatory approvals.",
      "Compliance & Docs",
      "authoritative_cargo_flags",
    );
  }

  const agreement = object(payload.trade_agreement_advice);
  if (agreement.applicable) {
    add(
      "agreement",
      "Is preferential trade treatment available?",
      "decision",
      agreement.agreement_exists_in_local_reference === true ? "review_required" : "not_confirmed",
      agreement.agreement_exists_in_local_reference === true
        ? agreement.agreement_name || "A preferential agreement exists in the local reference."
        : "No preferential agreement is confirmed in the local reference; verify the official customs position.",
      "Compliance & Docs",
      "trade_agreement_advice",
    );
  }

  const compliance = object(payload.trade_compliance_readiness);
  if (compliance.applicable) {
    add("compliance", "Is trade compliance ready?", "decision", compliance.status || "review", compliance.summary || "Review restrictions, classification, permits and partner checks.", "Compliance & Docs", "trade_compliance_readiness");
  }

  const documents = object(payload.document_requirements_advice);
  if (documents.applicable) {
    add("documents", "Prepare and confirm documents", "document", documents.status || "review", documentDetail(documents), "Compliance & Docs", "document_requirements_advice");
  }

  const insurance = object(payload.insurance_advice);
  if (insurance.applicable) {
    add("insurance", "Confirm cargo insurance", "process", insurance.status || "review", insurance.summary || "Confirm responsibility, cargo value, coverage and exclusions.", "Reports", "insurance_advice");
  }

  const landed = object(payload.landed_cost_advice);
  if (landed.applicable) {
    const missing = list(landed.missing_cost_inputs);
    const complete = !missing.length && !["blocked", "needs_more_information"].includes(cleanStatus(landed.status));
    add(
      "cost",
      complete ? "Review landed-cost result" : "Complete landed-cost inputs",
      "process",
      complete ? "ready" : landed.status || "blocked",
      complete ? landed.summary || "Validate duty, tax, insurance and delivery costs." : `${missing.length || "Some"} commercial input(s) remain.`,
      "Reports",
      "landed_cost_advice",
    );
  }

  const readiness = object(payload.booking_readiness);
  const finalStatus = verdictObject.verdict || readiness.status || payload.decision || "review_required";
  add("booking", "Is the shipment ready to book?", "decision", finalStatus, readiness.summary || "Resolve remaining blockers and complete live partner checks before booking.", "Shipments", "final_verdict");
  add(
    "finish",
    tone(finalStatus) === "ready" ? "Proceed to booking" : "Resolve review items",
    "terminal",
    finalStatus,
    tone(finalStatus) === "ready" ? "The available planning and readiness gates have passed." : "Complete the highlighted decisions, documents and commercial inputs, then rerun the plan.",
    "Shipments",
    "booking_outcome",
  );

  return nodes;
}

export function connectorLabel(node) {
  if (!node) return "";
  if (node.id === "clarify") return "Details supplied";
  if (node.id === "specialist") return "Approval confirmed";
  if (node.id === "agreement") return node.tone === "ready" ? "Eligible" : "Verify";
  if (node.id === "compliance") return node.tone === "blocked" ? "Resolve" : "Continue";
  if (node.id === "booking") return node.tone === "ready" ? "Yes" : "Not yet";
  return "Next";
}
