import Badge from "./Badge.jsx";

// Surfaces the actual plain-English answer right after a request runs, instead
// of making the user click into Reports to find it. Combines `final_answer`
// (the headline/status) with `agent_summaries` (the real substance from
// whichever specialist agents actually ran) and falls back to the executive
// summary's next actions when final_answer itself has nothing queued up.
export default function AnswerCard({ result }) {
  const fa = result?.final_answer;
  const summaries = result?.agent_summaries || [];
  const es = result?.executive_summary;

  if (!fa && summaries.length === 0) return null;

  const nextActions =
    (fa?.next_actions && fa.next_actions.length ? fa.next_actions : null) ||
    (es?.top_next_actions && es.top_next_actions.length ? es.top_next_actions : []);

  const blockers = fa?.blockers?.length ? fa.blockers : [];
  const warnings = fa?.warnings?.length ? fa.warnings : [];

  return (
    <div className="card" style={{ borderLeft: "4px solid var(--accent-teal, #0f9d8f)" }}>
      <div className="card-header">
        <div className="card-title">Answer</div>
        <Badge status={fa?.status} />
      </div>
      <div className="card-body">
        {fa?.headline && <p style={{ fontWeight: 600, marginBottom: 8 }}>{fa.headline}</p>}
        {fa?.answer_text && (
          <p style={{ color: "var(--text-secondary)", marginBottom: summaries.length ? 14 : 0 }}>
            {fa.answer_text}
          </p>
        )}

        {summaries.map((s, i) => (
          <p key={i} style={{ color: "var(--text-secondary)", marginBottom: 10 }}>
            <strong>{s.agent_name}:</strong> {s.summary}
          </p>
        ))}

        {blockers.length > 0 && (
          <>
            <div className="form-label" style={{ marginTop: 10 }}>Blockers</div>
            <ul className="bullets">{blockers.map((b, i) => <li key={i}>{b}</li>)}</ul>
          </>
        )}

        {warnings.length > 0 && (
          <>
            <div className="form-label" style={{ marginTop: 10 }}>Warnings</div>
            <ul className="bullets">{warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
          </>
        )}

        {nextActions.length > 0 && (
          <>
            <div className="form-label" style={{ marginTop: 10 }}>What to do next</div>
            <ul className="bullets">{nextActions.slice(0, 5).map((a, i) => <li key={i}>{a}</li>)}</ul>
          </>
        )}
      </div>
    </div>
  );
}
