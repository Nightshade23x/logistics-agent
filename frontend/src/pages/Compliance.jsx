import Badge from "../components/Badge.jsx";
import ResultGate from "../components/ResultGate.jsx";
import { cleanText, formatValue, groupItems, humanizeKey, uniq } from "../utils/displayFormat.js";

function arrayValue(value) {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  return [value];
}

function DocChecklist({ title, items, tone }) {
  const docs = uniq(arrayValue(items));

  if (!docs.length) return null;

  return (
    <div className="doc-checklist">
      <div className="section-subtitle">{title}</div>
      <div className="doc-pill-grid">
        {docs.map((doc, index) => (
          <label className={`doc-pill clickable ${tone || ""}`} key={`${doc}-${index}`}>
            <input type="checkbox" />
            <span>{humanizeKey(doc)}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function ComplianceSummary({ result }) {
  const docs = result.document_requirements_advice || {};
  const readiness = result.trade_compliance_readiness || {};

  const stats = [
    ["Origin", readiness.origin_country || docs.origin_country || "Missing"],
    ["Destination", readiness.destination_country || docs.destination_country || "Not detected"],
    ["Incoterm", readiness.incoterm || docs.incoterm || "Not detected"],
    ["Documents missing", arrayValue(docs.missing_or_unconfirmed_documents || readiness.missing_information).length],
    ["Partner review", readiness.ready_for_partner_review ? "Ready" : "Not ready"]
  ];

  return (
    <div className="card compliance-summary-card">
      <div className="card-header">
        <div>
          <div className="card-title">Compliance readiness</div>
          <div className="section-muted">Route, document, and partner-review readiness.</div>
        </div>
        <Badge status={readiness.status || docs.status || "review_required"} />
      </div>
      <div className="card-body">
        <div className="smart-metric-grid">
          {stats.map(([label, value]) => (
            <div className="smart-metric" key={label}>
              <div className="smart-metric-label">{label}</div>
              <div className="smart-metric-value">{formatValue(value)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TradeTermsCard({ advice }) {
  if (!advice) return null;

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Trade terms</div>
        <Badge status={advice.status || "review_required"} />
      </div>
      <div className="card-body">
        <p className="section-summary">{cleanText(advice.summary || "Review trade terms before booking.")}</p>

        <div className="trade-term-box">
          <div className="section-subtitle">{advice.incoterm || "Incoterm"}</div>
          <ul className="compact-list">
            <li>Seller usually arranges main carriage under CIF.</li>
            <li>Seller normally arranges minimum insurance cover.</li>
            <li>Risk transfer can happen before final delivery, so confirm the exact transfer point.</li>
          </ul>
        </div>

        <DocChecklist title="Checks before booking" items={(advice.recommendations || []).concat(advice.warnings || [])} tone="review" />
      </div>
    </div>
  );
}

function SmallReadinessCard({ title, data, fields }) {
  if (!data) return null;

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">{title}</div>
        <Badge status={data.status || "review_required"} />
      </div>
      <div className="card-body">
        {data.summary && <p className="section-summary">{cleanText(data.summary)}</p>}
        <div className="preview-list-v2">
          {fields.map(([label, value]) => (
            <div className="preview-row-v2" key={label}>
              <span>{label}</span>
              <strong>{formatValue(value)}</strong>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ClarificationGroups({ questions }) {
  const list = arrayValue(questions);
  const groups = groupItems(list);

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Clarification questions</div>
        <span className="tab-count">{list.length}</span>
      </div>
      <div className="card-body">
        {list.length ? (
          <div className="grouped-list">
            {Object.entries(groups).map(([group, items]) => (
              <div className="grouped-list-block" key={group}>
                <div className="grouped-list-title">{group}</div>
                <ul className="compact-list">
                  {items.map((item, index) => <li key={index}>{humanizeKey(item)}</li>)}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <p className="empty-text">No open questions.</p>
        )}
      </div>
    </div>
  );
}

export default function Compliance() {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Compliance & Documents</div>
          <div className="page-subtitle">Document checklist, trade terms, insurance, and compliance readiness.</div>
        </div>
      </div>

      <ResultGate>
        {(result) => {
          const docs = result.document_requirements_advice || {};
          const readiness = result.trade_compliance_readiness || {};
          const landed = result.landed_cost_advice || {};

          return (
            <div className="content-grid">
              <div className="content-col">
                <ComplianceSummary result={result} />

                <div className="card">
                  <div className="card-header">
                    <div>
                      <div className="card-title">Document checklist</div>
                      <div className="section-muted">Prepare these before final compliance review.</div>
                    </div>
                    <Badge status={docs.status || "review_required"} />
                  </div>
                  <div className="card-body">
                    {docs.summary && <p className="section-summary">{cleanText(docs.summary)}</p>}
                    <DocChecklist title="Required documents" items={docs.required_documents} tone="missing" />
                    <DocChecklist title="Conditional documents" items={docs.conditional_documents} tone="review" />
                    <DocChecklist title="Missing or unconfirmed" items={docs.missing_or_unconfirmed_documents} tone="missing" />
                    <DocChecklist title="Recommendations" items={docs.recommendations} />
                  </div>
                </div>

                <div className="card">
                  <div className="card-header">
                    <div className="card-title">Trade compliance</div>
                    <Badge status={readiness.status || "review_required"} />
                  </div>
                  <div className="card-body">
                    {readiness.summary && <p className="section-summary">{cleanText(readiness.summary)}</p>}
                    <DocChecklist title="Missing information" items={readiness.missing_information} tone="missing" />
                    <DocChecklist title="Ready items" items={readiness.ready_items} />
                    <DocChecklist title="Cargo items" items={readiness.cargo_items_preview} />
                  </div>
                </div>
              </div>

              <div className="content-col">
                <TradeTermsCard advice={result.trade_terms_advice} />

                <SmallReadinessCard
                  title="Insurance"
                  data={result.insurance_advice}
                  fields={[
                    ["Recommendation", result.insurance_advice?.insurance_recommendation],
                    ["Incoterm", result.insurance_advice?.incoterm]
                  ]}
                />

                <SmallReadinessCard
                  title="Landed cost readiness"
                  data={landed}
                  fields={[
                    ["Status", landed.status],
                    ["Known subtotal", landed.estimated_subtotal_known_usd],
                    ["Missing inputs", arrayValue(landed.missing_cost_inputs).map(humanizeKey).join(", ") || "None"]
                  ]}
                />

                <ClarificationGroups questions={result.clarification_questions} />
              </div>
            </div>
          );
        }}
      </ResultGate>
    </>
  );
}
