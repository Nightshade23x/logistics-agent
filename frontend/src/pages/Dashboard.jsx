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
  "Ship 10 crates of ceramic tiles from India to Germany using CIF. Each crate is 1.2 m x 1.0 m x 0.8 m and weighs 250 kg. The cargo is fragile and stackable.",
  "Ship 8 pallets of glass jars from India to USA using CIF. Each pallet is 1.2 m x 1.0 m x 1.5 m and weighs 180 kg. The cargo is fragile and non-stackable.",
  "Calculate landed cost for glass bottles from India to USA using CIF. Procurement value 15000 USD, freight quote 2200 USD, insurance premium 500 USD, duty rate 6 percent, import tax 7 percent, customs brokerage 300 USD, and local delivery 650 USD.",
  "List the required shipping and compliance documents for 20 lithium-ion battery packs sent by air from China to Germany under DDP. Each pack weighs 25 kg."
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
const USER_VIEW_KEY = "meridian.user.view";
const FONT_SCALE_KEY = "meridian.user.fontScale";
const USER_FRIENDLY_VIEW_V37 = true;

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
  const [userView, setUserView] = useState(() => loadDashboardValue(USER_VIEW_KEY, "simple"));
  const [fontScale, setFontScale] = useState(() => loadDashboardValue(FONT_SCALE_KEY, "normal"));

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
    try {
      localStorage.setItem(USER_VIEW_KEY, userView);
      localStorage.setItem(FONT_SCALE_KEY, fontScale);
    } catch {
      // Keep the app usable if browser storage is unavailable.
    }
    document.documentElement.dataset.fontScale = fontScale;
    if (userView === "simple" && mode !== "text") {
      setMode("text");
    }
  }, [userView, fontScale, mode]);


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
          <div className="page-title">Shipping assistant</div>
          <div className="page-subtitle">Describe what you need in your own words. The system will calculate, explain, and show what must happen next.</div>
        </div>
        <div className="accessibility-controls" aria-label="Display preferences">
          <div className="view-toggle" role="group" aria-label="Information detail">
            <button type="button" className={userView === "simple" ? "active" : ""} aria-pressed={userView === "simple"} onClick={() => setUserView("simple")}>Simple view</button>
            <button type="button" className={userView === "advanced" ? "active" : ""} aria-pressed={userView === "advanced"} onClick={() => setUserView("advanced")}>Advanced view</button>
          </div>
          <div className="font-scale-controls" role="group" aria-label="Text size">
            <span>Text size</span>
            {["compact", "normal", "large"].map((value, index) => (
              <button type="button" key={value} className={fontScale === value ? "active" : ""} aria-pressed={fontScale === value} aria-label={`${value} text`} onClick={() => setFontScale(value)}>{index === 0 ? "A−" : index === 1 ? "A" : "A+"}</button>
            ))}
          </div>
        </div>
      </div>

      {userView === "simple" && (
        <section className="friendly-steps" aria-label="How to use the shipping assistant">
          <div><span>1</span><strong>Describe</strong><p>Tell us what is moving and where it is going.</p></div>
          <div><span>2</span><strong>Review</strong><p>Check the details the system understood.</p></div>
          <div><span>3</span><strong>Complete</strong><p>Answer only the missing questions.</p></div>
          <div><span>4</span><strong>Decide</strong><p>See costs, risks, documents, and next steps.</p></div>
        </section>
      )}

      <div className="request-panel request-panel-v2">
        <div className="card request-builder-v2">
          <div className="card-header">
            <div>
              <div className="card-title">{userView === "simple" ? "What do you need help with?" : "New trade request"}</div>
              <div className="section-muted">{userView === "simple" ? "Use normal sentences. You do not need to know logistics terms." : "Describe what you want to source, ship, calculate, or check."}</div>
            </div>
          </div>

          <div className="card-body">
            {userView === "advanced" && (
              <div className="segment" role="tablist" aria-label="Request input type">
                {["text", "json", "documents"].map((m) => (
                  <button type="button" role="tab" aria-selected={mode === m} key={m} className={mode === m ? "active" : ""} onClick={() => setMode(m)}>
                    {m === "text" ? "Free text" : m === "json" ? "Structured JSON" : "Documents"}
                  </button>
                ))}
              </div>
            )}

            {mode === "text" && (
              <div className="form-group">
                <label className="form-label" htmlFor="shipping-request">{userView === "simple" ? "Tell us what you want to do" : "Request"}</label>
                <textarea
                  id="shipping-request"
                  className="form-textarea request-textarea-v2"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  aria-describedby="shipping-request-help"
                  placeholder={userView === "simple" ? "Example: Ship 10 boxes from India to Germany. Each box weighs 25 kg and the contents are fragile." : "Example: Find suppliers for 1000 ceramic tiles from India to Germany using CIF. Budget 12000 USD."}
                />

                <div className="helper-text" id="shipping-request-help">
                  {userView === "simple" ? "Useful details include: what it is, how many, where it starts, where it goes, size, weight, and whether it is fragile or dangerous." : "Include product, quantity, origin, destination, incoterm, budget, CBM, weight, and cost inputs if known."}
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

            {error && <div className="error-banner" role="alert">{error}</div>}
            <div className="sr-only" aria-live="polite">{loading ? "The agents are preparing your result." : ""}</div>

            <div className="request-action-row-v2" style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", marginTop: 12 }}>
              <button className="btn btn-primary run-request-v2" type="button" onClick={submit} disabled={loading || (mode === "text" && !text.trim())}>
                {loading && <span className="spinner" />}
                {loading ? "Preparing your result..." : userView === "simple" ? "Create my shipping plan" : "Run agent pipeline"}
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
              <div className="card-title">{userView === "simple" ? "What we understood" : "Parsed preview"}</div>
              <div className="section-muted">{userView === "simple" ? "Check these details before creating the plan." : "Quick check before sending."}</div>
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

      {showCurrentResult && result && userView === "simple" && (
        <div className="result-language-guide" role="note">
          <strong>How to read this result</strong>
          <span><b>Ready for planning</b> means the information is useful for a first review.</span>
          <span><b>Ready to book</b> means the required details and checks are complete. These are not the same.</span>
        </div>
      )}

      {showCurrentResult && result && <AnswerCard result={result} />}
      {showCurrentResult && result && (
        <NeedMoreInfoCard
          result={result}
          originalText={text}
          onResult={(payload, meta) => {
            setShowCurrentResult(true);
            setResult(payload, meta);
            // MISSING_INFO_REQUEST_VISIBILITY_V35
            setText(payload?.request_metadata?.input_source || text);
          }}
        />
      )}

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
