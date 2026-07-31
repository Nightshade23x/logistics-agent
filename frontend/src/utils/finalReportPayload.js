// Final defensive normalization for Reports / JSON export.
//
// This does not invent shipment facts. It resolves duplicated
// fields using explicit/canonical values that already exist in
// the backend response.

function numberOrNull(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return null;
  }

  const valueNumber = Number(value);

  return Number.isFinite(valueNumber)
    ? valueNumber
    : null;
}


function explicitWeightFromPrompt(result) {
  const text = String(
    result?.request_metadata?.input_source || ""
  );

  const patterns = [
    /\btotal\s+weight\s*(?:is|=|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*kg\b/i,
    /\bweight\s*(?:is|=|:)\s*([0-9]+(?:\.[0-9]+)?)\s*kg\b/i,
    /\bweighs?\s*([0-9]+(?:\.[0-9]+)?)\s*kg\b/i,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);

    if (match) {
      const value = numberOrNull(match[1]);

      if (value !== null) {
        return value;
      }
    }
  }

  return null;
}


function cleanText(value) {
  const text = String(value ?? "").trim();
  const lower = text.toLowerCase();

  if (
    lower.includes("review was not applicable")
  ) {
    return "";
  }

  if (
    lower === "landed_cost has blockers."
  ) {
    return "Complete the missing landed-cost inputs before booking.";
  }

  if (
    lower === "trade_compliance has blockers."
  ) {
    return "Complete the required document and compliance checks before booking.";
  }

  if (
    lower === "document_requirements needs more information."
  ) {
    return "Complete the required shipment documents before final review.";
  }

  return text;
}


function cleanList(values) {
  const output = [];
  const seen = new Set();

  for (const value of values || []) {
    const cleaned = cleanText(value);

    if (!cleaned) {
      continue;
    }

    const key = cleaned.toLowerCase();

    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    output.push(cleaned);
  }

  return output;
}


function syncSection(result, id, callback) {
  const sections = result?.ui_sections;

  if (!Array.isArray(sections)) {
    return;
  }

  const section = sections.find(
    (item) =>
      item &&
      typeof item === "object" &&
      item.section_id === id
  );

  if (section) {
    callback(section);
  }
}



// FINAL_NP_EXPORT_CLEANUP_V2
function finalNpDirectItemsV2(textValue) {
  const text = String(textValue || "");

  const pattern =
    /([0-9]+(?:\.[0-9]+)?)\s*CBM\s+(?:of\s+)?(.*?)\s+weigh(?:ing|s)?\s+([0-9]+(?:\.[0-9]+)?)\s*kg\s*(?=(?:,?\s*(?:and|plus|&)\s+[0-9]+(?:\.[0-9]+)?\s*CBM\b)|\s+from\b|[.;]|$)/gi;

  const items = [];

  let match;

  while ((match = pattern.exec(text)) !== null) {
    const cbm = Number(match[1]);
    const name = String(match[2] || "").trim();
    const weight = Number(match[3]);

    if (
      Number.isFinite(cbm) &&
      cbm > 0 &&
      Number.isFinite(weight) &&
      weight > 0 &&
      name
    ) {
      items.push({
        item_name: name,
        quantity: 1,
        total_cbm: cbm,
        unit_cbm: cbm,
        total_weight_kg: weight,
        unit_weight_kg: weight,
        aggregate_volume_only: true,
        dimensions_are_aggregate: true,
        display_dimensions_estimated: true,
        weight_estimated: false,
        weight_source: "explicit_user_item_weight",
        category_tags: ["general_cargo"],
      });
    }
  }

  return items.length >= 2
    ? items
    : [];
}


