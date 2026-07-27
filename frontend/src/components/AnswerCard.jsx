import Badge from "./Badge.jsx";
import AnswerFlow from "./AnswerFlow.jsx";
import {
  buildNextStepFlow,
  getAgentSummaryFallback,
  getAnswerActions,
  getAnswerStatus,
  parseAnswerSections,
  pickUserFacingAnswer,
} from "../utils/userFacingAnswer.js";

function AnswerSection({ section }) {
  return (
    <div className="answer-section">
      <div className="answer-section-title">{section.title}</div>

      {section.body.map((paragraph, index) => (
        <p className="answer-paragraph" key={`p-${index}`}>
          {paragraph}
        </p>
      ))}

      {section.bullets.length > 0 && (
        <ul className="answer-bullets">
          {section.bullets.map((bullet, index) => (
            <li key={`b-${index}`}>{bullet}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function AnswerCard({ result }) {
  const answerText = pickUserFacingAnswer(result);
  const fallbackText = getAgentSummaryFallback(result);
  const displayText = answerText || fallbackText;
  const actions = getAnswerActions(result);
  const status = getAnswerStatus(result);
  const sections = parseAnswerSections(displayText);
  const flowSteps = buildNextStepFlow(result, actions);

  if (!displayText && !actions.length && !flowSteps.length) return null;

  return (
    <div className="card answer-card-v2">
      <div className="card-header answer-card-header">
        <div>
          <div className="card-title">Answer</div>
          <div className="answer-subtitle">First-pass plan, key decisions, and next steps</div>
        </div>
        <Badge status={status} />
      </div>

      <div className="card-body">
        <div className="answer-layout">
          <div className="answer-main">
            {sections.map((section, index) => (
              <AnswerSection section={section} key={`${section.title}-${index}`} />
            ))}
          </div>

          <AnswerFlow steps={flowSteps} />
        </div>
      </div>
    </div>
  );
}
