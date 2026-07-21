import { useState } from "react";
import AdvisorCard from "../components/AdvisorCard.jsx";
import ResultGate from "../components/ResultGate.jsx";
import { api } from "../api.js";

const SAMPLE_REQUEST = JSON.stringify(
  {
    request_id: "SHOP-REQ-002",
    destination_country: "USA",
    preferred_currency: "USD",
    preferred_countries: ["India"],
    avoid_countries: ["China"],
    budget_usd: 13000,
    items: [
      { name: "TVs", quantity: 50 },
      { name: "Scooters", quantity: 5 },
    ],
  },
  null,
  2
);

function ShoppingPlayground() {
  const [input, setInput] = useState(SAMPLE_REQUEST);
  const [output, setOutput] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setError(null);
    setLoading(true);
    setOutput(null);
    try {
      const parsed = JSON.parse(input);
      const res = await api.agentShopping(parsed);
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
        <div className="card-title">Shopping Agent — Direct Call</div>
        <span className="tab-count">POST /api/agents/shopping</span>
      </div>
      <div className="card-body">
        <p style={{ color: "var(--text-secondary)", marginBottom: 10 }}>
          Calls app/shopping_agent.py build_shopping_plan() directly — bypasses the logistics
          handoff and partner review that the full pipeline runs.
        </p>
        <textarea className="form-textarea mono" style={{ minHeight: 160 }} value={input} onChange={(e) => setInput(e.target.value)} />
        {error && <div className="error-banner" style={{ marginTop: 10 }}>{error}</div>}
        <button className="btn btn-primary" style={{ marginTop: 10 }} onClick={run} disabled={loading}>
          {loading && <span className="spinner" />}
          {loading ? "Running…" : "Run Shopping Agent"}
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

export default function Procurement() {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Procurement</div>
          <div className="page-subtitle">Supplier matching, cost estimate, and quality review from app/shopping_agent.py.</div>
        </div>
      </div>

      <div className="content-grid">
        <div className="content-col">
          <ResultGate>
            {(result) => (
              <>
                <AdvisorCard title="Shopping Quality Review" data={result.shopping_quality_review} />
                <AdvisorCard title="Procurement Advice" data={result.procurement_advice} />
              </>
            )}
          </ResultGate>
        </div>
        <div className="content-col">
          <ShoppingPlayground />
        </div>
      </div>
    </>
  );
}