function finalNpCleanReportV2(result) {
  if (
    !result ||
    typeof result !== "object"
  ) {
    return result;
  }

  const prompt = String(
    result?.request_metadata?.input_source || ""
  );

  const parsedItems =
    finalNpDirectItemsV2(prompt);


  // ---------------------------------------------------------
  // N: direct multi-item aggregate data
  // ---------------------------------------------------------

  if (parsedItems.length >= 2) {
    const totalCbm = parsedItems.reduce(
      (sum, item) => sum + item.total_cbm,
      0
    );

    const totalWeight = parsedItems.reduce(
      (sum, item) => sum + item.total_weight_kg,
      0
    );

    const visualizer =
      result.logistics_visualizer;

    if (
      visualizer &&
      typeof visualizer === "object"
    ) {
      const previous = Array.isArray(
        visualizer.cargo_mix
      )
        ? visualizer.cargo_mix
        : [];

      const previousByName =
        new Map(
          previous
            .filter(
              (item) =>
                item &&
                typeof item === "object"
            )
            .map(
              (item) => [
                String(
                  item.item_name || ""
                ).toLowerCase(),
                item,
              ]
            )
        );


      visualizer.cargo_mix =
        parsedItems.map((item) => {
          const previousItem =
            previousByName.get(
              item.item_name.toLowerCase()
            ) || {};

          return {
            ...previousItem,
            ...item,

            dimensions_m:
              previousItem.dimensions_m ||
              item.dimensions_m,

            category_tags:
              Array.isArray(
                previousItem.category_tags
              ) &&
              previousItem.category_tags.length
                ? previousItem.category_tags
                : item.category_tags,
          };
        });


      if (
        visualizer.container &&
        typeof visualizer.container === "object"
      ) {
        visualizer.container.total_cbm =
          totalCbm;

        visualizer.container.total_weight_kg =
          totalWeight;

        visualizer.container.total_items =
          parsedItems.length;
      }


      if (
        visualizer.display_metrics &&
        typeof visualizer.display_metrics === "object"
      ) {
        visualizer.display_metrics.loaded_cbm =
          totalCbm;
      }
    }


    const freight =
      result?.logistics_quality_review
        ?.freight_mode_advice;

    if (
      freight &&
      typeof freight === "object"
    ) {
      freight.total_cbm =
        totalCbm;

      freight.total_weight_kg =
        totalWeight;
    }
  }


  // ---------------------------------------------------------
  // P: preserve blocked payload-limit report state
  // ---------------------------------------------------------

  const payloadBlocked =
    result?.payload_constraint?.status ===
    "blocked";

  if (payloadBlocked) {
    const sections =
      Array.isArray(result.ui_sections)
        ? result.ui_sections
        : [];

    const logistics =
      sections.find(
        (section) =>
          section &&
          section.section_id === "logistics"
      );

    if (logistics) {
      logistics.status = "blocked";

      logistics.summary =
        "The shipment exceeds the reference single-container payload limit and requires multiple-container or specialist heavy-cargo planning.";
    }
  }


  return result;
}


