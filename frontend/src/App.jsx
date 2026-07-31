import { Routes, Route } from "react-router-dom";
import Topbar from "./components/Topbar.jsx";
import Sidebar from "./components/Sidebar.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Shipments from "./pages/Shipments.jsx";
import ContainerPlanning from "./pages/ContainerPlanning.jsx";
import Procurement from "./pages/Procurement.jsx";
import Compliance from "./pages/Compliance.jsx";
import PartnerAgents from "./pages/PartnerAgents.jsx";
import Reports from "./pages/Reports.jsx";
import Integrations from "./pages/Integrations.jsx";

export default function App() {
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <Topbar />
      <div className="app">
        <Sidebar />
        <main id="main-content" className="main" tabIndex="-1">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/shipments" element={<Shipments />} />
            <Route path="/container-planning" element={<ContainerPlanning />} />
            <Route path="/procurement" element={<Procurement />} />
            <Route path="/compliance" element={<Compliance />} />
            <Route path="/partner-agents" element={<PartnerAgents />} />
            <Route path="/integrations" element={<Integrations />} />
            <Route path="/reports" element={<Reports />} />
          </Routes>
        </main>
      </div>
      <div className="footer-bar">Meridian Logistics Console · powered by the Logistics Agent backend</div>
    </>
  );
}
