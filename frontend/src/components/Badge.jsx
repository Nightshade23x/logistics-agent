// Maps the backend's free-form status/decision strings onto one of the
// reference design's 5 badge tones (clear / review / blocked / info / neutral).
function toneFor(status) {
  if (!status) return "neutral";
  const s = String(status).toLowerCase();
  if (s.includes("blocked") || s.includes("critical") || s.includes("error")) return "blocked";
  if (s.includes("clear") || s.includes("ready") || s.includes("ok")) return "clear";
  if (s.includes("review") || s.includes("missing") || s.includes("needs") || s.includes("partial")) return "review";
  if (s.includes("not_configured") || s.includes("not_applicable") || s.includes("unknown")) return "neutral";
  return "info";
}

export default function Badge({ status, label }) {
  const tone = toneFor(status);
  const text = label || String(status ?? "unknown").replaceAll("_", " ");
  return (
    <span className={`badge ${tone}`}>
      <span className="badge-dot" />
      {text}
    </span>
  );
}
