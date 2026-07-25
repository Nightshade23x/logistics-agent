import { useState } from "react";
import Badge from "../components/Badge.jsx";
import ResultGate from "../components/ResultGate.jsx";
import { api } from "../api.js";

const PARTNERS = [
  { key: "risk", name: "Risk Agent", icon: "⚠️" },
  { key: "compliance", name: "Compliance Agent", icon: "✅" },
  { key: "trader", name: "Trader Agent", icon: "💱" },
  { key: "finance", name: "Finance Agent", icon: "💰" },
];

const ENDPOINTS = {
  logistics: {
    label: "Logistics Agent",
    route: "/api/agents/logistics",
    sample: JSON.stringify({ items: [{ name: "TV", quantity: 10, length_m: 1.2, width_m: 0.2, height_m: 0.8, weight_kg: 12, fragile: true }] }, null, 2),
    call: (parsed) => api.agentLogistics(parsed.items, parsed.shipment_context || null),
  },
  document: {
    label: "Document Agent",
    route: "/api/agents/document",
    sample: JSON.stringify({ text: "INVOICE\nSupplier: Acme Traders\nBuyer: Demo Customer\nTotal Value: 5000 USD" }, null, 2),
    call: (parsed) => api.agentDocument(parsed.text),
  },
  "partner-review": {
    label: "Partner Review Service",
    route: "/api/agents/partner-review",
    sample: JSON.stringify({ payload: { items: [{ name: "TVs", quantity: 50 }], total_value: 12250 }, request_id: "PLAYGROUND-1" }, null, 2),
    call: (parsed) => api.agentPartnerReview(parsed.payload, parsed.request_id || null),
  },
  intent: {
    label: "Intent Classifier",
    route: "/api/agents/intent",
    sample: JSON.stringify({ text: "I need a 20ft container quote for ceramic tiles" }, null, 2),
    call: (parsed) => api.agentIntent(parsed.text),
  },
};

function Playground() {
  const [tab, setTab] = useState("logistics");
  const [input, setInput] = useState(ENDPOINTS.logistics.sample);
  const [output, setOutput] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  function switchTab(key) {
    setTab(key);
    setInput(ENDPOINTS[key].sample);
    setOutput(null);
    setError(null);
  }

  async function run() {
    setError(null);
    setLoading(true);
    setOutput(null);
    try {
      const parsed = JSON.parse(input);
      const res = await ENDPOINTS[tab].call(parsed);
      setOutput(res);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">Agent Playground</div>
      </div>
      <div className="card-body">
        <div className="tabs">
          {Object.entries(ENDPOINTS).map(([key, cfg]) => (
            <button key={key} className={`tab${tab === key ? " active" : ""}`} onClick={() => switchTab(key)}>
              {cfg.label}
            </button>
          ))}
        </div>
        <p style={{ color: "var(--text-secondary)", marginBottom: 10 }}>
          <span className="mono">POST {ENDPOINTS[tab].route}</span>
        </p>
        <textarea className="form-textarea mono" style={{ minHeight: 160 }} value={input} onChange={(e) => setInput(e.target.value)} />
        {error && <div className="error-banner" style={{ marginTop: 10 }}>{error}</div>}
        <button className="btn btn-primary" style={{ marginTop: 10 }} onClick={run} disabled={loading}>
          {loading && <span className="spinner" />}
          {loading ? "Calling agent…" : "Send"}
        </button>
        {output && (
          <>
            <div className="form-label" style={{ marginTop: 16 }}>Response</div>
            <pre className="json-view">{JSON.stringify(output, null, 2)}</pre>
          </>
        )}
      </div>
    </div>
  );
}

// Real status of the specialist-agent connection, based on what the backend
// actually tells us (result.live_orchestrator_configured), not a guess from
// a status string. Previously this checked
// `status !== "partner_review_not_configured"` and defaulted everything else
// — including "needs_more_information", "blocked", null, etc — to "reporting
// via Trade Orchestrator", which was wrong any time the orchestrator wasn't
// actually connected. Verified against app/partner_review_service.py:
// live_orchestrator_configured is only true when TRADE_ORCHESTRATOR_BASE_URL
// is set and the live orchestrator path was actually taken.
function partnerConnectionLabel(result) {
  const status = result?.partner_review_status;
  const liveConfigured = result?.live_orchestrator_configured;

  if (!liveConfigured) {
    return "not configured — set env vars in config/partner_integrations.example.env";
  }
  if (status === "needs_more_information") {
    return "prepared for orchestrator — waiting on more shipment or trade info before it can run";
  }
  if (status === "blocked" || status === "review_required") {
    return "reporting via Trade Orchestrator — response flagged for review";
  }
  if (status === "clear") {
    return "reporting via Trade Orchestrator";
  }
  return "orchestrator connected — awaiting a request";
}

export default function PartnerAgents() {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Specialist Agents</div>
          <div className="page-subtitle">
            Risk / Compliance / Trader (MCP) and Finance (REST) — degrade to "not_configured" when
            env vars are unset, per app/partner_review_service.py.
          </div>
        </div>
      </div>

      <div className="content-grid">
        <div className="content-col">
          <ResultGate>
            {(result) => (
              <div className="card">
                <div className="card-header">
                  <div className="card-title">Specialist Agent Status</div>
                  <Badge status={result.partner_review_status} />
                </div>
                <div className="card-body">
                  {result.partner_review_summary && (
                    <p style={{ marginBottom: 12, color: "var(--text-secondary)" }}>{result.partner_review_summary}</p>
                  )}
                  <ul className="partner-list">
                    {PARTNERS.map((p) => (
                      <li className="partner-item" key={p.key}>
                        <div className="partner-info">
                          <div className="partner-icon">{p.icon}</div>
                          <div>
                            <div className="partner-name">{p.name}</div>
                            <div className="partner-meta">{partnerConnectionLabel(result)}</div>
                          </div>
                        </div>
                        <Badge status={result.partner_review_status} />
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </ResultGate>
        </div>
        <div className="content-col">
          <Playground />
        </div>
      </div>
    </>
  );
}
