import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useStore } from "../store.jsx";
import Badge from "../components/Badge.jsx";

const SAMPLE_TEXT =
  "I need 50 TVs, 5 scooters, and 100 ceramic tiles. Prefer suppliers from India. Avoid China. Budget 13000 USD.";

const SAMPLE_JSON = {
  request_id: "SHOP-REQ-001",
  customer: "Demo Customer",
  destination_country: "USA",
  preferred_currency: "USD",
  items: [
    { name: "TVs", quantity: 50 },
    { name: "Scooters", quantity: 5 },
    { name: "Ceramic tiles", quantity: 100 },
  ],
};

const QUICK_SAMPLES = [
  "50 TVs and 5 scooters to USA, budget 13000 USD",
  "20ft container of hazardous chemicals, destination Germany",
  "100 ceramic tiles, oversized multi-container shipment",
  "Perishable produce, 500kg, destination UK",
];

export default function Dashboard() {
  const { result, history, setResult, loadFromHistory, clearAll } = useStore();
  const navigate = useNavigate();

  const [mode, setMode] = useState("text");
  const [text, setText] = useState(SAMPLE_TEXT);
  const [jsonText, setJsonText] = useState(JSON.stringify(SAMPLE_JSON, null, 2));
  const [files, setFiles] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function submit() {
    setError(null);
    setLoading(true);
    try {
      let payload;
      if (mode === "text") {
        payload = await api.requestText(text);
      } else if (mode === "json") {
        let parsed;
        try {
          parsed = JSON.parse(jsonText);
        } catch (e) {
          throw new Error("The JSON request body is not valid JSON: " + e.message);
        }
        payload = await api.requestJson(parsed);
      } else {
        if (!files || files.length === 0) throw new Error("Choose at least one document to upload.");
        payload = await api.requestDocuments(files);
      }
      setResult(payload, { label: mode === "text" ? text.slice(0, 60) : mode === "json" ? "JSON request" : "Document upload" });
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-subtitle">
            Submit a request to the Logistics Agent pipeline — routes through Shopping, Logistics,
            Document AI, and Partner Review automatically.
          </div>
        </div>
        <div className="page-actions">
          <button className="btn" onClick={clearAll} disabled={!result && history.length === 0}>
            Clear history
          </button>
        </div>
      </div>

      <div className="request-panel">
        <div className="card">
          <div className="card-header">
            <div className="card-title">Request Builder</div>
          </div>
          <div className="card-body">
            <div className="segment">
              {["text", "json", "documents"].map((m) => (
                <button key={m} className={mode === m ? "active" : ""} onClick={() => setMode(m)}>
                  {m === "text" ? "Free Text" : m === "json" ? "Structured JSON" : "Documents"}
                </button>
              ))}
            </div>

            {mode === "text" && (
              <div className="form-group">
                <label className="form-label">User Request</label>
                <textarea className="form-textarea" value={text} onChange={(e) => setText(e.target.value)} />
                <div className="helper-text">
                  Routed by keyword scoring to shopping / logistics / document intent (see agent_router.py).
                </div>
                <div className="quick-samples">
                  {QUICK_SAMPLES.map((s) => (
                    <span key={s} className="chip" onClick={() => setText(s)}>
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {mode === "json" && (
              <div className="form-group">
                <label className="form-label">Structured Request (shopping or logistics-style JSON)</label>
                <textarea
                  className="form-textarea mono"
                  style={{ minHeight: 220 }}
                  value={jsonText}
                  onChange={(e) => setJsonText(e.target.value)}
                />
                <div className="helper-text">
                  Sent to process_json_file_request — intent is inferred from the JSON shape.
                </div>
              </div>
            )}

            {mode === "documents" && (
              <div className="form-group">
                <label className="form-label">Trade Documents</label>
                <input
                  className="form-input"
                  type="file"
                  multiple
                  onChange={(e) => setFiles(e.target.files)}
                />
                <div className="helper-text">
                  Invoice, packing list, bill of lading, certificate of origin (.txt / .pdf / .docx).
                </div>
              </div>
            )}

            {error && <div className="error-banner">{error}</div>}

            <button className="btn btn-primary" onClick={submit} disabled={loading}>
              {loading && <span className="spinner" />}
              {loading ? "Running pipeline…" : "Run Request"}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <div className="card-title">Request Preview</div>
          </div>
          <div className="card-body">
            {mode === "text" && <p style={{ color: "var(--text-secondary)" }}>{text || "—"}</p>}
            {mode === "json" && <pre className="json-view">{jsonText}</pre>}
            {mode === "documents" && (
              <p style={{ color: "var(--text-secondary)" }}>
                {files && files.length ? Array.from(files).map((f) => f.name).join(", ") : "No files selected."}
              </p>
            )}
          </div>
        </div>
      </div>

      {result && (
        <div className="results-header">
          <div className="results-header-left">
            <div className="verdict-block">
              <div className="verdict-label">Decision</div>
              <div className="verdict-value">{result.decision}</div>
            </div>
            <Badge status={result.status} />
            <span className="badge info">
              <span className="badge-dot" /> intent: {result.detected_intent}
            </span>
          </div>
          <button className="btn btn-teal" onClick={() => navigate("/shipments")}>
            View full breakdown →
          </button>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <div className="card-title">Recent Requests</div>
        </div>
        <div className="card-body tight">
          {history.length === 0 ? (
            <div className="empty-state">
              <div className="icon">🗂️</div>
              <p>No requests yet — run one above to see it here.</p>
            </div>
          ) : (
            <div>
              <div className="shipment-row header">
                <div>Request</div>
                <div>Type</div>
                <div>Intent</div>
                <div>Decision</div>
                <div>Time</div>
                <div></div>
              </div>
              {history.map((h) => (
                <div className="shipment-row" key={h.id} onClick={() => { loadFromHistory(h.id); navigate("/shipments"); }}>
                  <div className="shipment-id">{String(h.label).slice(0, 48)}</div>
                  <div className="shipment-route">{h.requestType}</div>
                  <div className="shipment-route">{h.detectedIntent}</div>
                  <div><Badge status={h.decision} /></div>
                  <div className="shipment-route">{new Date(h.timestamp).toLocaleTimeString()}</div>
                  <div>→</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
