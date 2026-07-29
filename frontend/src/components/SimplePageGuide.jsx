import { useStore } from "../store.jsx";

const TERM_HELP = {
  "cbm": "Cubic metres: the amount of space the packed cargo takes up.",
  "fcl": "Full container load: one shipment uses a whole container.",
  "lcl": "Less than container load: cargo shares container space with other shipments.",
  "payload": "The maximum cargo weight a container or vehicle can safely carry.",
  "fit check": "A planning check of whether the cargo appears to fit within the selected container limits.",
  "incoterm": "A standard trade term that divides transport tasks, costs, and risk between buyer and seller.",
  "cif": "Cost, Insurance and Freight: the seller arranges main carriage and minimum insurance to the named port, but risk can transfer earlier.",
  "landed cost": "The estimated total cost after purchase price, freight, insurance, duties, taxes, brokerage, and local delivery.",
  "ready for review": "The first plan is useful, but a person or connected specialist still needs to confirm it.",
  "ready to book": "The required details and checks appear complete enough to approach a carrier for booking.",
  "live api": "A result retrieved directly from a connected provider service.",
  "demo estimate": "A test calculation that is not a live or bookable carrier price.",
};

// EMPTY_STATE_SIMPLE_TABS_V38
// EASE_OF_ACCESS_GUIDED_WORKFLOW_V39
export default function SimplePageGuide({ title, children, items = [], terms = [] }) {
  const { userView } = useStore();
  if (userView !== "simple") return null;

  return (
    <section className="simple-page-guide" role="note">
      <div>
        <strong>{title}</strong>
        {children && <p>{children}</p>}
        {terms.length > 0 && (
          <div className="plain-language-terms" aria-label="Plain-language logistics terms">
            <span>Terms on this page</span>
            <div>
              {terms.map((term) => (
                <details key={term}>
                  <summary>{term}</summary>
                  <p>{TERM_HELP[String(term).toLowerCase()] || "This term is explained in the result where it is used."}</p>
                </details>
              ))}
            </div>
          </div>
        )}
      </div>
      {items.length > 0 && <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>}
    </section>
  );
}
