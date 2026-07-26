import Badge from "./Badge.jsx";
import { cleanText, formatValue, humanizeKey } from "../utils/displayFormat.js";

function StatCard({ label, value, tone }) {
  return (
    <div className={`executive-stat ${tone || ""}`}>
      <div className="executive-stat-label">{label}</div>
      <div className="executive-stat-value">{formatValue(value)}</div>
    </div>
  );
}

export default function ExecutiveSummary({ es }) {
  if (!es) return null;

  const topRisks = Array.isArray(es.top_risks) ? es.top_risks : [];
  const strengths = Array.isArray(es.top_strengths) ? es.top_strengths : [];
  const missing = Array.isArray(es.top_missing_items) ? es.top_missing_items : [];

  return (
    <div className="card executive-summary-v2">
      <div className="card-header">
        <div>
          <div className="card-title">Shipment status</div>
          <div className="section-muted">High-level readiness for the latest request</div>
        </div>
        <Badge status={es.status || es.decision} />
      </div>

      <div className="card-body">
        <p className="executive-headline">{cleanText(es.headline || es.summary || "Review the shipment result.")}</p>

        <div className="executive-stat-grid">
          <StatCard label="Booking score" value={`${es.booking_score ?? 0} / 100`} tone="score" />
          <StatCard label="Ready first pass" value={es.ready_for_first_pass} tone={es.ready_for_first_pass ? "good" : "warn"} />
          <StatCard label="Ready to book" value={es.ready_for_booking} tone={es.ready_for_booking ? "good" : "bad"} />
          <StatCard label="Next gate" value={humanizeKey(es.next_gate || "Review")} tone="gate" />
        </div>

        <div className="executive-columns">
          <div>
            <div className="section-subtitle">Strengths</div>
            {strengths.length ? (
              <ul className="compact-list">
                {strengths.slice(0, 5).map(function (item, index) {
                  return <li key={index}>{cleanText(item)}</li>;
                })}
              </ul>
            ) : (
              <p className="empty-text">No strengths confirmed yet.</p>
            )}
          </div>

          <div>
            <div className="section-subtitle">Main risks</div>
            {topRisks.length ? (
              <ul className="compact-list">
                {topRisks.slice(0, 6).map(function (item, index) {
                  return <li key={index}>{cleanText(item)}</li>;
                })}
              </ul>
            ) : (
              <p className="empty-text">No major risks listed.</p>
            )}
          </div>

          <div>
            <div className="section-subtitle">Missing</div>
            {missing.length ? (
              <ul className="compact-list">
                {missing.slice(0, 6).map(function (item, index) {
                  return <li key={index}>{humanizeKey(item)}</li>;
                })}
              </ul>
            ) : (
              <p className="empty-text">No missing items listed.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
