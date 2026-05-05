import React, { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { useTheme } from "../context/ThemeContext.jsx";
import api from "../api/client.js";

const BASE_ITEMS = [
  { to: "/", label: "Главная", icon: "⊞", exact: true },
  { to: "/board", label: "Воронка", icon: "◫" },
  { to: "/analytics", label: "Аналитика", icon: "↗" },
];

const ADMIN_ITEM = { to: "/users", label: "Команда", icon: "👤" };

export default function BottomNav() {
  const { dark, toggle } = useTheme();
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    api.get("/auth/me").then(({ data }) => setIsAdmin(data.role === "admin")).catch(() => {});
  }, []);

  const items = isAdmin ? [...BASE_ITEMS, ADMIN_ITEM] : BASE_ITEMS;

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 flex z-50">
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} end={item.exact}
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center justify-center py-2.5 gap-0.5 transition-colors ${
              isActive ? "text-indigo-600 dark:text-indigo-400" : "text-slate-400 dark:text-slate-500"
            }`
          }>
          <span className="text-xl leading-none">{item.icon}</span>
          <span className="text-[10px] font-medium">{item.label}</span>
        </NavLink>
      ))}
      {/* Theme toggle as last item */}
      <button onClick={toggle}
        className="flex-1 flex flex-col items-center justify-center py-2.5 gap-0.5 text-slate-400 dark:text-slate-500 transition-colors hover:text-slate-600 dark:hover:text-slate-300">
        <span className="text-xl leading-none">{dark ? "☀️" : "🌙"}</span>
        <span className="text-[10px] font-medium">{dark ? "Светлая" : "Тёмная"}</span>
      </button>
    </nav>
  );
}
