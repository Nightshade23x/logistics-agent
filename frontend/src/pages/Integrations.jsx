import { useEffect, useState } from "react";
import { api } from "../api.js";


function statusLabel(value) {
  const text = String(value || "unknown").replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}


function ProviderCard({ provider, health }) {
  const healthValue = health?.status || (provider.configured ? "configured" : "not_configured");
  return (
    <article className="integration-provider-card">
      <div className="integration-provider-head">
        <div>
          <h3>{provider.display_name}</h3>
          <p>{provider.provider_type === "mock" ? "Safe demonstration provider" : "External REST provider"}</p>
        </div>
        <span className={`integration-source-badge ${provider.live ? "live" : "demo"}`}>
          {provider.live ? "Live API" : "Demo / sandbox"}
        </span>
      </div>
      <dl className="integration-definition-list">
        <div><dt>Connection</dt><dd>{statusLabel(healthValue)}</dd></div>
        <div><dt>Environment</dt><dd>{statusLabel(provider.environment)}</dd></div>
        <div><dt>Credentials</dt><dd>{provider.credentials_configured ? "Available" : "Not configured"}</dd></div>
        <div><dt>Can provide</dt><dd>{(provider.capabilities || []).join(", ") || "No capabilities listed"}</dd></div>
      </dl>
      {health?.summary && <p className="integration-health-note">{health.summary}</p>}
    </article>
  );
}


export default function Integrations() {
  const [catalog, setCatalog] = useState(null);
  const [health, setHealth] = useState(null);
  const [quotes, setQuotes] = useState(null);
  const [loading, setLoading] = useState(true);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [error, setError] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [form, setForm] = useState({
    origin_country: "India",
    destination_country: "Germany",
    total_weight_kg: "2500",
    total_cbm: "9.6",
    package_count: "10",
    currency: "USD",
    hazardous: false,
  });

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const [catalogPayload, healthPayload] = await Promise.all([
        api.integrations(apiKey),
        api.integrationHealth(apiKey),
      ]);
      setCatalog(catalogPayload);
      setHealth(healthPayload);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // The access key is intentionally not persisted in browser storage.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function requestQuotes(event) {
    event.preventDefault();
    setQuoteLoading(true);
    setError("");
    try {
      const payload = await api.integrationQuotes(
        {
          ...form,
          total_weight_kg: form.total_weight_kg ? Number(form.total_weight_kg) : null,
          total_cbm: form.total_cbm ? Number(form.total_cbm) : null,
          package_count: Number(form.package_count || 1),
        },
        apiKey,
      );
      setQuotes(payload);
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setQuoteLoading(false);
    }
  }

  const healthById = Object.fromEntries((health?.providers || []).map((item) => [item.provider_id, item]));

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Company and carrier integrations</div>
          <div className="page-subtitle">Connect approved APIs, check their status, and compare normalized shipment quotes.</div>
        </div>
        <button className="btn" type="button" onClick={refresh} disabled={loading}>Refresh connections</button>
      </div>

      <div className="integration-explainer" role="note">
        <strong>What this means:</strong> demo estimates are clearly separated from live carrier prices. Credentials stay on the backend and are never shown in this page.
      </div>

      <details className="integration-admin-details">
        <summary>Administrator access</summary>
        <label htmlFor="integration-api-key">API access key, only when your administrator enabled one</label>
        <input
          id="integration-api-key"
          className="form-input"
          type="password"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          autoComplete="off"
        />
      </details>

      {error && <div className="error-banner" role="alert">{error}</div>}
      <div aria-live="polite" className="sr-only">{loading ? "Checking integrations" : "Integration check complete"}</div>

      <section className="integration-provider-grid" aria-label="Configured providers">
        {(catalog?.providers || []).map((provider) => (
          <ProviderCard key={provider.provider_id} provider={provider} health={healthById[provider.provider_id]} />
        ))}
      </section>

      <div className="card integration-quote-card">
        <div className="card-header">
          <div>
            <div className="card-title">Try the standard quote contract</div>
            <div className="section-muted">One request format can be sent to every configured provider.</div>
          </div>
        </div>
        <div className="card-body">
          <form onSubmit={requestQuotes} className="integration-quote-form">
            <label>Origin country<input className="form-input" value={form.origin_country} onChange={(e) => setForm({ ...form, origin_country: e.target.value })} required /></label>
            <label>Destination country<input className="form-input" value={form.destination_country} onChange={(e) => setForm({ ...form, destination_country: e.target.value })} required /></label>
            <label>Total weight in kg<input className="form-input" type="number" min="0" step="any" value={form.total_weight_kg} onChange={(e) => setForm({ ...form, total_weight_kg: e.target.value })} /></label>
            <label>Total volume in CBM<input className="form-input" type="number" min="0" step="any" value={form.total_cbm} onChange={(e) => setForm({ ...form, total_cbm: e.target.value })} /></label>
            <label>Number of packages<input className="form-input" type="number" min="1" step="1" value={form.package_count} onChange={(e) => setForm({ ...form, package_count: e.target.value })} /></label>
            <label>Currency<input className="form-input" value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value.toUpperCase() })} /></label>
            <label className="integration-checkbox"><input type="checkbox" checked={form.hazardous} onChange={(e) => setForm({ ...form, hazardous: e.target.checked })} /> Dangerous goods</label>
            <button className="btn btn-primary" type="submit" disabled={quoteLoading}>{quoteLoading ? "Checking providers..." : "Compare available quotes"}</button>
          </form>
        </div>
      </div>

      {quotes && (
        <section className="integration-results" aria-live="polite">
          <h2>Quote results</h2>
          {(quotes.quotes || []).length === 0 ? (
            <div className="integration-empty">No provider returned a quote. Open the connection cards above to check configuration.</div>
          ) : (
            <div className="integration-quote-grid">
              {quotes.quotes.map((quote) => (
                <article className="integration-quote" key={`${quote.provider_id}-${quote.service_code}`}>
                  <div className="integration-quote-top">
                    <div><strong>{quote.service_name}</strong><span>{quote.provider_name}</span></div>
                    <span className={`integration-source-badge ${quote.live ? "live" : "demo"}`}>{quote.live ? "Live API" : "Demo estimate"}</span>
                  </div>
                  <div className="integration-price">{quote.currency} {Number(quote.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                  <p>Transit estimate: {quote.transit_days_min ?? "?"}–{quote.transit_days_max ?? "?"} days</p>
                  {(quote.warnings || []).map((warning) => <p className="integration-warning" key={warning}>{warning}</p>)}
                </article>
              ))}
            </div>
          )}
          <p className="integration-disclaimer">{quotes.disclaimer}</p>
        </section>
      )}
    </>
  );
}
