import { Link } from "react-router-dom";
import { useStore } from "../store.jsx";

export default function ResultGate({ children }) {
  const { result } = useStore();

  if (!result) {
    return (
      <div className="card">
        <div className="card-body">
          <div className="empty-state">
            <div className="icon">📭</div>
            <p style={{ marginBottom: 12 }}>
              No shipment has been processed yet. Run a request from the Dashboard to populate this
              page with live backend data.
            </p>
            <Link to="/" className="btn btn-primary" style={{ display: "inline-flex" }}>
              Go to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return children(result);
}
