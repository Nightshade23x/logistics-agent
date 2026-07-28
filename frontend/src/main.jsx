// DASHBOARD_CURRENT_WORKSPACE_RESET_V1
try {
  localStorage.removeItem("meridian.dashboard.mode");
  localStorage.removeItem("meridian.dashboard.text");
  localStorage.removeItem("meridian.dashboard.json");
  // Keep the current result available to other open tabs.
} catch {
  // Browser storage unavailable; continue normally.
}

import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { StoreProvider } from "./store.jsx";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <StoreProvider>
        <App />
      </StoreProvider>
    </BrowserRouter>
  </React.StrictMode>
);
