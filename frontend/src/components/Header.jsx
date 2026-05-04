import React from "react";
import { useNavigate } from "react-router-dom";

export default function Header({ title }) {
  const navigate = useNavigate();

  function logout() {
    localStorage.removeItem("token");
    navigate("/login");
  }

  return (
    <header className="bg-blue-900 text-white px-6 py-4 flex items-center justify-between shadow-md">
      <div className="flex items-center gap-3">
        <span
          className="text-xl font-bold cursor-pointer hover:opacity-80"
          onClick={() => navigate("/")}
        >
          CRM
        </span>
        {title && <span className="text-blue-300 text-sm">/ {title}</span>}
      </div>
      <button
        onClick={logout}
        className="text-sm text-blue-200 hover:text-white transition"
      >
        Выйти
      </button>
    </header>
  );
}
