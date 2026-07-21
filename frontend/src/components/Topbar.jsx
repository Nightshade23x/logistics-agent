import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function Topbar() {
  const [online, setOnline] = useState(null);

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then(() => !cancelled && setOnline(true))
      .catch(() => !cancelled && setOnline(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">ML</div>
        <div>
          <div className="brand-text">Meridian Logistics</div>
          <div className="brand-sub">Cargo Operations Console</div>
        </div>
      </div>
      <div className="topbar-right">
        <span className="env-badge">
          {online === null ? "CHECKING API…" : online ? "API CONNECTED" : "API OFFLINE"}
        </span>
        <div className="user-chip">
          <div className="user-avatar">OP</div>
          <span>Operations</span>
        </div>
      </div>
    </header>
  );
}
