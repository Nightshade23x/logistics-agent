import { useState } from "react";
import Badge from "../components/Badge.jsx";
import ResultGate from "../components/ResultGate.jsx";
import { api } from "../api.js";
import { cleanText, humanizeKey } from "../utils/displayFormat.js";

const PARTNERS = [
  {
    key: "risk",
    name: "Risk Agent",
    role: "Checks country risk, sanctions indicators, and risk warnings."
  },
  {
    key: "compliance",
    name: "Compliance Agent",
    role: "Checks restricted goods, permits, documents, and compliance flags."
  },
  {
    key: "trader",
    name: "Trader Agent",
    role: "Checks HS code, duty rate, FTA status, and export strategy."
  },
  {
    key: "finance",
    name: "Finance Agent",
    role: "Checks landed cost, freight, insurance, duty, tax, and budget readiness."
  }
];

const ENDPOINTS = {
  logistics: {
    label: "Logistics Agent",
    route: "/api/agents/logistics",
    sample: JSON.stringify({ items: [{ name: "TV", quantity: 10, length_m: 1.2, width_m: 0.2, height_m: 0.8, weight_kg: 12, fragile: true }] }, null, 2),
    call: (parsed) => api.agentLogistics(parsed.items, parsed.shipment_context || null)
  },
  shopping: {
    label: "Shopping Agent",
    route: "/api/agents/shopping",
    sample: JSON.stringify({ destination_country: "USA", preferred_countries: ["India"], items: [{ product_name: "ceramic tiles", quantity: 1000 }] }, null, 2),
    call: (parsed) => api.agentShopping(parsed)
  },
  document: {
    label: "Document Agent",
    route: "/api/agents/document",
    sample: JSON.stringify({ text: "INVOICE\nSupplier: Acme Traders\nBuyer: Demo Customer\nTotal Value: 5000 USD" }, null, 2),
    call: (parsed) => api.agentDocument(parsed.text)
  }
};

function AgentPlayground() {
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
    <details className="developer-playground-details">
      <summary>Developer testing tools</summary>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">Direct agent playground</div>
            <div className="section-muted">Use only for debugging direct API routes. Normal users should start from the Dashboard.</div>
          </div>
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

          <textarea className="form-textarea mono" style={{ minHeight: 180 }} value={input} onChange={(e) => setInput(e.target.value)} />

          {error && <div className="error-banner" style={{ marginTop: 10 }}>{error}</div>}

          <button className="btn btn-primary" style={{ marginTop: 10 }} onClick={run} disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "Calling agent..." : "Send direct call"}
          </button>

          {output && (
            <>
              <div className="form-label" style={{ marginTop: 16 }}>Response</div>
              <pre className="json-view">{JSON.stringify(output, null, 2)}</pre>
            </>
          )}
        </div>
      </div>
    </details>
  );
}

function statusForPartner(result, key) {
  const status = result?.partner_review_status || "partner_review_not_configured";

  if (status === "clear") return "clear";
  if (status === "partner_review_not_configured" || status === "unknown") return "review_required";

  return status;
}

export default function PartnerAgents() {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Agent Diagnostics</div>
          <div className="page-subtitle">Monitor specialist agent availability and test direct agent calls. Local advisory fallback keeps the main app usable when live partner services are not connected.</div>
        </div>
      </div>

      <div className="content-grid">
        <div className="content-col">
          <ResultGate>
            {(result) => (
              <div className="card">
                <div className="card-header">
                  <div>
                    <div className="card-title">Agent connection status</div>
                    <div className="section-muted">Latest request agent availability.</div>
                  </div>
                  <Badge status={result.partner_review_status || "partner_review_not_configured"} />
                </div>

                <div className="card-body">
                  {result.partner_review_summary && <p className="section-summary">{cleanText(result.partner_review_summary)}</p>}

                  <div className="agent-diagnostic-grid">
                    {PARTNERS.map((partner) => (
                      <div className="agent-diagnostic-card" key={partner.key}>
                        <div className="agent-diagnostic-top">
                          <div>
                            <div className="agent-diagnostic-title">{partner.name}</div>
                            <p>{partner.role}</p>
                          </div>
                          <Badge status={statusForPartner(result, partner.key)} />
                        </div>

                        <div className="preview-list-v2">
                          <div className="preview-row-v2"><span>Mode</span><strong>Local fallback / live service optional</strong></div>
                          <div className="preview-row-v2"><span>Used in latest request</span><strong>{(result.agents_called || []).some((a) => humanizeKey(a).toLowerCase().includes(partner.key)) ? "Yes" : "No"}</strong></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </ResultGate>
        </div>

        <div className="content-col">
          <AgentPlayground />
        </div>
      </div>
    </>
  );
}
