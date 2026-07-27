import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api.js";
import Badge from "../components/Badge.jsx";
import AnswerCard from "../components/AnswerCard.jsx";
import NeedMoreInfoCard from "../components/NeedMoreInfoCard.jsx";
import { useStore } from "../store.jsx";
import { humanizeKey, humanizeStatus } from "../utils/displayFormat.js";

const SAMPLE_TEXT = "";

const SAMPLE_JSON = {
  items: [
    { name: "TV", quantity: 50 },
    { name: "Scooters", quantity: 5 },
    { name: "Ceramic tiles", quantity: 100 }
  ],
  destination_country: "USA",
  budget_usd: 13000
};

const QUICK_SAMPLES = [
  "Find suppliers for 1000 ceramic tiles and make a shipping plan from India to Germany using CIF. Budget 12000 USD.",
  "Ship 8 pallets of glass jars from India to USA using CIF. Each pallet is 1.2 m x 1.0 m x 1.5 m and weighs 180 kg. The cargo is fragile.",
  "Calculate landed cost for glass bottles from India to USA using CIF. Cargo value 15000 USD, freight quote 2200 USD, insurance premium 500 USD, duty rate 6 percent, VAT 7 percent, customs brokerage 300 USD, local delivery 650 USD.",
  "What documents are needed for lithium batteries shipped from China to Germany using DDP?"
];

function inferIntent(text) {
  const lower = String(text || "").toLowerCase();

  if (lower.includes("supplier") || lower.includes("buy") || lower.includes("source")) return "Shopping";
  if (lower.includes("landed cost") || lower.includes("budget") || lower.includes("freight quote")) return "Finance";
  if (lower.includes("document") || lower.includes("invoice") || lower.includes("packing list")) return "Documents";
  if (lower.includes("hs code") || lower.includes("duty") || lower.includes("fta")) return "Trader";
  if (lower.includes("ship") || lower.includes("container") || lower.includes("cbm") || lower.includes("pallet")) return "Logistics";

  return "General";
}

function detectTerm(text, pattern) {
  const match = String(text || "").match(pattern);
  return match ? match[1] : null;
}

function parsePreview(text) {
  const destination = detectTerm(text, /\bto\s+([A-Z][A-Za-z ]{1,30})(?:\s+using|\s+with|\.|,|$)/);
  const origin = detectTerm(text, /\bfrom\s+([A-Z][A-Za-z ]{1,30})(?:\s+to|\s+using|\s+with|\.|,|$)/);
  const incoterm = detectTerm(text, /\b(EXW|FOB|CIF|DAP|DDP|FCA|CFR)\b/i);
  const budget = detectTerm(text, /\bbudget\s*(?:is|of|:)?\s*([0-9,.]+\s*USD)/i);
  const cbm = detectTerm(text, /\b([0-9.]+\s*CBM)\b/i);
  const weight = detectTerm(text, /\b([0-9,.]+\s*kg)\b/i);

  return [
    ["Likely intent", inferIntent(text)],
    ["Origin", origin || "Not detected"],
    ["Destination", destination || "Not detected"],
    ["Incoterm", incoterm ? incoterm.toUpperCase() : "Not detected"],
    ["Budget", budget || "Not detected"],
    ["Cargo volume", cbm || "Not detected"],
    ["Weight", weight || "Not detected"]
  ];
}

function ResultDecisionStrip({ result, onBreakdown }) {
  if (!result) return null;

  return (
    <div className="decision-strip-v2">
      <div className="decision-strip-main">
        <div className="decision-mini">
          <div className="decision-mini-label">Decision</div>
          <div className="decision-mini-value">{humanizeStatus(result.decision || result.status)}</div>
        </div>

        <Badge status={result.status} />

        <span className="badge info">
          <span className="badge-dot" />
          Intent: {humanizeKey(result.detected_intent || "unknown")}
        </span>

        {(result.agents_called || []).slice(0, 4).map((agent) => (
          <span className="agent-chip" key={agent}>{humanizeKey(agent)}</span>
        ))}
      </div>

      <button className="btn btn-teal" onClick={onBreakdown}>
        View full breakdown
      </button>
    </div>
  );
}

const DASHBOARD_MODE_KEY = "meridian.dashboard.mode";
const DASHBOARD_TEXT_KEY = "meridian.dashboard.text";
const DASHBOARD_JSON_KEY = "meridian.dashboard.json";

function loadDashboardValue(key, fallback) {
  try {
    const saved = localStorage.getItem(key);

    return saved === null
      ? fallback
      : saved;

  } catch {
    return fallback;
  }
}


