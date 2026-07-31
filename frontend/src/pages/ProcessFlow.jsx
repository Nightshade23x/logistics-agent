// PROCESS_FLOW_TAB_V67
import AnswerFlow from "../components/AnswerFlow.jsx";
import ResultGate from "../components/ResultGate.jsx";
import SimplePageGuide from "../components/SimplePageGuide.jsx";
import ViewControls from "../components/ViewControls.jsx";
import { useStore } from "../store.jsx";

export default function ProcessFlow() {
  const { userView } = useStore();

  return (
    <>
      <div className="page-header">
        <div>
          <div className="page-title">{userView === "simple" ? "Shipment process flow" : "Dynamic Process Flow"}</div>
          <div className="page-subtitle">Follow the shipment from request intake through route, compliance, documents, insurance, cost checks and booking readiness.</div>
        </div>
        <ViewControls compact />
      </div>

      <SimplePageGuide
        title="How to use this flow"
        terms={["Process", "Decision", "Document", "Blocked"]}
        items={[
          "Rectangles show work that must be completed.",
          "Diamonds show decisions or readiness gates.",
          "Blocked steps must be resolved before booking.",
        ]}
      >
        The flow updates automatically whenever a new shipment result is created.
      </SimplePageGuide>

      <ResultGate>
        {(result) => <div className="process-flow-page-v67"><AnswerFlow result={result} /></div>}
      </ResultGate>
    </>
  );
}