export function normalizeFinalReportPayload(input) {
  if (
    !input ||
    typeof input !== "object"
  ) {
    return input;
  }

  let result;

  try {
    result = structuredClone(input);
  } catch {
    result = JSON.parse(
      JSON.stringify(input)
    );
  }


  const metrics =
    result.logistics_metrics &&
    typeof result.logistics_metrics === "object"
      ? result.logistics_metrics
      : (result.logistics_metrics = {});


  const handoff =
    result.handoff_payload &&
    typeof result.handoff_payload === "object"
      ? result.handoff_payload
      : {};


  const logisticsReview =
    result.logistics_quality_review &&
    typeof result.logistics_quality_review === "object"
      ? result.logistics_quality_review
      : {};


  const visualizer =
    result.logistics_visualizer &&
    typeof result.logistics_visualizer === "object"
      ? result.logistics_visualizer
      : {};


  const container =
    visualizer.container &&
    typeof visualizer.container === "object"
      ? visualizer.container
      : {};


  const totalWeight =
    explicitWeightFromPrompt(result) ??
    numberOrNull(handoff.total_weight_kg) ??
    numberOrNull(logisticsReview.total_weight_kg) ??
    numberOrNull(metrics.total_weight_kg) ??
    numberOrNull(container.total_weight_kg);


  const totalCbm =
    numberOrNull(handoff.total_cbm) ??
    numberOrNull(logisticsReview.total_cbm) ??
    numberOrNull(metrics.total_cbm) ??
    numberOrNull(container.total_cbm);


  const recommendedContainer =
    handoff.recommended_container ||
    handoff.container_recommendation ||
    logisticsReview.recommended_container ||
    metrics.recommended_container ||
    container.selected_container ||
    null;


  if (totalWeight !== null) {
    metrics.total_weight_kg = totalWeight;
    container.total_weight_kg = totalWeight;

    if (
      Array.isArray(visualizer.cargo_mix) &&
      visualizer.cargo_mix.length === 1 &&
      visualizer.cargo_mix[0] &&
      typeof visualizer.cargo_mix[0] === "object"
    ) {
      const item = visualizer.cargo_mix[0];

      const quantity =
        numberOrNull(item.quantity) || 1;

      item.total_weight_kg = totalWeight;
      item.unit_weight_kg =
        totalWeight / quantity;

      item.weight_estimated = false;
      item.weight_source =
        "explicit_user_or_canonical_weight";

      delete item.estimated_density_kg_per_cbm;
      delete item.weight_estimate_warning;
    }
  }


  if (totalCbm !== null) {
    metrics.total_cbm = totalCbm;
    container.total_cbm = totalCbm;
  }


  if (recommendedContainer) {
    metrics.recommended_container =
      recommendedContainer;

    container.selected_container =
      recommendedContainer;
  }


  // ---------------------------------------------
  // final_answer must represent the same answer
  // the user actually sees.
  // ---------------------------------------------

  const answer =
    result.display_answer ||
    result.frontend_answer ||
    "";

  if (answer) {
    result.display_answer = answer;
    result.frontend_answer = answer;

    if (
      !result.final_answer ||
      typeof result.final_answer !== "object"
    ) {
      result.final_answer = {};
    }

    result.final_answer.answer_text = answer;

    const firstLine = String(answer)
      .split(/\r?\n/)
      .find((line) => line.trim());

    if (firstLine) {
      result.final_answer.headline =
        firstLine.trim();
    }
  }


  // ---------------------------------------------
  // short answer
  // ---------------------------------------------

  const parts = [
    `Decision: ${
      result.decision ||
      result.status ||
      "review_required"
    }.`,
  ];

  if (
    Array.isArray(result.agents_called) &&
    result.agents_called.length
  ) {
    parts.push(
      `Agents called: ${result.agents_called.join(", ")}.`
    );
  }

  const logisticsBits = [];

  if (totalCbm !== null) {
    logisticsBits.push(
      `${totalCbm} CBM`
    );
  }

  if (totalWeight !== null) {
    logisticsBits.push(
      `${totalWeight} kg`
    );
  }

  if (recommendedContainer) {
    logisticsBits.push(
      `recommended container ${recommendedContainer}`
    );
  }

  if (metrics.risk_level) {
    logisticsBits.push(
      `risk level ${metrics.risk_level}`
    );
  }

  if (logisticsBits.length) {
    parts.push(
      `Logistics: ${logisticsBits.join(", ")}.`
    );
  }

  result.short_answer =
    parts.join(" ");


  // ---------------------------------------------
  // logistics report
  // ---------------------------------------------

  if (
    result.logistics_quality_review &&
    typeof result.logistics_quality_review === "object"
  ) {
    const review =
      result.logistics_quality_review;

    review.applicable = true;

    if (
      review.status === "not_applicable"
    ) {
      review.status = "review_required";
    }

    review.summary =
      "Logistics planning output is available and usable for first-pass shipment review.";

    if (totalCbm !== null) {
      review.total_cbm = totalCbm;
    }

    if (totalWeight !== null) {
      review.total_weight_kg =
        totalWeight;
    }

    if (recommendedContainer) {
      review.recommended_container =
        recommendedContainer;
    }
  }


  syncSection(
    result,
    "logistics",
    (section) => {
      section.status = "review_required";

      section.summary =
        "Logistics planning output is available and usable for first-pass shipment review.";

      if (
        !section.metrics ||
        typeof section.metrics !== "object"
      ) {
        section.metrics = {};
      }

      if (totalCbm !== null) {
        section.metrics.total_cbm =
          totalCbm;
      }

      if (totalWeight !== null) {
        section.metrics.total_weight_kg =
          totalWeight;
      }

      if (recommendedContainer) {
        section.metrics.recommended_container =
          recommendedContainer;
      }

      if (metrics.recommended_load_type) {
        section.metrics.recommended_load_type =
          metrics.recommended_load_type;
      }

      if (metrics.risk_level) {
        section.metrics.risk_level =
          metrics.risk_level;
      }

      if (
        metrics.risk_score !== undefined
      ) {
        section.metrics.risk_score =
          metrics.risk_score;
      }
    }
  );


  // ---------------------------------------------
  // cleanup internal report language
  // ---------------------------------------------

  if (
    result.executive_summary &&
    typeof result.executive_summary === "object"
  ) {
    result.executive_summary.top_risks =
      cleanList(
        result.executive_summary.top_risks
      );

    result.executive_summary.top_next_actions =
      cleanList(
        result.executive_summary.top_next_actions
      );
  }


  if (
    result.booking_readiness &&
    typeof result.booking_readiness === "object"
  ) {
    result.booking_readiness.review_items =
      cleanList(
        result.booking_readiness.review_items
      );

    result.booking_readiness.blockers =
      cleanList(
        result.booking_readiness.blockers
      );

    result.booking_readiness.next_steps =
      cleanList(
        result.booking_readiness.next_steps
      );
  }


  if (
    result.action_plan &&
    typeof result.action_plan === "object"
  ) {
    result.action_plan.immediate_actions =
      cleanList(
        result.action_plan.immediate_actions
      );

    result.action_plan.before_booking =
      cleanList(
        result.action_plan.before_booking
      );
  }


  syncSection(
    result,
    "executive_decision",
    (section) => {
      section.bullets =
        cleanList(section.bullets);

      section.actions =
        cleanList(section.actions);
    }
  );


  syncSection(
    result,
    "next_actions",
    (section) => {
      section.bullets =
        cleanList(section.bullets);

      section.actions =
        cleanList(section.actions);
    }
  );


  // ---------------------------------------------
  // Partner Checks contradiction
  // ---------------------------------------------

  syncSection(
    result,
    "partner_checks",
    (section) => {
      const partnerStatus =
        result.partner_review_status;

      if (
        partnerStatus === null ||
        partnerStatus === undefined ||
        partnerStatus === "" ||
        partnerStatus === "unknown"
      ) {
        section.status = "unknown";

        section.summary =
          "No structured partner-review result is available for this request.";

        section.bullets = [];
        section.actions = [];
      }
    }
  );


  result = finalNpCleanReportV2(result);

  return result;
}
