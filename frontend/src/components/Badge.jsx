import { humanizeStatus } from "../utils/displayFormat.js";

function statusClass(status) {
  const raw = String(status || "").toLowerCase();

  if (raw.includes("critical") || raw.includes("blocked") || raw.includes("error")) return "blocked";
  if (raw.includes("clear") || raw.includes("ready") || raw.includes("available")) return "clear";
  if (raw.includes("review") || raw.includes("missing") || raw.includes("partial")) return "review_required";
  if (raw.includes("not_applicable") || raw.includes("unavailable")) return "not_applicable";

  return raw || "unknown";
}

export default function Badge({ status }) {
  return (
    <span className={`badge ${statusClass(status)}`}>
      <span className="badge-dot" />
      {humanizeStatus(status)}
    </span>
  );
}
