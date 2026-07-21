import Badge from "../components/Badge.jsx";
import Kpi from "../components/Kpi.jsx";
import SectionCard from "../components/SectionCard.jsx";
import ResultGate from "../components/ResultGate.jsx";

function ExecutiveSummary({ es }) {
  if (!es || !es.applicable) return null;
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Executive Summary</div>
        <Badge status={es.status} />
      </div>
      <div className="card-body">
        <p style={{ marginBottom: 14, fontWeight: 500 }}>{es.headline}</p>
        <div className="kpi-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
          <Kpi label="Booking score" value={es.booking_score} tone="blue" />
          <Kpi label="Ready first pass" value={es.ready_for_first_pass ? "Yes" : "No"} tone={es.ready_for_first_pass ? "teal" : "amber"} />
          <Kpi label="Ready to book" value={es.ready_for_booking ? "Yes" : "No"} tone={es.ready_for_booking ? "teal" : "red"} />
          <Kpi label="Next gate" value={String(es.next_gate || "—").replaceAll("_", " ")} />
        </div>
        <div className="grid-2">
          <div>
            <div className="form-label">Top strengths</div>
            <ul className="bullets">{(es.top_strengths || []).slice(0, 6).map((s, i) => <li key={i}>{s}</li>)}</ul>
          </div>
          <div>
            <div className="form-label">Top risks</div>
            <ul className="bullets">{(es.top_risks || []).slice(0, 6).map((s, i) => <li key={i}>{s}</li>)}</ul>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Shipments() {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Shipments</div>
          <div className="page-subtitle">Full agent breakdown for the most recently processed request.</div>
        </div>
      </div>

      <ResultGate>
        {(result) => (
          <div className="content-grid">
            <div className="content-col">
              <ExecutiveSummary es={result.executive_summary} />
              {(result.ui_sections || []).map((s) => (
                <SectionCard key={s.section_id} section={s} />
              ))}
            </div>
            <div className="content-col">
              <div className="card">
                <div className="card-header">
                  <div className="card-title">Backend Validation</div>
                  <Badge status={result.backend_validation?.response_contract_valid ? "clear" : "blocked"} />
                </div>
                <div className="card-body">
                  <ul className="info-list">
                    <li><span className="label">Contract valid</span><span className="value">{String(result.backend_validation?.response_contract_valid)}</span></li>
                    <li><span className="label">Errors</span><span className="value">{result.backend_validation?.response_contract_errors?.length || 0}</span></li>
                    <li><span className="label">Warnings</span><span className="value">{result.backend_validation?.response_contract_warnings?.length || 0}</span></li>
                  </ul>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <div className="card-title">Request Metadata</div>
                </div>
                <div className="card-body">
                  <ul className="info-list">
                    <li><span className="label">Type</span><span className="value">{result.request_metadata?.request_type}</span></li>
                    <li><span className="label">Served by</span><span className="value">{result.request_metadata?.served_by}</span></li>
                    <li><span className="label">Agents called</span><span className="value">{(result.agents_called || []).join(", ")}</span></li>
                  </ul>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <div className="card-title">Missing Information</div>
                  <span className="tab-count">{result.missing_information_count ?? 0}</span>
                </div>
                <div className="card-body">
                  {(result.missing_information_preview || []).length ? (
                    <ul className="bullets">{result.missing_information_preview.map((m, i) => <li key={i}>{m}</li>)}</ul>
                  ) : (
                    <p style={{ color: "var(--text-muted)" }}>Nothing missing.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </ResultGate>
    </>
  );
}
