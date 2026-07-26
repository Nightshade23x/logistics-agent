var LABEL_OVERRIDES = {
  cbm: "CBM",
  usd: "USD",
  kg: "kg",
  fcl: "FCL",
  lcl: "LCL",
  vat: "VAT",
  hs: "HS",
  exw: "EXW",
  fob: "FOB",
  cif: "CIF",
  dap: "DAP",
  ddp: "DDP",

  origin_country: "Origin country",
  destination_country: "Destination country",
  freight_quote_usd: "Freight quote",
  insurance_premium_usd: "Insurance premium",
  duty_rate_percent: "Duty rate",
  import_tax_rate_percent: "Import tax / VAT rate",
  customs_brokerage_usd: "Customs brokerage",
  local_delivery_usd: "Local delivery",
  procurement_value_usd: "Procurement value",
  estimated_duty: "Estimated duty",
  estimated_import_tax_or_vat: "Estimated import tax / VAT",
  total_cbm: "Total CBM",
  total_weight_kg: "Total weight",
  recommended_container: "Recommended container",
  recommended_load_type: "Recommended load type",
  risk_level: "Risk level",
  risk_score: "Risk score",
  readiness_status: "Readiness status",
  ready_for_first_pass: "Ready for first pass",
  ready_for_booking: "Ready for booking",
  ready_for_partner_review: "Ready for partner review",
  next_gate: "Next gate",
  selected_items_count: "Selected items",
  supplier_options_count: "Supplier options",
  estimated_total_procurement_cost_usd: "Estimated procurement cost",
  budget_usd: "Budget",
  selected_product_names: "Selected products",
  selected_supplier_countries: "Supplier countries",
  missing_information: "Missing information",
  missing_cost_inputs: "Missing cost inputs",
  known_inputs: "Known inputs",
  required_documents: "Required documents",
  conditional_documents: "Conditional documents",
  missing_or_unconfirmed_documents: "Missing or unconfirmed documents",
  user_questions: "Open questions",
  cargo_items_preview: "Cargo items",
  partner_review_status: "Partner review status",
  landed_cost_formula: "Landed cost formula",
  insurance_recommendation: "Insurance recommendation",
  estimated_cargo_value_usd: "Estimated cargo value",
  estimated_subtotal_known_usd: "Known subtotal",
  trade_term: "Trade term",
  incoterm: "Incoterm",
  item_count: "Item count",
  agents_called: "Agents called",
  served_by: "Served by",
  response_contract_valid: "Contract valid",
  response_contract_errors: "Errors",
  response_contract_warnings: "Warnings"
};

var STATUS_OVERRIDES = {
  needs_more_information: "Needs more information",
  partial_plan_needs_more_information: "Partial plan needs more information",
  review_required: "Review required",
  ready_for_review: "Ready for review",
  ready_for_review_with_high_risk: "Ready for review with high risk",
  blocked: "Blocked",
  critical_review_required: "Critical review required",
  clear: "Clear",
  not_applicable: "Not applicable",
  unknown: "Unknown",
  unavailable: "Unavailable",
  available: "Available",
  partner_review_not_configured: "Partner review not configured",
  resolve_blockers: "Resolve blockers",
  fill_missing_information: "Fill missing information",
  review_before_booking: "Review before booking",
  fcl_preferred: "FCL preferred",
  lcl_suitable: "LCL suitable",
  fcl_suitable: "FCL suitable"
};

