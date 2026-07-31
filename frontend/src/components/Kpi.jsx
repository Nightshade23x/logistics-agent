export default function Kpi({ label, value, unit, tone = "" }) {
  return (
    <div className={`kpi ${tone}`}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">
        {value ?? "—"}
        {unit ? <span className="unit">{unit}</span> : null}
      </div>
    </div>
  );
}
