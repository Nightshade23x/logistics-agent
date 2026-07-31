import Badge from "./Badge.jsx";

function prettyKey(key) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const SKIP_KEYS = new Set(["applicable", "status", "summary"]);

export default function AdvisorCard({ title, data }) {
  if (!data) return null;
  if (data.applicable === false) {
    return (
      <div className="card">
        <div className="card-header">
          <div className="card-title">{title}</div>
          <Badge status="not_applicable" />
        </div>
        <div className="card-body">
          <p style={{ color: "var(--text-muted)" }}>{data.summary || "Not applicable to this request."}</p>
        </div>
      </div>
    );
  }

  const listFields = [];
  const scalarFields = [];
  const dictFields = [];

  Object.entries(data).forEach(([key, value]) => {
    if (SKIP_KEYS.has(key)) return;
    if (Array.isArray(value)) {
      if (value.length) listFields.push([key, value]);
    } else if (value && typeof value === "object") {
      if (Object.keys(value).length) dictFields.push([key, value]);
    } else if (value !== null && value !== undefined && value !== "") {
      scalarFields.push([key, value]);
    }
  });

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">{title}</div>
        <Badge status={data.status} />
      </div>
      <div className="card-body">
        {data.summary && <p style={{ color: "var(--text-secondary)", marginBottom: 12 }}>{data.summary}</p>}

        {(scalarFields.length > 0 || dictFields.length > 0) && (
          <ul className="info-list" style={{ marginBottom: listFields.length ? 12 : 0 }}>
            {scalarFields.map(([k, v]) => (
              <li key={k}>
                <span className="label">{prettyKey(k)}</span>
                <span className="value">{String(v)}</span>
              </li>
            ))}
            {dictFields.map(([k, v]) => (
              <li key={k}>
                <span className="label">{prettyKey(k)}</span>
                <span className="value">{Object.entries(v).map(([kk, vv]) => `${kk}: ${vv}`).join(", ")}</span>
              </li>
            ))}
          </ul>
        )}

        {listFields.map(([key, values], idx) => (
          <div key={key} style={{ marginTop: idx > 0 ? 12 : 0 }}>
            <div className="form-label">{prettyKey(key)}</div>
            <ul className="bullets">
              {values.map((v, i) => (
                <li key={i}>{typeof v === "object" ? JSON.stringify(v) : String(v)}</li>
              ))}
            </ul>
          </div>
        ))}

        {listFields.length === 0 && scalarFields.length === 0 && dictFields.length === 0 && !data.summary && (
          <p style={{ color: "var(--text-muted)" }}>No data returned.</p>
        )}
      </div>
    </div>
  );
}
