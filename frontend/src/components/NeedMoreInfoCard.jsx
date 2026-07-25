import { useState } from "react";
import { api } from "../api.js";

// Surfaces `action_plan.user_questions` / `clarification_questions` as an
// actual form instead of a dead-end bullet list. Answers get appended as
// plain-English follow-up sentences to the original request and resubmitted
// through the same text pipeline — so it inherits whatever the parser can
// already handle (e.g. answering "FOB" to the Incoterm question works best
// if phrased as "Use FOB incoterm", since that's what the backend regex
// looks for). This is a first pass: a more robust version would map answers
// straight into Structured JSON fields instead of round-tripping through
// free-text parsing again.
export default function NeedMoreInfoCard({ result, originalText, onResult }) {
  const questions =
    (result?.clarification_questions?.length && result.clarification_questions) ||
    result?.action_plan?.user_questions ||
    [];

  const [answers, setAnswers] = useState({});
  const [extra, setExtra] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!questions.length) return null;

  function setAnswer(q, value) {
    setAnswers((prev) => ({ ...prev, [q]: value }));
  }

  async function handleSubmit() {
    const answeredLines = questions
      .map((q) => (answers[q] || "").trim())
      .filter(Boolean);
    const extraLine = extra.trim();

    if (!answeredLines.length && !extraLine) {
      setError("Answer at least one question, or add a note, before submitting.");
      return;
    }

    const followUp = [...answeredLines, extraLine].filter(Boolean).join(". ");
    const combinedText = `${originalText}\n\nAdditional information: ${followUp}.`;

    setLoading(true);
    setError(null);
    try {
      const payload = await api.requestText(combinedText);
      onResult(payload, { label: combinedText.slice(0, 60) });
      setAnswers({});
      setExtra("");
    } catch (e) {
      setError(e.message || "Failed to resubmit with the additional information.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card" style={{ borderLeft: "4px solid var(--accent-amber)" }}>
      <div className="card-header">
        <div className="card-title">More information needed</div>
      </div>
      <div className="card-body">
        <p style={{ color: "var(--text-secondary)", marginBottom: 12 }}>
          Answer any of these and resubmit — your answers get added to the original request.
        </p>

        {questions.map((q, i) => (
          <div className="form-group" key={i} style={{ marginBottom: 10 }}>
            <label className="form-label">{q}</label>
            <input
              type="text"
              className="form-input"
              value={answers[q] || ""}
              onChange={(e) => setAnswer(q, e.target.value)}
              placeholder="Type your answer..."
            />
          </div>
        ))}

        <div className="form-group" style={{ marginBottom: 10 }}>
          <label className="form-label">Anything else to add</label>
          <textarea
            className="form-textarea"
            rows={2}
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            placeholder="Optional — any other details"
          />
        </div>

        {error && <p style={{ color: "var(--accent-red)", marginBottom: 10 }}>{error}</p>}

        <button className="btn btn-teal" onClick={handleSubmit} disabled={loading}>
          {loading ? "Resubmitting..." : "Submit additional info"}
        </button>
      </div>
    </div>
  );
}
