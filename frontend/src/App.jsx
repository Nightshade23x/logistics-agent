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

export default function App() {
  return (
    <>
      <Topbar />
      <div className="app">
        <Sidebar />
        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/shipments" element={<Shipments />} />
            <Route path="/container-planning" element={<ContainerPlanning />} />
            <Route path="/procurement" element={<Procurement />} />
            <Route path="/compliance" element={<Compliance />} />
            <Route path="/partner-agents" element={<PartnerAgents />} />
            <Route path="/reports" element={<Reports />} />
          </Routes>
        </main>
      </div>
      <div className="footer-bar">Meridian Logistics Console · powered by the Logistics Agent backend</div>
    </>
  );
}
