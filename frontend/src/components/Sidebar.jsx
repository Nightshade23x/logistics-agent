import { NavLink } from "react-router-dom";
import { useStore } from "../store.jsx";

const NAV = [
  {
    label: "Plan",
    items: [
      { to: "/", label: "Start a Shipment", icon: "🏠", end: true },
      { to: "/shipments", label: "Shipment Plan", icon: "📦" },
      { to: "/container-planning", label: "Loading Plan", icon: "🚢" },
    ],
  },
  {
    label: "Prepare",
    items: [
      { to: "/procurement", label: "Suppliers & Buying", icon: "🛒" },
      { to: "/compliance", label: "Rules & Documents", icon: "📄" },
      { to: "/integrations", label: "Carrier Connections", icon: "🔌" },
    ],
  },
  {
    label: "Review",
    items: [
      { to: "/reports", label: "Saved Reports", icon: "📊" },
      { to: "/partner-agents", label: "System Details", icon: "🤝", advancedOnly: true },
    ],
  },
];

export default function Sidebar() {
  const { userView } = useStore();

  return (
    <aside className="sidebar">
      <nav aria-label="Main navigation">
        {NAV.map((group) => {
          const visibleItems = group.items.filter((item) => !item.advancedOnly || userView === "advanced");
          if (!visibleItems.length) return null;

          return (
            <div className="side-section" key={group.label}>
              <div className="side-label">{group.label}</div>
              {visibleItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  title={item.label}
                  className={({ isActive }) => `side-item${isActive ? " active" : ""}`}
                >
                  <span className="icon" aria-hidden="true">{item.icon}</span>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
