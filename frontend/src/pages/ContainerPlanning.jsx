import Badge from "../components/Badge.jsx";
import Kpi from "../components/Kpi.jsx";
import ResultGate from "../components/ResultGate.jsx";
import Container3DVisualizer from "../components/Container3DVisualizer.jsx";


// CONTAINER_PLANNING_METRICS_V7
//
// Shipment-level totals are authoritative. Item rows may contain stale
// estimates from an earlier planning pass, so they are only a last resort.
// For direct multi-item prompts, the explicit user-entered weights win.
function finiteNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function completeCargoTotal(cargo, key) {
  if (!Array.isArray(cargo) || !cargo.length) return null;
  const values = cargo.map((item) => finiteNumber(item?.[key]));
  if (values.some((value) => value === null)) return null;
  return values.reduce((sum, value) => sum + value, 0);
}

function containerPlanningRequestText(result) {
  const candidates = [
    result?.request_metadata?.input_source,
    result?.request_metadata?.original_text,
    result?.request_metadata?.request_text,
    result?.original_prompt,
    result?.request_text,
    result?.user_request,
    result?.prompt,
    result?.input_text,
  ];

  for (const value of candidates) {
    const text = String(value ?? "").trim();
    if (text) return text;
  }

  return "";
}

export function directMultiItemTotals(result) {
  const text = containerPlanningRequestText(result);
  if (!text) return null;

  const pattern =
    /([0-9][0-9,]*(?:\.[0-9]+)?)\s*CBM\s+(?:of\s+)?(.*?)\s+weigh(?:ing|s)?\s+([0-9][0-9,]*(?:\.[0-9]+)?)\s*kg\b/gi;

  const items = [];
  let match;

  while ((match = pattern.exec(text)) !== null) {
    const cbm = Number(match[1].replaceAll(",", ""));
    const weightKg = Number(match[3].replaceAll(",", ""));

    if (
      Number.isFinite(cbm) &&
      cbm > 0 &&
      Number.isFinite(weightKg) &&
      weightKg > 0
    ) {
      items.push({ cbm, weightKg });
    }
  }

  if (items.length < 2) return null;

  return {
    totalCbm: items.reduce((sum, item) => sum + item.cbm, 0),
    totalWeightKg: items.reduce((sum, item) => sum + item.weightKg, 0),
  };
}

export function getContainerPlanningMetrics(result) {
  const visualizer = result?.logistics_visualizer || {};
  const metrics = result?.logistics_metrics || {};
  const container = visualizer?.container || {};
  const display = visualizer?.display_metrics || visualizer?.utilization || {};
  const handoff = result?.handoff_payload || {};
  const review = result?.logistics_quality_review || {};
  const cargo = Array.isArray(visualizer?.cargo_mix)
    ? visualizer.cargo_mix
    : [];

  const explicit = directMultiItemTotals(result);
  const cargoCbm = completeCargoTotal(cargo, "total_cbm");
  const cargoWeight = completeCargoTotal(cargo, "total_weight_kg");

  const totalCbm =
    finiteNumber(explicit?.totalCbm) ??
    finiteNumber(display.loaded_cbm) ??
    finiteNumber(display.total_cbm) ??
    finiteNumber(container.total_cbm) ??
    finiteNumber(handoff.total_cbm) ??
    finiteNumber(review.total_cbm) ??
    finiteNumber(metrics.total_cbm) ??
    cargoCbm;

  const totalWeightKg =
    finiteNumber(explicit?.totalWeightKg) ??
    finiteNumber(container.total_weight_kg) ??
    finiteNumber(handoff.total_weight_kg) ??
    finiteNumber(review.total_weight_kg) ??
    finiteNumber(metrics.total_weight_kg) ??
    cargoWeight;

  const utilizationPercent =
    finiteNumber(display.utilization_percent) ??
    finiteNumber(container.utilization_percent) ??
    (totalCbm !== null && finiteNumber(container.capacity_cbm)
      ? Number(((totalCbm / Number(container.capacity_cbm)) * 100).toFixed(2))
      : null);

  return {
    totalCbm,
    totalWeightKg,
    utilizationPercent,
  };
}

const ZONE_TONES = ["", "teal", "amber"];

function ContainerViz({ container, zoneLayout }) {
  const zones = zoneLayout && zoneLayout.length ? zoneLayout : null;
  return (
    <div className="container-viz">
      <div className="container-shell">
        {zones ? (
          zones.map((zone, i) => {
            const itemCount = (zone.items || []).reduce((sum, it) => sum + (it.quantity || 0), 0);
            const heightPct = Math.min(100, 30 + itemCount * 2);
            return (
              <div className="zone" key={zone.zone_name}>
                <div className={`zone-fill ${ZONE_TONES[i % ZONE_TONES.length]}`} style={{ height: `${heightPct}%` }}>
                  {itemCount}
                </div>
                <div className="zone-label">{zone.zone_name.replaceAll("_", " ")}</div>
              </div>
            );
          })
        ) : (
          <div style={{ margin: "auto", color: "var(--text-muted)", fontSize: 12 }}>No zone layout returned.</div>
        )}
      </div>
      <div className="utilization-bar">
        <div className="utilization-fill" style={{ width: `${container?.utilization_percent ?? 0}%` }} />
      </div>
      <div className="container-legend">
        <span>Utilization: {container?.utilization_percent ?? "—"}%</span>
        <span>Capacity: {container?.safe_capacity_cbm ?? "—"} m³ safe / {container?.capacity_cbm ?? "—"} m³ total</span>
        <span>Payload limit: {container?.max_payload_kg ?? "—"} kg</span>
      </div>
    </div>
  );
}

