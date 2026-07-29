import Badge from "../components/Badge.jsx";
import SectionCard from "../components/SectionCard.jsx";
import ResultGate from "../components/ResultGate.jsx";
import ExecutiveSummary from "../components/ExecutiveSummary.jsx";
import ViewControls from "../components/ViewControls.jsx";
import SimplePageGuide from "../components/SimplePageGuide.jsx";
import { useStore } from "../store.jsx";
import { humanizeKey, groupItems } from "../utils/displayFormat.js";

function SideInfoCard({ title, children, badge }) {
  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">{title}</div>
        {badge}
      </div>
      <div className="card-body">{children}</div>
    </div>
  );
}

function MissingInfoPanel({ items }) {
  const list = Array.isArray(items) ? items : [];
  const groups = groupItems(list);

  return (
    <SideInfoCard title="Missing information" badge={<span className="tab-count">{list.length}</span>}>
      {list.length ? (
        <div className="grouped-list">
          {Object.entries(groups).map(([group, groupItems]) => (
            <div className="grouped-list-block" key={group}>
              <div className="grouped-list-title">{group}</div>
              <ul className="compact-list">
                {groupItems.map((item, index) => (
                  <li key={`${item}-${index}`}>{humanizeKey(item)}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-text">Nothing missing.</p>
      )}
    </SideInfoCard>
  );
}

export default function Shipments() {
  const { userView } = useStore();
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">{userView === "simple" ? "Your shipping plan" : "Shipments"}</div>
          <div className="page-subtitle">{userView === "simple" ? "See what is ready, what still needs attention, and what to do next." : "Full shipment breakdown, readiness gate, missing inputs, and agent results."}</div>
        </div>
        <ViewControls compact />
      </div>
      <SimplePageGuide title="How to read this page" items={["Ready for first pass means the plan is useful for review.", "Ready to book means all required details and checks are complete.", "Missing information tells you exactly what to provide next."]}>Start with the shipment status and missing information. Technical validation and request metadata are available in Advanced view.</SimplePageGuide>

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
              {userView === "advanced" && <>
                <SideInfoCard title="Backend validation" badge={<Badge status={result.backend_validation?.response_contract_valid ? "clear" : "blocked"} />}>
                  <ul className="info-list"><li><span className="label">Contract valid</span><span className="value">{result.backend_validation?.response_contract_valid ? "Yes" : "No"}</span></li><li><span className="label">Errors</span><span className="value">{result.backend_validation?.response_contract_errors?.length || 0}</span></li><li><span className="label">Warnings</span><span className="value">{result.backend_validation?.response_contract_warnings?.length || 0}</span></li></ul>
                </SideInfoCard>
                <SideInfoCard title="Request metadata"><ul className="info-list"><li><span className="label">Type</span><span className="value">{humanizeKey(result.request_metadata?.request_type)}</span></li><li><span className="label">Served by</span><span className="value">{humanizeKey(result.request_metadata?.served_by)}</span></li><li><span className="label">Agents called</span><span className="value">{(result.agents_called || []).map(humanizeKey).join(", ")}</span></li></ul></SideInfoCard>
              </>}

              <MissingInfoPanel items={result.missing_information_preview} />
            </div>
          </div>
        )}
      </ResultGate>
    </>
  );
}
