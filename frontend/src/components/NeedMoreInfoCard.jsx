import { useState } from "react";
import { api } from "../api.js";
import { humanizeKey } from "../utils/displayFormat.js";

function placeholderForQuestion(question) {
  const q = String(question || "").toLowerCase();

  if (q.includes("origin") || q.includes("supplier country")) {
    return "India";
  }

  if (q.includes("destination")) {
    return "Germany";
  }

  if (q.includes("quantity") || q.includes("order volume")) {
    return "1000 ceramic tiles";
  }

  if (q.includes("budget") || q.includes("target unit price")) {
    return "Budget 12000 USD";
  }

  if (q.includes("freight") || q.includes("insurance") || q.includes("duty") || q.includes("vat") || q.includes("brokerage") || q.includes("delivery")) {
    return "Freight 3500 USD, insurance 600 USD, duty 8%, VAT 6%, brokerage 400 USD, delivery 800 USD";
  }

  if (q.includes("dimension") || q.includes("cbm") || q.includes("weight")) {
    return "Total cargo is 10 CBM and 1200 kg";
  }

  if (q.includes("document") || q.includes("invoice") || q.includes("packing")) {
    return "Commercial invoice, packing list, and bill of lading will be prepared";
  }

  return "Type your answer...";
}

function formatAnswerLine(question, answer) {
  const q = String(question || "").toLowerCase();
  const a = String(answer || "").trim();

  if (!a) return null;

  if (q.includes("origin") || q.includes("supplier country")) {
    return `Origin country: ${a}`;
  }

  if (q.includes("destination")) {
    return `Destination country: ${a}`;
  }

  if (q.includes("incoterm")) {
    return /incoterm/i.test(a) ? a : `Use ${a} incoterm.`;
  }

  return a;
}

// MISSING_INFO_SUPERSEDE_INCOTERM_V90
// A corrected trade term supersedes an earlier standalone trade-term answer.
function removePriorStandaloneIncotermAnswers(text) {
  return String(text || "")
    .replace(/^\s*Use\s+[A-Za-z]{2,12}\s+incoterm\.?\s*$/gim, "")
    .replace(/^\s*Incoterm\s*(?:is|=|:)?\s*[A-Za-z]{2,12}\.?\s*$/gim, "")
    .replace(/^\s*Trade\s+term\s*(?:is|=|:)?\s*[A-Za-z]{2,12}\.?\s*$/gim, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function buildUpdatedRequest(originalText, questions, answers, extraLine) {
  let baseText = String(originalText || "").trim();
  const formattedLines = [];

  for (const question of questions) {
    const answer = answers[question] || "";
    const line = formatAnswerLine(question, answer);
    if (!line) continue;

    if (String(question || "").toLowerCase().includes("incoterm")) {
      baseText = removePriorStandaloneIncotermAnswers(baseText);
    }

    formattedLines.push(line);
  }

  const additions = [...formattedLines, String(extraLine || "").trim()].filter(Boolean);

  return [baseText, additions.join("\n")]
    .filter(Boolean)
    .join("\n\n")
    .trim();
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
    const hasAnsweredQuestion = questions.some((q) => String(answers[q] || "").trim());
    const extraLine = extra.trim();

    if (!hasAnsweredQuestion && !extraLine) {
      setError("Answer at least one question, or add a note, before submitting.");
      return;
    }

    const combinedText = buildUpdatedRequest(originalText, questions, answers, extraLine);

    setLoading(true);
    setError(null);

    try {
      const payload = await api.requestText(combinedText);
      onResult(payload, { label: combinedText.slice(0, 60) });
      setAnswers({});
      setExtra("");
    } catch (e) {
      setError(e.message || "Failed to rerun the agents with the added information.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card need-info-v2">
      <div className="card-header">
        <div>
          <div className="card-title">More information needed</div>
          <div className="section-muted">Add the missing details below. The app will merge them into the original request and rerun the agents.</div>
        </div>
      </div>

      <div className="card-body">
        <div className="need-info-grid">
          {questions.map((q, i) => (
            <div className="form-group" key={`${q}-${i}`}>
              <label className="form-label">{humanizeKey(q)}</label>
              <input
                type="text"
                className="form-input"
                value={answers[q] || ""}
                onChange={(e) => setAnswer(q, e.target.value)}
                placeholder={placeholderForQuestion(q)}
              />
            </div>
          ))}
        </div>

        <div className="form-group" style={{ marginTop: 12 }}>
          <label className="form-label">Anything else to add</label>
          <textarea
            className="form-textarea"
            value={extra}
            onChange={(e) => setExtra(e.target.value)}
            placeholder="Optional notes, handling instructions, preferred route, document details..."
            style={{ minHeight: 90 }}
          />
        </div>

        {error && <p style={{ color: "var(--danger)", marginTop: 8 }}>{error}</p>}

        <button className="btn primary" onClick={handleSubmit} disabled={loading}>
          {loading ? "Rerunning agents..." : "Update request and rerun agents"}
        </button>
      </div>
    </div>
  );
}
