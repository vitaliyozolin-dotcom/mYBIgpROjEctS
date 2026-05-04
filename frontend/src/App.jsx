import React from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import Login from "./pages/Login.jsx";
import Board from "./pages/Board.jsx";
import LeadDetail from "./pages/LeadDetail.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Analytics from "./pages/Analytics.jsx";
import Sidebar from "./components/Sidebar.jsx";

function PrivateRoute({ children }) {
  return localStorage.getItem("token") ? children : <Navigate to="/login" replace />;
}

function AppLayout({ children }) {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  );
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<PrivateRoute><AppLayout><Dashboard /></AppLayout></PrivateRoute>} />
        <Route path="/board" element={<PrivateRoute><AppLayout><Board /></AppLayout></PrivateRoute>} />
        <Route path="/leads/:id" element={<PrivateRoute><AppLayout><LeadDetail /></AppLayout></PrivateRoute>} />
        <Route path="/analytics" element={<PrivateRoute><AppLayout><Analytics /></AppLayout></PrivateRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toaster position="top-right" toastOptions={{ style: { borderRadius: "10px", fontSize: "14px" } }} />
    </>
  );
}
