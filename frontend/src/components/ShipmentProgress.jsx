const STAGES = [
  { label: "Draft", help: "Shipment details are being entered." },
  { label: "Details checked", help: "The system has produced a first calculation." },
  { label: "More information needed", help: "Some details still need to be confirmed." },
  { label: "Ready for review", help: "The plan is ready for a person to review." },
  { label: "Ready to book", help: "Required details and checks appear complete." },
];

function asList(value) {
  if (!value) return [];
  return Array.isArray(value) ? value.filter(Boolean) : [value];
}

// READINESS_PROGRESS_TRANSITION_V90
// "Ready for review" and "Ready to book" are separate gates.
// Active clarification questions block review; booking-only missing items do not.
export function shipmentProgressIndex(result) {
  if (!result) return 0;

  const executive = result.executive_summary || {};
  const booking = result.booking_readiness_advice || result.booking_readiness || {};
  const activeQuestions = [
    ...asList(result.clarification_questions),
    ...asList(result.action_plan?.user_questions),
  ];
  const status = String(result.status || result.decision || executive.status || "").toLowerCase();

  // HARD_BLOCKER_PROGRESS_V92
  const hardBlockers = asList(booking.hard_blockers);
  const hasHardBlocker =
    hardBlockers.length > 0 ||
    status.includes("critical_review_required") ||
    status === "blocked";

  const readyToBook =
    executive.ready_for_booking === true ||
    booking.ready_for_booking === true ||
    booking.ready_to_book === true ||
    status.includes("ready_to_book");

  const readyForFirstPass =
    executive.ready_for_first_pass === true ||
    booking.ready_for_first_pass === true;

  if (readyToBook) return 4;
  if (hasHardBlocker) return 2;
  if (activeQuestions.length) return 2;
  if (readyForFirstPass) return 3;
  if (status.includes("missing") || status.includes("blocked")) return 2;
  if (status.includes("review") || result) return 3;
  return 1;
}

function progressHelp(result, activeIndex) {
  const booking = result?.booking_readiness_advice || result?.booking_readiness || {};
  const activeQuestions = [
    ...asList(result?.clarification_questions),
    ...asList(result?.action_plan?.user_questions),
  ];

  if (activeIndex === 2) {
    const hardBlockers = asList(booking.hard_blockers);
    if (hardBlockers.length) {
      // CRITICAL_BLOCKER_COPY_V93
      const actionable = hardBlockers.filter(
        (item) => !/^\s*[a-z_ ]+\s+has\s+blockers\.?\s*$/i.test(String(item))
      );
      const displayItems = actionable.length ? actionable : hardBlockers;
      const preview = displayItems.slice(0, 2).map((item) => String(item)).join("; ");

      if (displayItems.length > 2) {
        return `Critical blockers must be resolved before Ready for review: ${preview}. See "Required before booking" below for the full list.`;
      }

      return `Critical blocker${displayItems.length === 1 ? "" : "s"} must be resolved before Ready for review: ${preview}.`;
    }

    if (activeQuestions.length) {
      return `${activeQuestions.length} clarification${activeQuestions.length === 1 ? "" : "s"} remain before Ready for review.`;
    }
  }

  if (activeIndex === 3) {
    // READY_TO_BOOK_COUNT_V91
    const explicitRequirements = asList(booking.booking_requirements);
    const bookingRemaining = explicitRequirements.length
      ? explicitRequirements
      : [
          ...asList(booking.hard_blockers || booking.blockers),
          ...asList(booking.booking_missing_items || booking.missing_information),
          ...asList(booking.booking_review_items),
        ];

    if (bookingRemaining.length) {
      const preview = bookingRemaining
        .slice(0, 3)
        .map((item) => String(item))
        .join("; ");
      const extra = bookingRemaining.length > 3 ? `; +${bookingRemaining.length - 3} more` : "";
      return `Ready for review. ${bookingRemaining.length} required item${bookingRemaining.length === 1 ? "" : "s"} remain before Ready to book: ${preview}${extra}.`;
    }

    return "Ready for review. No booking-critical requirements remain.";
  }

  return STAGES[activeIndex].help;
}

export default function ShipmentProgress({ result = null }) {
  const activeIndex = shipmentProgressIndex(result);

  return (
    <section className="shipment-progress-card" aria-labelledby="shipment-progress-title">
      <div className="shipment-progress-head">
        <div><span>Shipment progress</span><strong id="shipment-progress-title">{STAGES[activeIndex].label}</strong></div>
        <p>{progressHelp(result, activeIndex)}</p>
      </div>
      <ol className="shipment-progress-list">
        {STAGES.map((stage, index) => (
          <li className={index === activeIndex ? "current" : index < activeIndex ? "complete" : "upcoming"} aria-current={index === activeIndex ? "step" : undefined} key={stage.label}>
            <span className="shipment-progress-dot">{index < activeIndex ? "✓" : index + 1}</span>
            <span><b>{stage.label}</b><small>{stage.help}</small></span>
          </li>
        ))}
      </ol>
    </section>
  );
}