export default function ContainerPlanning() {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Container Planning</div>
          <div className="page-subtitle">Output of app/logistics_agent.py — container fit, loading sequence, and route.</div>
        </div>
      </div>

      <ResultGate>
        {(result) => {
          const lv = result.logistics_visualizer;
          const lm = result.logistics_metrics;
          if (!lv || lv.status !== "available") {
            return (
              <div className="card">
                <div className="card-body">
                  <div className="empty-state">
                    <div className="icon">🚫</div>
                    <p>No logistics visualizer data for this request (intent may not have reached the Logistics Agent).</p>
                  </div>
                </div>
              </div>
            );
          }
          const c = lv.container;
          const canonical = getContainerPlanningMetrics(result);
          return (
            <>
              <div className="kpi-grid">
                <Kpi label="Total CBM" value={canonical.totalCbm} unit="m³" tone="blue" />
                <Kpi label="Total Weight" value={canonical.totalWeightKg} unit="kg" tone="teal" />
                <Kpi label="Risk Score" value={lm.risk_score} unit={`(${lm.risk_level})`} tone={lm.risk_level === "high" ? "red" : "amber"} />
                <Kpi label="Utilization" value={canonical.utilizationPercent} unit="%" />
              </div>

              <div className="content-grid">
                <div className="content-col">
                  <div className="card">
                    <div className="card-header">
                      <div className="card-title">{c?.selected_container} — Load Layout</div>
                      <Badge status={lm.readiness_status} />
                    </div>
                    <div className="card-body">
                      <Container3DVisualizer result={result} />
                    </div>
                  </div>

                  <div className="card">
                    <div className="card-header"><div className="card-title">Cargo Mix</div></div>
                    <div className="card-body tight">
                      <div className="table-wrap">
                        <table className="table">
                          <thead>
                            <tr><th>Item</th><th>Qty</th><th className="num">Unit CBM</th><th className="num">Total CBM</th><th className="num">Total Weight (kg)</th><th>Tags</th></tr>
                          </thead>
                          <tbody>
                            {(lv.cargo_mix || []).map((item) => (
                              <tr key={item.item_name}>
                                <td className="item-name">{item.item_name}</td>
                                <td>{item.quantity}</td>
                                <td className="num">{item.unit_cbm}</td>
                                <td className="num">{item.total_cbm}</td>
                                <td className="num">{item.total_weight_kg}</td>
                                <td>{(item.category_tags || []).join(", ")}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  <div className="card">
                    <div className="card-header"><div className="card-title">Loading Sequence</div></div>
                    <div className="card-body tight">
                      <div className="table-wrap">
                        <table className="table">
                          <thead>
                            <tr><th>#</th><th>Item</th><th>Qty</th><th>Suggested Zone</th><th>Reason</th></tr>
                          </thead>
                          <tbody>
                            {(lv.loading_sequence || []).map((s) => (
                              <tr key={s.sequence_number}>
                                <td>{s.sequence_number}</td>
                                <td className="item-name">{s.item_name}</td>
                                <td>{s.quantity}</td>
                                <td>{s.suggested_zone}</td>
                                <td style={{ color: "var(--text-secondary)" }}>{s.reason}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="content-col">
                  <div className="card">
                    <div className="card-header"><div className="card-title">Container Options</div></div>
                    <div className="card-body tight">
                      <ul className="info-list" style={{ padding: "0 18px" }}>
                        {(lv.container_options || []).map((opt) => (
                          <li key={opt.option_name} style={{ flexDirection: "column", alignItems: "flex-start", gap: 4, padding: "12px 0" }}>
                            <span className="value">{opt.option_name}</span>
                            <span className="label" style={{ fontSize: 11 }}>
                              {opt.estimated_utilization_percent}% utilization · {opt.safe_capacity_cbm} m³ safe · {opt.payload_limit_kg} kg limit
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="card">
                    <div className="card-header">
                      <div className="card-title">Fit Check</div>
                      <Badge status={lv.fit_check?.status} />
                    </div>
                    <div className="card-body">
                      <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
                        Checked against: {lv.fit_check?.selected_container_checked || "—"}
                      </p>
                      {(lv.fit_check?.warnings || []).length > 0 && (
                        <>
                          <div className="form-label">Warnings</div>
                          <ul className="bullets" style={{ marginBottom: 10 }}>
                            {lv.fit_check.warnings.map((w, i) => <li key={i}>{w}</li>)}
                          </ul>
                        </>
                      )}
                      {(lv.fit_check?.recommendations || []).length > 0 && (
                        <>
                          <div className="form-label">Recommendations</div>
                          <ul className="bullets">
                            {lv.fit_check.recommendations.map((w, i) => <li key={i}>{w}</li>)}
                          </ul>
                        </>
                      )}
                      {!(lv.fit_check?.warnings || []).length && !(lv.fit_check?.recommendations || []).length && (
                        <p style={{ color: "var(--text-muted)" }}>No issues flagged.</p>
                      )}
                    </div>
                  </div>

                  {(lv.layout_notes || []).length > 0 && (
                    <div className="card">
                      <div className="card-header"><div className="card-title">Layout Notes</div></div>
                      <div className="card-body">
                        <ul className="bullets">{lv.layout_notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          );
        }}
      </ResultGate>
    </>
  );
}
