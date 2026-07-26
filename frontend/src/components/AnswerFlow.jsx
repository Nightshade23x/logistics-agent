export default function AnswerFlow({ steps }) {
  if (!steps || !steps.length) return null;

  return (
    <div className="answer-flow">
      <div className="answer-flow-title">Next step flow</div>

      <div className="answer-flow-track">
        {steps.map((step, index) => (
          <div className="answer-flow-item-wrap" key={`${step.title}-${index}`}>
            <div className={`answer-flow-item ${step.status === "now" ? "is-now" : ""}`}>
              <div className="answer-flow-number">{step.label}</div>
              <div className="answer-flow-content">
                <div className="answer-flow-step-title">{step.title}</div>
                <div className="answer-flow-tab">Go to: {step.tab}</div>
                <div className="answer-flow-detail">{step.detail}</div>
              </div>
            </div>

            {index < steps.length - 1 && <div className="answer-flow-arrow">→</div>}
          </div>
        ))}
      </div>
    </div>
  );
}