export default function Dashboard() {
  const { result, history, setResult, loadFromHistory, clearCurrent, clearAll } = useStore();
  const navigate = useNavigate();

  const [mode, setMode] = useState(() => loadDashboardValue(DASHBOARD_MODE_KEY, "text"));
  const [text, setText] = useState(() => loadDashboardValue(DASHBOARD_TEXT_KEY, ""));
  const [jsonText, setJsonText] = useState(() => loadDashboardValue(DASHBOARD_JSON_KEY, JSON.stringify(SAMPLE_JSON, null, 2)));
  const [files, setFiles] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showCurrentResult, setShowCurrentResult] = useState(() => Boolean(result));

  useEffect(() => {
    try {
      localStorage.setItem(
        DASHBOARD_MODE_KEY,
        mode
      );

      localStorage.setItem(
        DASHBOARD_TEXT_KEY,
        text
      );

      localStorage.setItem(
        DASHBOARD_JSON_KEY,
        jsonText
      );

    } catch {
      // Keep the app usable if browser storage is unavailable.
    }
  }, [mode, text, jsonText]);


  useEffect(() => {
    if (result) {
      setShowCurrentResult(true);
    }
  }, [result]);


  function resetDashboardDraft() {
    setMode("text");
    setText("");
    setJsonText("");
    setFiles(null);
    setError(null);
    setShowCurrentResult(false);
  }


  function clearCurrentWorkspace() {
    clearCurrent();
    resetDashboardDraft();
  }


  function clearEverything() {
    clearAll();
    resetDashboardDraft();
  }


  async function submit() {
    setError(null);
    setLoading(true);

    try {
      let payload;

      if (mode === "text") {
        payload = await api.requestText(text);
      } else if (mode === "json") {
        payload = await api.requestJson(JSON.parse(jsonText));
      } else {
        payload = await api.requestDocuments(files || []);
      }

      setShowCurrentResult(true);
      setResult(payload, {
        label: mode === "text" ? text.slice(0, 60) : mode === "json" ? "JSON request" : "Document upload"
      });
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  const previewRows = parsePreview(text);

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-subtitle">Submit a sourcing, logistics, finance, or document request and let the agent pipeline prepare a first-pass plan.</div>
        </div>
      </div>

      <div className="request-panel request-panel-v2">
        <div className="card request-builder-v2">
          <div className="card-header">
            <div>
              <div className="card-title">New trade request</div>
              <div className="section-muted">Describe what you want to source, ship, calculate, or check.</div>
            </div>
          </div>

          <div className="card-body">
            <div className="segment">
              {["text", "json", "documents"].map((m) => (
                <button key={m} className={mode === m ? "active" : ""} onClick={() => setMode(m)}>
                  {m === "text" ? "Free text" : m === "json" ? "Structured JSON" : "Documents"}
                </button>
              ))}
            </div>

            {mode === "text" && (
              <div className="form-group">
                <label className="form-label">Request</label>
                <textarea
                  className="form-textarea request-textarea-v2"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Example: Find suppliers for 1000 ceramic tiles from India to Germany using CIF. Budget 12000 USD."
                />

                <div className="helper-text">
                  Include product, quantity, origin, destination, incoterm, budget, CBM, weight, and cost inputs if known.
                </div>

                <div className="sample-label">Try an example</div>
                <div className="example-card-grid">
                  {QUICK_SAMPLES.map((sample, index) => (
                    <button type="button" className="example-card" key={sample} onClick={() => setText(sample)}>
                      <span className="example-card-kicker">Example {index + 1}</span>
                      <span className="example-card-text">{sample}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {mode === "json" && (
              <div className="form-group">
                <label className="form-label">Structured JSON</label>
                <textarea className="form-textarea mono" value={jsonText} onChange={(e) => setJsonText(e.target.value)} />
              </div>
            )}

            {mode === "documents" && (
              <div className="form-group">
                <label className="form-label">Upload trade documents</label>
                <input type="file" multiple onChange={(e) => setFiles(e.target.files)} />
                <div className="helper-text">Invoice, packing list, bill of lading, certificate of origin, PDF, DOCX, or TXT.</div>
              </div>
            )}

            {error && <div className="error-banner">{error}</div>}

            <div className="request-action-row-v2" style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginTop: 12 }}>
              <button className="btn btn-primary run-request-v2" onClick={submit} disabled={loading}>
                {loading && <span className="spinner" />}
                {loading ? "Running agents..." : "Run agent pipeline"}
              </button>

              <button className="btn" onClick={clearCurrentWorkspace}>
                Clear current
              </button>

              <button className="btn" onClick={clearEverything}>
                Clear all
              </button>
            </div>
          </div>
        </div>

        <div className="card request-preview-v2">
          <div className="card-header">
            <div>
              <div className="card-title">Parsed preview</div>
              <div className="section-muted">Quick check before sending.</div>
            </div>
          </div>
          <div className="card-body">
            {mode === "text" && (
              <div className="preview-list-v2">
                {previewRows.map(([label, value]) => (
                  <div className="preview-row-v2" key={label}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </div>
            )}
            {mode === "json" && <pre className="json-view">{jsonText}</pre>}
            {mode === "documents" && (
              <p style={{ color: "var(--text-secondary)" }}>
                {files && files.length ? Array.from(files).map((f) => f.name).join(", ") : "No files selected."}
              </p>
            )}
          </div>
        </div>
      </div>

      <ResultDecisionStrip result={showCurrentResult ? result : null} onBreakdown={() => navigate("/shipments")} />

      {showCurrentResult && result && <AnswerCard result={result} />}
      {showCurrentResult && result && <NeedMoreInfoCard result={result} originalText={text} onResult={(payload, meta) => { setShowCurrentResult(true); setResult(payload, meta); }} />}

      <div className="recent-requests-dropdown">
        <details>
          <summary>
            <span>Recent Requests ({history.length})</span>
            <span className="recent-requests-summary-help">Show or hide request history</span>
          </summary>

          <div className="card">
            <div className="card-body tight">
              {history.length === 0 ? (
                <div className="empty-state">
                  <p>No requests yet. Run one above to see it here.</p>
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
                    <div className="shipment-row" key={h.id} onClick={() => { loadFromHistory(h.id); setShowCurrentResult(true); navigate("/shipments"); }}>
                      <div className="shipment-id">{String(h.label).slice(0, 64)}</div>
                      <div className="shipment-route">{humanizeKey(h.requestType)}</div>
                      <div className="shipment-route">{humanizeKey(h.detectedIntent)}</div>
                      <div><Badge status={h.status ?? h.decision} /></div>
                      <div className="shipment-route">{new Date(h.timestamp).toLocaleTimeString()}</div>
                      <div>Go</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </details>
      </div>
    </>
  );
}
