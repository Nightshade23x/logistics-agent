import Badge from "../components/Badge.jsx";
import AnswerCard from "../components/AnswerCard.jsx";
import ResultGate from "../components/ResultGate.jsx";
import ViewControls from "../components/ViewControls.jsx";
import SimplePageGuide from "../components/SimplePageGuide.jsx";
import { useStore } from "../store.jsx";
import { cleanText, formatValue, groupItems, humanizeKey, uniq } from "../utils/displayFormat.js";

import { normalizeFinalReportPayload } from "../utils/finalReportPayload";
function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(normalizeFinalReportPayload(data), null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function ChecklistCard({ title, items, priority, grouped }) {
  const list = uniq(Array.isArray(items) ? items : []);

  if (!list.length) return null;

  if (grouped) {
    const groups = groupItems(list);

    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title">{title}</div>
          <span className="tab-count">{list.length}</span>
        </div>
        <div className="card-body grouped-list">
          {Object.entries(groups).map(([group, groupItems]) => (
            <div className="grouped-list-block" key={group}>
              <div className="grouped-list-title">{group}</div>
              <ul className="compact-list">
                {groupItems.map((item, index) => <li key={index}>{humanizeKey(item)}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">{title}</div>
        <span className="tab-count">{list.length}</span>
      </div>
      <div className="card-body">
        <div className="report-checklist">
          {list.map((item, index) => (
            <label className="report-check-row" key={`${item}-${index}`}>
              <input type="checkbox" />
              <span>{humanizeKey(cleanText(item))}</span>
              <em>{priority || "med"}</em>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}

function BookingReadiness({ br }) {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Booking readiness</div>
        <Badge status={br?.status} />
      </div>
      <div className="card-body">
        <div className="booking-score-card">
          <div className="smart-metric-label">Score</div>
          <div className="booking-score-value">{br?.score ?? 0}<span>/100</span></div>
        </div>
        <div className="preview-list-v2">
          <div className="preview-row-v2"><span>Ready first pass</span><strong>{formatValue(br?.ready_for_first_pass)}</strong></div>
          <div className="preview-row-v2"><span>Ready to book</span><strong>{formatValue(br?.ready_for_booking)}</strong></div>
          <div className="preview-row-v2"><span>Next gate</span><strong>{humanizeKey(br?.next_gate || "Review")}</strong></div>
        </div>
      </div>
    </div>
  );
}

export default function Reports() {
  const { userView } = useStore();
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">{userView === "simple" ? "Your final checklist" : "Reports"}</div>
          <div className="page-subtitle">{userView === "simple" ? "Review the answer, missing details, next actions, and booking readiness in one place." : "Final answer, grouped action plan, missing information, and booking readiness."}</div>
        </div>
        <div className="page-actions"><ViewControls compact />{userView === "advanced" && <button className="btn" onClick={() => downloadJson(window.__lastResult || {}, "shipment-report.json")}>Export technical JSON</button>}</div>
      </div>
      <SimplePageGuide title="Work from top to bottom" items={["Read the final answer first.", "Complete high-priority missing information and immediate actions.", "Use booking readiness to see whether the shipment can move to a carrier booking."]} />

      <ResultGate>
        {(result) => {
          window.__lastResult = result;
          const ap = result.action_plan || {};
          const br = result.booking_readiness || {};

          return (
            <div className="content-grid">
              <div className="content-col">
                <AnswerCard result={result} />
                <ChecklistCard title="Missing information" items={result.missing_information_preview} priority="high" grouped />
                <ChecklistCard title="Immediate actions" items={ap.immediate_actions} priority="high" />
                <ChecklistCard title="Before booking" items={ap.before_booking} priority="med" />
                <ChecklistCard title="Partner steps" items={ap.partner_steps} priority="low" />
                <ChecklistCard title="Open questions" items={ap.user_questions} priority="med" grouped />
              </div>

              <div className="content-col">
                <BookingReadiness br={br} />

                <div className="card">
                  <div className="card-header">
                    <div className="card-title">Next milestone</div>
                    <Badge status={br.status || result.status} />
                  </div>
                  <div className="card-body">
                    <p className="section-summary">{cleanText(br.summary || ap.summary || "Review the grouped checklist before booking.")}</p>
                    <ul className="compact-list">
                      {(br.next_steps || ap.ready_to_continue || []).slice(0, 6).map((step, index) => (
                        <li key={index}>{humanizeKey(step)}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          );
        }}
      </ResultGate>
    </>
  );
}
