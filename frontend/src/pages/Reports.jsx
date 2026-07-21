import Badge from "../components/Badge.jsx";
import ResultGate from "../components/ResultGate.jsx";

function ChecklistCard({ title, items, priority = "med" }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">{title}</div>
        <span className="tab-count">{items.length}</span>
      </div>
      <div className="card-body tight">
        <ul className="checklist" style={{ padding: "0 18px" }}>
          {items.map((item, i) => (
            <li key={i}>
              <input type="checkbox" readOnly />
              <div className="check-content">
                <div className="check-title">{item}</div>
              </div>
              <span className={`check-priority ${priority}`}>{priority}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function Reports() {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Reports</div>
          <div className="page-subtitle">Final answer, action plan, and booking readiness gate.</div>
        </div>
      </div>

      <ResultGate>
        {(result) => {
          const fa = result.final_answer;
          const ap = result.action_plan;
          const br = result.booking_readiness;
          return (
            <>
              <div className="page-actions" style={{ marginBottom: 16 }}>
                <button className="btn" onClick={() => downloadJson(result, "shipment-report.json")}>
                  ⬇ Export full JSON
                </button>
              </div>

              <div className="content-grid">
                <div className="content-col">
                  <div className="card">
                    <div className="card-header">
                      <div className="card-title">Final Answer</div>
                      <Badge status={fa?.status} />
                    </div>
                    <div className="card-body">
                      <p style={{ fontWeight: 500, marginBottom: 10 }}>{fa?.headline}</p>
                      {fa?.answer_text && <p style={{ color: "var(--text-secondary)", marginBottom: 12 }}>{fa.answer_text}</p>}
                      <div className="grid-2">
                        <div>
                          <div className="form-label">Ready items</div>
                          <ul className="bullets">{(fa?.ready_items || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
                        </div>
                        <div>
                          <div className="form-label">Blockers</div>
                          <ul className="bullets">{(fa?.blockers || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
                        </div>
                      </div>
                    </div>
                  </div>

                  <ChecklistCard title="Immediate Actions" items={ap?.immediate_actions} priority="high" />
                  <ChecklistCard title="Before Booking" items={ap?.before_booking} priority="med" />
                  <ChecklistCard title="Partner Steps" items={ap?.partner_steps} priority="low" />
                  <ChecklistCard title="Open Questions" items={ap?.user_questions} priority="med" />
                </div>

                <div className="content-col">
                  <div className="card">
                    <div className="card-header">
                      <div className="card-title">Booking Readiness</div>
                      <Badge status={br?.status} />
                    </div>
                    <div className="card-body">
                      <div className="kpi" style={{ marginBottom: 12 }}>
                        <div className="kpi-label">Score</div>
                        <div className="kpi-value">{br?.score}<span className="unit">/ 100</span></div>
                      </div>
                      <ul className="info-list">
                        <li><span className="label">Ready first pass</span><span className="value">{String(br?.ready_for_first_pass)}</span></li>
                        <li><span className="label">Ready to book</span><span className="value">{String(br?.ready_for_booking)}</span></li>
                        <li><span className="label">Next gate</span><span className="value">{String(br?.next_gate || "—").replaceAll("_", " ")}</span></li>
                      </ul>
                    </div>
                  </div>

                  <div className="card">
                    <div className="card-header"><div className="card-title">Next Milestone</div></div>
                    <div className="card-body">
                      <ul className="bullets">{(br?.next_steps || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
                    </div>
                  </div>
                </div>
              </div>
            </>
          );
        }}
      </ResultGate>
    </>
  );
}
