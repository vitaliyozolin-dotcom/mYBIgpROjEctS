import React from "react";
import { NavLink, useNavigate } from "react-router-dom";

const ITEMS = [
  { to: "/", label: "Главная", icon: "⊞", exact: true },
  { to: "/board", label: "Воронка", icon: "◫" },
  { to: "/analytics", label: "Аналитика", icon: "↗" },
];

export default function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 flex z-50 safe-area-bottom">
      {ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.exact}
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center justify-center py-2.5 gap-0.5 transition-colors ${
              isActive ? "text-indigo-600" : "text-slate-400"
            }`
          }
        >
          <span className="text-xl leading-none">{item.icon}</span>
          <span className="text-[10px] font-medium">{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
