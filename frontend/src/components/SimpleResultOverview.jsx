import Badge from "./Badge.jsx";
import { cleanText, humanizeKey } from "../utils/displayFormat.js";

function asList(value) {
  if (!value) return [];
  return Array.isArray(value) ? value.filter(Boolean) : [value];
}

function firstValue(...values) {
  return values.find((value) => value !== null && value !== undefined && value !== "");
}

function firstNumber(...values) {
  for (const value of values) {
    const number = Number(value);
    if (Number.isFinite(number)) return number;
  }
  return null;
}

function uniqueText(items) {
  return [...new Set(items.map((item) => cleanText(humanizeKey(item))).filter(Boolean))];
}

// BOOKING_STATUS_MEANING_V92
function statusMeaning(result, missing) {
  const executive = result.executive_summary || {};
  const booking = result.booking_readiness_advice || result.booking_readiness || {};
  const status = String(result.status || result.decision || executive.status || "").toLowerCase();
  const readyToBook = executive.ready_for_booking === true || booking.ready_for_booking === true || booking.ready_to_book === true || status.includes("ready_to_book");
  const hardBlockers = asList(booking.hard_blockers);
  const readyForReview = executive.ready_for_first_pass === true || booking.ready_for_first_pass === true;

  if (readyToBook) return "The required booking details and checks are complete enough to proceed to carrier booking review.";
  if (hardBlockers.length || status.includes("critical")) return "The shipment should not move forward yet. Resolve the highlighted safety or compliance blocker first.";
  if (readyForReview) return "The plan is ready for review. Any items shown below are the specific requirements that remain before booking.";
  if (missing.length) return "A useful first plan is available, but more information is needed before review.";
  return "The system has produced a first-pass shipment result.";
}

function OverviewSection({ title, children, tone = "" }) {
  return <section className={`simple-result-section ${tone}`}><h3>{title}</h3>{children}</section>;
}

export default function SimpleResultOverview({ result }) {
  if (!result) return null;

  const executive = result.executive_summary || {};
  const booking = result.booking_readiness_advice || result.booking_readiness || {};
  const metrics = result.logistics_metrics || {};
  const visualizer = result.logistics_visualizer || {};
  const container = visualizer.container || {};
  const display = visualizer.display_metrics || visualizer.utilization || {};
  const handoff = result.handoff_payload || {};

  const totalCbm = firstNumber(display.loaded_cbm, display.total_cbm, container.total_cbm, handoff.total_cbm, metrics.total_cbm);
  const totalWeight = firstNumber(container.total_weight_kg, handoff.total_weight_kg, metrics.total_weight_kg);
  const utilization = firstNumber(display.utilization_percent, container.utilization_percent);
  const containerName = firstValue(container.recommended_container, container.container_type, container.type, handoff.container_recommendation, metrics.container_recommendation);

  // SIMPLE_BOOKING_REQUIREMENTS_V91
  const bookingRequirements = uniqueText(
    asList(booking.booking_requirements)
  ).slice(0, 6);

  const followUpItems = uniqueText([
    ...asList(result.missing_information_preview),
    ...asList(executive.top_missing_items),
    ...asList(booking.missing_information),
    ...asList(booking.pre_dispatch_items),
    ...asList(booking.informational_items),
  ])
    .filter((item) => !bookingRequirements.includes(item))
    .slice(0, 6);

  const missing = bookingRequirements.length ? bookingRequirements : followUpItems;

  const actions = uniqueText([
    ...asList(result.action_plan?.immediate_actions),
    ...asList(result.action_plan?.next_steps),
    ...asList(result.action_plan?.recommended_actions),
    ...asList(result.booking_readiness_advice?.recommendations),
  ]).slice(0, 6);

  const calculated = [];
  if (totalCbm !== null) calculated.push(["Cargo volume", `${totalCbm.toLocaleString()} CBM`]);
  if (totalWeight !== null) calculated.push(["Total weight", `${totalWeight.toLocaleString()} kg`]);
  if (containerName) calculated.push(["Suggested container", humanizeKey(containerName)]);
  if (utilization !== null) calculated.push(["Container use", `${utilization.toLocaleString()}%`]);

  return (
    <div className="simple-result-overview" aria-label="Plain-language shipment result">
      <div className="simple-result-overview-head">
        <div><span>Simple result</span><h2>Your shipment at a glance</h2></div>
        <Badge status={result.status || result.decision || executive.status} />
      </div>
      <p className="simple-result-headline">{cleanText(executive.headline || executive.summary || "The system completed a first-pass shipment assessment.")}</p>

      <div className="simple-result-grid">
        <OverviewSection title="1. What was calculated">
          {calculated.length ? <dl className="simple-result-metrics">{calculated.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl> : <p>The system completed a first-pass assessment. More measurements may be needed for exact figures.</p>}
        </OverviewSection>

        <OverviewSection title="2. What this means" tone="meaning">
          <p>{statusMeaning(result, missing)}</p>
        </OverviewSection>

        <OverviewSection
          title={bookingRequirements.length ? "3. Required before booking" : "3. Booking requirements"}
          tone={bookingRequirements.length ? "attention" : "complete"}
        >
          {bookingRequirements.length ? (
            <ul>{bookingRequirements.map((item) => <li key={item}>{item}</li>)}</ul>
          ) : (
            <>
              <p>No booking-critical requirements remain.</p>
              {followUpItems.length ? <p>Other review, document-pack, or informational notes remain available in the full breakdown.</p> : null}
            </>
          )}
        </OverviewSection>

        <OverviewSection title="4. What to do next" tone="next">
          {actions.length ? <ol>{actions.map((item) => <li key={item}>{item}</li>)}</ol> : <p>Review the plan, confirm its assumptions, and obtain a live carrier quote before booking.</p>}
        </OverviewSection>
      </div>
    </div>
  );
}
