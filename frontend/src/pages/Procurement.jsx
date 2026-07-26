import { useState } from "react";
import Badge from "../components/Badge.jsx";
import ResultGate from "../components/ResultGate.jsx";
import { api } from "../api.js";
import { cleanText, formatValue, humanizeKey, uniq } from "../utils/displayFormat.js";

const SAMPLE_SHOPPING = JSON.stringify({
  request_id: "SHOP-REQ-002",
  destination_country: "USA",
  preferred_currency: "USD",
  preferred_countries: ["India"],
  avoided_countries: ["China"],
  budget_usd: 13000,
  items: [
    { product_name: "TV", quantity: 50 },
    { product_name: "electric scooters", quantity: 5 },
    { product_name: "ceramic tiles", quantity: 100 }
  ]
}, null, 2);

function collectSuppliers(result) {
  const direct = []
    .concat(Array.isArray(result?.supplier_options) ? result.supplier_options : [])
    .concat(Array.isArray(result?.shortlisted_suppliers) ? result.shortlisted_suppliers : [])
    .concat(Array.isArray(result?.recommended_suppliers) ? result.recommended_suppliers : []);

  if (direct.length) return direct;

  const recs = result?.procurement_advice?.recommendations || [];
  return recs
    .filter((x) => String(x || "").toLowerCase().includes("supplier") || String(x || "").toLowerCase().includes("shortlist"))
    .map((text, index) => ({
      supplier_name: cleanText(String(text).replace(/^Shortlist:\s*/i, "").split(":")[0]) || `Supplier option ${index + 1}`,
      supplier_type: index === 0 ? "Best price candidate" : index === 1 ? "Balanced reliability candidate" : "Premium / urgent candidate",
      notes: cleanText(String(text).split(":").slice(1).join(":")) || "Review price, lead time, payment terms, packaging, certifications, and reliability."
    }));
}

function SupplierCard({ supplier, index }) {
  const name = supplier.supplier_name || supplier.name || supplier.supplier || `Supplier option ${index + 1}`;
  const type = supplier.supplier_type || supplier.selection_status || "Shortlisted for review";
  const product = supplier.product || supplier.product_name || supplier.item_name;
  const note = supplier.notes || supplier.reason || supplier.summary || "Review price, lead time, payment terms, packing quality, certifications, and reliability.";

  return (
    <div className="supplier-profile-card">
      <div className="supplier-profile-top">
        <div>
          <div className="supplier-profile-title">{humanizeKey(name)}</div>
          <div className="supplier-profile-type">{humanizeKey(type)}</div>
        </div>
        <Badge status="review_required" />
      </div>

      {product && <div className="supplier-profile-product">Product: {humanizeKey(product)}</div>}
      <p>{cleanText(note)}</p>

      <div className="supplier-check-tags">
        <span>Price</span>
        <span>Lead time</span>
        <span>Payment</span>
        <span>Packaging</span>
        <span>Certifications</span>
      </div>
    </div>
  );
}

function ProcurementSummary({ result, suppliers }) {
  const advice = result?.procurement_advice || {};
  const quality = result?.shopping_quality_review || {};

  const stats = [
    ["Selected items", advice.selected_items_count ?? quality.selected_items_count ?? 0],
    ["Supplier options", suppliers.length || advice.supplier_options_count || quality.supplier_options_count || 0],
    ["Budget", advice.budget_usd ? `${advice.budget_usd} USD` : "Not confirmed"],
    ["Estimated cost", advice.estimated_total_procurement_cost_usd ? `${advice.estimated_total_procurement_cost_usd} USD` : "Not confirmed"]
  ];

  return (
    <div className="procurement-summary-grid">
      {stats.map(([label, value]) => (
        <div className="smart-metric" key={label}>
          <div className="smart-metric-label">{label}</div>
          <div className="smart-metric-value">{formatValue(value)}</div>
        </div>
      ))}
    </div>
  );
}

function ActionGroup({ title, items }) {
  const list = uniq(items || []).filter(Boolean);

  if (!list.length) return null;

  return (
    <div className="procurement-action-group">
      <div className="section-subtitle">{title}</div>
      <ul className="compact-list">
        {list.map((item, index) => (
          <li key={`${item}-${index}`}>{humanizeKey(cleanText(item))}</li>
        ))}
      </ul>
    </div>
  );
}

function ShoppingPlayground() {
  const [input, setInput] = useState(SAMPLE_SHOPPING);
  const [output, setOutput] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setError(null);
    setLoading(true);

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
    <details className="developer-playground-details">
      <summary>Developer direct-call tools</summary>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">Shopping Agent direct call</div>
            <div className="section-muted">For debugging only. The main dashboard uses the full pipeline.</div>
          </div>
          <span className="tab-count">POST /api/agents/shopping</span>
        </div>
        <div className="card-body">
          <textarea className="form-textarea mono" style={{ minHeight: 160 }} value={input} onChange={(e) => setInput(e.target.value)} />
          {error && <div className="error-banner" style={{ marginTop: 10 }}>{error}</div>}
          <button className="btn btn-primary" style={{ marginTop: 10 }} onClick={run} disabled={loading}>
            {loading && <span className="spinner" />}
            {loading ? "Running..." : "Run Shopping Agent"}
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

export default function Procurement() {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Procurement</div>
          <div className="page-subtitle">Supplier shortlist, commercial gaps, negotiation checklist, and purchase-order readiness.</div>
        </div>
      </div>

      <ResultGate>
        {(result) => {
          const suppliers = collectSuppliers(result);
          const advice = result.procurement_advice || {};
          const questions = advice.user_questions || result.clarification_questions || [];

          return (
            <div className="content-grid">
              <div className="content-col">
                <div className="card">
                  <div className="card-header">
                    <div>
                      <div className="card-title">Procurement plan</div>
                      <div className="section-muted">First-pass supplier plan for review.</div>
                    </div>
                    <Badge status={advice.status || result.shopping_quality_review?.status || "review_required"} />
                  </div>

                  <div className="card-body">
                    <p className="section-summary">{cleanText(advice.summary || result.shopping_quality_review?.summary || "Review supplier options and commercial gaps before issuing a purchase order.")}</p>
                    <ProcurementSummary result={result} suppliers={suppliers} />

                    <div className="section-subtitle">Supplier shortlist</div>
                    {suppliers.length ? (
                      <div className="supplier-profile-grid">
                        {suppliers.slice(0, 6).map((supplier, index) => (
                          <SupplierCard supplier={supplier} index={index} key={index} />
                        ))}
                      </div>
                    ) : (
                      <p className="empty-text">No supplier shortlist available for this request.</p>
                    )}
                  </div>
                </div>

                <div className="card">
                  <div className="card-header">
                    <div className="card-title">Procurement checklist</div>
                    <Badge status="review_required" />
                  </div>
                  <div className="card-body procurement-action-grid">
                    <ActionGroup title="Missing commercial details" items={questions} />
                    <ActionGroup title="Before purchase order" items={advice.negotiation_points || advice.recommendations} />
                    <ActionGroup title="Shipping handoff" items={[
                      "Confirm final packed dimensions and total weight.",
                      "Confirm cargo value for insurance and landed cost.",
                      "Request proforma invoice from shortlisted suppliers."
                    ]} />
                  </div>
                </div>
              </div>

              <div className="content-col">
                <ShoppingPlayground />
              </div>
            </div>
          );
        }}
      </ResultGate>
    </>
  );
}
