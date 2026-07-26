import Badge from "./Badge.jsx";
import { cleanText, formatValue, groupItems, humanizeKey, uniq } from "../utils/displayFormat.js";

function isEmpty(value) {
  return value === null || value === undefined || value === "" || (Array.isArray(value) && value.length === 0);
}

function MetricGrid({ metrics }) {
  const entries = Object.entries(metrics || {}).filter(function (entry) {
    return !isEmpty(entry[1]);
  });

  if (!entries.length) return null;

  return (
    <div className="smart-metric-grid">
      {entries.slice(0, 8).map(function ([key, value]) {
        return (
          <div className="smart-metric" key={key}>
            <div className="smart-metric-label">{humanizeKey(key)}</div>
            <div className="smart-metric-value">{formatValue(value)}</div>
          </div>
        );
      })}
    </div>
  );
}

function SupplierCards({ items }) {
  const suppliers = uniq(items || []).filter(function (item) {
    return String(item || "").toLowerCase().includes("supplier") || String(item || "").toLowerCase().includes("shortlist");
  });

  if (!suppliers.length) return null;

  return (
    <div className="supplier-card-grid">
      {suppliers.slice(0, 6).map(function (item, index) {
        const text = cleanText(String(item).replace(/^Shortlist:\s*/i, ""));
        const parts = text.split(":");
        const title = parts[0] || `Supplier option ${index + 1}`;
        const detail = parts.slice(1).join(":").trim();

        return (
          <div className="supplier-mini-card" key={`${title}-${index}`}>
            <div className="supplier-mini-title">{title}</div>
            {detail && <div className="supplier-mini-detail">{detail}</div>}
          </div>
        );
      })}
    </div>
  );
}

function GroupedList({ title, items }) {
  const cleaned = uniq(items || []).map(function (item) {
    return cleanText(item);
  }).filter(Boolean);

  if (!cleaned.length) return null;

  if (title && title.toLowerCase().includes("missing")) {
    const groups = groupItems(cleaned);
    const groupEntries = Object.entries(groups);

    return (
      <div className="grouped-list">
        {groupEntries.map(function ([groupName, groupItems]) {
          return (
            <div className="grouped-list-block" key={groupName}>
              <div className="grouped-list-title">{groupName}</div>
              <ul className="compact-list">
                {groupItems.map(function (item, index) {
                  return <li key={`${item}-${index}`}>{humanizeKey(item)}</li>;
                })}
              </ul>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <ul className="compact-list">
      {cleaned.map(function (item, index) {
        return <li key={`${item}-${index}`}>{humanizeKey(item)}</li>;
      })}
    </ul>
  );
}

function Checklist({ title, items, tone }) {
  const cleaned = uniq(items || []).map(function (item) {
    return cleanText(item);
  }).filter(Boolean);

  if (!cleaned.length) return null;

  return (
    <div className="checklist-block">
      {title && <div className="section-subtitle">{title}</div>}
      <div className="checklist-grid">
        {cleaned.map(function (item, index) {
          return (
            <div className={`checklist-pill ${tone || ""}`} key={`${item}-${index}`}>
              <span className="checklist-box" />
              <span>{humanizeKey(item)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function SectionCard({ section }) {
  if (!section) return null;

  const metrics = section.metrics && Object.keys(section.metrics).length ? section.metrics : null;
  const bullets = Array.isArray(section.bullets) ? section.bullets : [];
  const actions = Array.isArray(section.actions) ? section.actions : [];
  const title = section.title || "Section";
  const lowerTitle = title.toLowerCase();

  const supplierItems = bullets.concat(actions).filter(function (item) {
    const text = String(item || "").toLowerCase();
    return text.includes("supplier") || text.includes("shortlist");
  });

  const normalBullets = bullets.filter(function (item) {
    return supplierItems.indexOf(item) < 0;
  });

  const isLong = normalBullets.length + actions.length > 8 || lowerTitle.includes("costs") || lowerTitle.includes("partner");

  const body = (
    <>
      {section.summary && <p className="section-summary">{cleanText(section.summary)}</p>}

      <MetricGrid metrics={metrics} />

      <SupplierCards items={supplierItems} />

      {section.required_documents && <Checklist title="Required documents" items={section.required_documents} tone="missing" />}
      {section.conditional_documents && <Checklist title="Conditional documents" items={section.conditional_documents} tone="review" />}
      {section.missing_or_unconfirmed_documents && <Checklist title="Missing or unconfirmed documents" items={section.missing_or_unconfirmed_documents} tone="missing" />}

      {normalBullets.length > 0 && (
        <div className="section-block">
          <div className="section-subtitle">{lowerTitle.includes("missing") ? "Missing details" : "Notes"}</div>
          <GroupedList title={title} items={normalBullets} />
        </div>
      )}

      {actions.length > 0 && (
        <div className="section-block">
          <div className="section-subtitle">Suggested actions</div>
          <GroupedList title="Actions" items={actions} />
        </div>
      )}
    </>
  );

  return (
    <div className="card smart-section-card">
      <div className="card-header">
        <div className="card-title">{title}</div>
        <Badge status={section.status} />
      </div>

      <div className="card-body">
        {isLong ? (
          <details className="smart-details" open={lowerTitle.includes("summary") || lowerTitle.includes("snapshot")}>
            <summary>Show section details</summary>
            <div className="smart-details-body">{body}</div>
          </details>
        ) : (
          body
        )}
      </div>
    </div>
  );
}
