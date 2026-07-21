import { NavLink } from "react-router-dom";

const NAV = [
  {
    label: "Workspace",
    items: [
      { to: "/", label: "Dashboard", icon: "🏠", end: true },
      { to: "/shipments", label: "Shipments", icon: "📦" },
      { to: "/container-planning", label: "Container Planning", icon: "🚢" },
    ],
  },
  {
    label: "Trade",
    items: [
      { to: "/procurement", label: "Procurement", icon: "🛒" },
      { to: "/compliance", label: "Compliance & Docs", icon: "📄" },
      { to: "/partner-agents", label: "Partner Agents", icon: "🤝" },
    ],
  },
  {
    label: "Insights",
    items: [{ to: "/reports", label: "Reports", icon: "📊" }],
  },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      {NAV.map((group) => (
        <div className="side-section" key={group.label}>
          <div className="side-label">{group.label}</div>
          {group.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `side-item${isActive ? " active" : ""}`}
            >
              <span className="icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </div>
      ))}
    </aside>
  );
}
