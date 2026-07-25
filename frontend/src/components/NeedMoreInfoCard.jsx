import { useState } from "react";
import { api } from "../api.js";

// Surfaces `action_plan.user_questions` / `clarification_questions` as an
// actual form instead of a dead-end bullet list. Answers get formatted into
// the specific phrasing the backend parsers actually look for (verified
// directly against app/shopping_text_parser.py and app/text_shipment_parser.py
// rather than guessed), then appended as new lines to the original request
// and resubmitted through the same text pipeline. Known formats:
//   - "destination" questions -> "Destination: <answer>" on its own line
//     (shopping_text_parser.py only matches this exact labeled-line form,
//     not "to <country>" inline phrasing)
//   - "incoterm" questions -> "Use <answer> incoterm." if the answer doesn't
//     already say "incoterm"
//   - everything else -> the raw answer, on its own line, prefixed with the
//     question so context isn't lost
// This still can't fill fields the backend has no extraction pattern for at
// all (freight/insurance/duty/import-tax/customs/local-delivery in the
// shopping-intent parser) — that's a backend gap, not something client-side
// formatting can work around.
function formatAnswerLine(question, answer) {
  const q = question.toLowerCase();
  const a = answer.trim();
  if (!a) return null;

  if (q.includes("destination")) {
    return `Destination: ${a}`;
  }
  if (q.includes("incoterm")) {
    return /incoterm/i.test(a) ? a : `Use ${a} incoterm.`;
  }
  return `${question} ${a}.`;
}

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
    const formattedLines = questions
      .map((q) => formatAnswerLine(q, answers[q] || ""))
      .filter(Boolean);
    const extraLine = extra.trim();

    if (!formattedLines.length && !extraLine) {
      setError("Answer at least one question, or add a note, before submitting.");
      return;
    }

    const allLines = [...formattedLines, extraLine].filter(Boolean);
    const combinedText = `${originalText}\n\n${allLines.join("\n")}`;

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