function titleCaseWords(text) {
  var words = String(text || "").split(" ");
  var output = [];

  for (var i = 0; i < words.length; i += 1) {
    var word = words[i];

    if (!word) {
      continue;
    }

    var upper = word.toUpperCase();

    if (
      upper === "USD" ||
      upper === "CBM" ||
      upper === "VAT" ||
      upper === "FCL" ||
      upper === "LCL" ||
      upper === "HS" ||
      word === "kg"
    ) {
      output.push(upper === "KG" ? "kg" : upper);
    } else {
      output.push(word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
    }
  }

  return output.join(" ");
}

function basicClean(value) {
  var text = String(value || "").trim();

  text = text.split("_").join(" ");
  text = text.split(" usd").join(" USD");
  text = text.split(" cbm").join(" CBM");
  text = text.split(" vat").join(" VAT");
  text = text.split(" fcl").join(" FCL");
  text = text.split(" lcl").join(" LCL");
  text = text.split(" hs").join(" HS");
  text = text.split(" kg").join(" kg");

  while (text.indexOf("  ") >= 0) {
    text = text.split("  ").join(" ");
  }

  return text.trim();
}

export function humanizeKey(value) {
  if (value === null || value === undefined) {
    return "";
  }

  var raw = String(value).trim();
  var lower = raw.toLowerCase();

  if (LABEL_OVERRIDES[raw]) {
    return LABEL_OVERRIDES[raw];
  }

  if (LABEL_OVERRIDES[lower]) {
    return LABEL_OVERRIDES[lower];
  }

  if (STATUS_OVERRIDES[raw]) {
    return STATUS_OVERRIDES[raw];
  }

  if (STATUS_OVERRIDES[lower]) {
    return STATUS_OVERRIDES[lower];
  }

  if (lower.indexOf("document:") === 0) {
    return "Document: " + titleCaseWords(basicClean(raw.slice(raw.indexOf(":") + 1)));
  }

  if (lower.indexOf("landed cost input:") === 0) {
    return "Landed cost: " + humanizeKey(raw.slice(raw.indexOf(":") + 1).trim());
  }

  return titleCaseWords(basicClean(raw));
}

export function humanizeStatus(value) {
  if (value === null || value === undefined || value === "") {
    return "Unknown";
  }

  return humanizeKey(value);
}

export function formatValue(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (typeof value === "number") {
    if (Number.isInteger(value)) {
      return String(value);
    }

    return String(Number(value.toFixed(2)));
  }

  if (Array.isArray(value)) {
    if (!value.length) {
      return "-";
    }

    var arr = [];

    for (var i = 0; i < value.length; i += 1) {
      if (typeof value[i] === "string") {
        arr.push(humanizeKey(value[i]));
      } else {
        arr.push(formatValue(value[i]));
      }
    }

    return arr.join(", ");
  }

  if (typeof value === "object") {
    var entries = Object.entries(value);
    var parts = [];

    for (var j = 0; j < entries.length; j += 1) {
      var key = entries[j][0];
      var child = entries[j][1];

      if (
        child === null ||
        child === undefined ||
        child === "" ||
        (Array.isArray(child) && child.length === 0)
      ) {
        continue;
      }

      parts.push(humanizeKey(key) + ": " + formatValue(child));
    }

    if (!parts.length) {
      return "-";
    }

    return parts.join(", ");
  }

  return humanizeKey(String(value));
}

export function cleanText(value) {
  if (!value) {
    return "";
  }

  return basicClean(value);
}

export function classifyMissingItem(item) {
  var text = String(item || "").toLowerCase();

  if (text.indexOf("origin") >= 0 || text.indexOf("destination") >= 0 || text.indexOf("incoterm") >= 0) {
    return "Route";
  }

  if (
    text.indexOf("freight") >= 0 ||
    text.indexOf("insurance") >= 0 ||
    text.indexOf("duty") >= 0 ||
    text.indexOf("tax") >= 0 ||
    text.indexOf("vat") >= 0 ||
    text.indexOf("brokerage") >= 0 ||
    text.indexOf("delivery") >= 0 ||
    text.indexOf("cost") >= 0
  ) {
    return "Finance";
  }

  if (
    text.indexOf("document") >= 0 ||
    text.indexOf("invoice") >= 0 ||
    text.indexOf("packing") >= 0 ||
    text.indexOf("bill of lading") >= 0
  ) {
    return "Documents";
  }

  if (
    text.indexOf("quantity") >= 0 ||
    text.indexOf("weight") >= 0 ||
    text.indexOf("cbm") >= 0 ||
    text.indexOf("dimension") >= 0
  ) {
    return "Cargo";
  }

  return "Other";
}

export function groupItems(items) {
  var groups = {};
  var list = Array.isArray(items) ? items : [];

  for (var i = 0; i < list.length; i += 1) {
    var group = classifyMissingItem(list[i]);

    if (!groups[group]) {
      groups[group] = [];
    }

    groups[group].push(list[i]);
  }

  return groups;
}

export function uniq(items) {
  var seen = {};
  var out = [];
  var list = Array.isArray(items) ? items : [];

  for (var i = 0; i < list.length; i += 1) {
    var item = list[i];
    var key = String(item || "").trim().toLowerCase();

    if (!key || seen[key]) {
      continue;
    }

    seen[key] = true;
    out.push(item);
  }

  return out;
}
