import { Link } from "react-router-dom";
import { useStore } from "../store.jsx";
// EMPTY_STATE_SIMPLE_TABS_V38
export default function ResultGate({ children }) {
  const { result, userView } = useStore();
  if (!result) return <div className="card"><div className="card-body"><div className="empty-state empty-state-v38">
    <div className="icon">📭</div><strong>No shipping plan yet</strong>
    <p>{userView === "simple" ? "Start on the Shipping Assistant page, enter your own request, and press Create my shipping plan." : "No active result exists in this session. Run a request or deliberately open one from Recent Requests."}</p>
    <p className="empty-state-note">Example text shown inside an empty request box is only a hint. It is never submitted automatically.</p>
    <Link to="/" className="btn btn-primary" style={{ display: "inline-flex" }}>Open Shipping Assistant</Link>
  </div></div></div>;
  return children(result);
}
