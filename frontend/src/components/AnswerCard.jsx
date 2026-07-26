import Badge from "./Badge.jsx";
import {
  getAgentSummaryFallback,
  getAnswerActions,
  getAnswerStatus,
  pickUserFacingAnswer,
} from "../utils/userFacingAnswer.js";

export default function AnswerCard({ result }) {
  const answerText = pickUserFacingAnswer(result);
  const fallbackText = getAgentSummaryFallback(result);
  const displayText = answerText || fallbackText;
  const actions = getAnswerActions(result);
  const status = getAnswerStatus(result);

  if (!displayText && !actions.length) return null;

  return (
    <div className="card" style={{ borderLeft: "4px solid var(--accent-teal)" }}>
      <div className="card-header">
        <div className="card-title">Answer</div>
        <Badge status={status} />
      </div>

      <div className="card-body">
        {displayText && (
          <div
            style={{
              color: "var(--text-secondary)",
              whiteSpace: "pre-wrap",
              lineHeight: 1.65,
              marginBottom: actions.length ? 16 : 0,
            }}
          >
            {displayText}
          </div>
        )}

        {actions.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <div className="form-label">What to do next</div>
            <ul className="bullets">
              {actions.slice(0, 8).map((action, index) => (
                <li key={index}>{action}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
