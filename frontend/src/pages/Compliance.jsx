import AdvisorCard from "../components/AdvisorCard.jsx";
import ResultGate from "../components/ResultGate.jsx";

export default function Compliance() {
  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">Compliance &amp; Documents</div>
          <div className="page-subtitle">
            Document validation, trade terms, insurance, required documents, landed cost, and
            compliance readiness advisors.
          </div>
        </div>
      </div>

      <ResultGate>
        {(result) => (
          <div className="content-grid">
            <div className="content-col">
              <AdvisorCard title="Document Quality Review" data={result.document_quality_review} />
              <AdvisorCard title="Document Requirements" data={result.document_requirements_advice} />
              <AdvisorCard title="Trade Compliance Readiness" data={result.trade_compliance_readiness} />
            </div>
            <div className="content-col">
              <AdvisorCard title="Trade Terms" data={result.trade_terms_advice} />
              <AdvisorCard title="Insurance" data={result.insurance_advice} />
              <AdvisorCard title="Landed Cost" data={result.landed_cost_advice} />

              <div className="card">
                <div className="card-header">
                  <div className="card-title">Clarification Questions</div>
                  <span className="tab-count">{(result.clarification_questions || []).length}</span>
                </div>
                <div className="card-body">
                  {(result.clarification_questions || []).length ? (
                    <ul className="bullets">
                      {result.clarification_questions.map((q, i) => <li key={i}>{q}</li>)}
                    </ul>
                  ) : (
                    <p style={{ color: "var(--text-muted)" }}>No open questions.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </ResultGate>
    </>
  );
}
