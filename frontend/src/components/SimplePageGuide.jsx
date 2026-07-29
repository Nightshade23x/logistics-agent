import { useStore } from "../store.jsx";
// EMPTY_STATE_SIMPLE_TABS_V38
export default function SimplePageGuide({ title, children, items = [] }) {
  const { userView } = useStore();
  if (userView !== "simple") return null;
  return <section className="simple-page-guide" role="note"><div><strong>{title}</strong>{children && <p>{children}</p>}</div>{items.length > 0 && <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>}</section>;
}
