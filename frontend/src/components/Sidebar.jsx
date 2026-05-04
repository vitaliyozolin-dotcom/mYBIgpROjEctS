import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

const NAV = [
  { to: "/", label: "Главная", icon: "⊞", exact: true },
  { to: "/board", label: "Воронка", icon: "◫" },
  { to: "/analytics", label: "Аналитика", icon: "↗" },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  function logout() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  return (
    <aside className={`flex flex-col bg-slate-900 text-slate-300 transition-all duration-200 ${collapsed ? "w-16" : "w-56"} shrink-0`}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-800">
        <div className="w-8 h-8 bg-indigo-500 rounded-lg flex items-center justify-center text-white font-bold text-sm shrink-0">
          C
        </div>
        {!collapsed && (
          <div>
            <p className="text-white font-semibold text-sm leading-none">CRM</p>
            <p className="text-slate-500 text-xs mt-0.5">Инвест Недвижимость</p>
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="ml-auto text-slate-600 hover:text-slate-300 transition text-xs"
        >
          {collapsed ? "▶" : "◀"}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 space-y-1 px-2">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.exact}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`
            }
          >
            <span className="text-base w-5 text-center shrink-0">{item.icon}</span>
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div className="p-2 border-t border-slate-800">
        <button
          onClick={logout}
          className="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm text-slate-500 hover:bg-slate-800 hover:text-slate-300 transition"
        >
          <span className="text-base w-5 text-center shrink-0">⎋</span>
          {!collapsed && <span>Выйти</span>}
        </button>
      </div>
    </aside>
  );
}
