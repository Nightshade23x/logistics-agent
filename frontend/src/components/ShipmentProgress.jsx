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

export function shipmentProgressIndex(result) {
  if (!result) return 0;

  const executive = result.executive_summary || {};
  const booking = result.booking_readiness_advice || result.booking_readiness || {};
  const missing = [
    ...asList(result.missing_information_preview),
    ...asList(executive.top_missing_items),
    ...asList(booking.missing_information),
  ];
  const status = String(result.status || result.decision || executive.status || "").toLowerCase();
  const readyToBook = executive.ready_for_booking === true || booking.ready_for_booking === true || booking.ready_to_book === true || status.includes("ready_to_book");

  if (readyToBook) return 4;
  if (missing.length || status.includes("missing") || status.includes("blocked")) return 2;
  if (status.includes("review") || executive.ready_for_first_pass === true || result) return 3;
  return 1;
}

export default function ShipmentProgress({ result = null }) {
  const activeIndex = shipmentProgressIndex(result);

  return (
    <section className="shipment-progress-card" aria-labelledby="shipment-progress-title">
      <div className="shipment-progress-head">
        <div><span>Shipment progress</span><strong id="shipment-progress-title">{STAGES[activeIndex].label}</strong></div>
        <p>{STAGES[activeIndex].help}</p>
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
