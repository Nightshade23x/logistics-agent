import Badge from "./Badge.jsx";

function prettyKey(key) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function prettyValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

// Renders one entry of `ui_sections` — the backend already ships title,
// status, summary, metrics (dict), bullets (list), actions (list), so this
// component is generic and works for every section the backend adds later.
export default function SectionCard({ section }) {
  const metrics = section.metrics && Object.keys(section.metrics).length ? section.metrics : null;

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">{section.title || section.section_id}</div>
        <Badge status={section.status} />
      </div>
      <div className="card-body">
        {section.summary && (
          <p style={{ color: "var(--text-secondary)", marginBottom: metrics || section.bullets?.length || section.actions?.length ? 14 : 0 }}>
            {section.summary}
          </p>
        )}

        {metrics && (
          <ul className="info-list" style={{ marginBottom: section.bullets?.length || section.actions?.length ? 10 : 0 }}>
            {Object.entries(metrics).map(([k, v]) => (
              <li key={k}>
                <span className="label">{prettyKey(k)}</span>
                <span className="value">{prettyValue(v)}</span>
              </li>
            ))}
          </ul>
        )}

        {Array.isArray(section.bullets) && section.bullets.length > 0 && (
          <>
            <div className="form-label" style={{ marginTop: 4 }}>Notes</div>
            <ul className="bullets" style={{ marginBottom: section.actions?.length ? 12 : 0 }}>
              {section.bullets.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          </>
        )}

        {Array.isArray(section.actions) && section.actions.length > 0 && (
          <>
            <div className="form-label">Suggested Actions</div>
            <ul className="bullets">
              {section.actions.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </>
        )}

        {!section.summary && !metrics && !section.bullets?.length && !section.actions?.length && (
          <p style={{ color: "var(--text-muted)" }}>No data returned for this section.</p>
        )}
      </div>
    </div>
  );
}
