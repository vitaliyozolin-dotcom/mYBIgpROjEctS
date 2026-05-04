import React, { useState } from "react";
import api from "../api/client.js";
import toast from "react-hot-toast";

export default function NewLeadModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: "", phone: "", email: "", source: "manual", budget: "", notes: "" });
  const [loading, setLoading] = useState(false);

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/leads", {
        ...form,
        budget: form.budget ? parseInt(form.budget) : null,
      });
      toast.success("Лид создан");
      onCreated();
    } catch {
      toast.error("Ошибка при создании");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h3 className="font-bold text-lg">Новый лид</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <input required placeholder="Имя *" value={form.name} onChange={(e) => set("name", e.target.value)}
            className="w-full border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <input placeholder="Телефон" value={form.phone} onChange={(e) => set("phone", e.target.value)}
            className="w-full border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <input placeholder="Email" type="email" value={form.email} onChange={(e) => set("email", e.target.value)}
            className="w-full border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <select value={form.source} onChange={(e) => set("source", e.target.value)}
            className="w-full border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="manual">Вручную</option>
            <option value="website">Сайт</option>
            <option value="avito">Авито</option>
            <option value="telegram">Telegram</option>
            <option value="vk">ВКонтакте</option>
            <option value="whatsapp">WhatsApp</option>
            <option value="instagram">Instagram</option>
          </select>
          <input placeholder="Бюджет (₽)" type="number" value={form.budget} onChange={(e) => set("budget", e.target.value)}
            className="w-full border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          <textarea placeholder="Заметки" rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)}
            className="w-full border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 border border-gray-300 rounded-lg py-2.5 text-sm font-medium hover:bg-gray-50 transition">
              Отмена
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 bg-blue-800 hover:bg-blue-900 text-white rounded-lg py-2.5 text-sm font-semibold transition disabled:opacity-60">
              {loading ? "Создаём..." : "Создать"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
