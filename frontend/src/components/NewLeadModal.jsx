import React, { useState } from "react";
import api from "../api/client.js";
import toast from "react-hot-toast";

const STAGES = [
  { value: "new", label: "Новая заявка" },
  { value: "no_answer", label: "Не дозвонились" },
  { value: "contacted", label: "Первичный контакт" },
  { value: "qualified", label: "Квалификация" },
  { value: "selection", label: "Подбор объекта" },
  { value: "showing_scheduled", label: "Показ назначен" },
  { value: "showing_done", label: "Показ проведён" },
  { value: "booking", label: "Бронь / Аванс" },
  { value: "documents", label: "Документы / Ипотека" },
  { value: "won", label: "Сделка" },
  { value: "lost", label: "Отказ / Архив" },
];

const SOURCES = [
  { value: "manual", label: "Вручную" },
  { value: "website", label: "Сайт" },
  { value: "avito", label: "Авито" },
  { value: "telegram", label: "Telegram" },
  { value: "vk", label: "ВКонтакте" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "instagram", label: "Instagram" },
  { value: "partners", label: "Партнёры" },
  { value: "referral", label: "Рекомендация" },
];

const TAGS = ["Горячий", "VIP", "Ипотека", "Инвестор", "Срочно", "Повторный", "Семья", "Корпоратив"];

export default function NewLeadModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: "",
    phone: "",
    email: "",
    source: "manual",
    stage: "new",
    budget: "",
    tags: [],
    next_action: "",
    next_date: "",
    notes: "",
  });
  const [loading, setLoading] = useState(false);

  function set(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function toggleTag(tag) {
    setForm((prev) => ({
      ...prev,
      tags: prev.tags.includes(tag) ? prev.tags.filter((t) => t !== tag) : [...prev.tags, tag],
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/leads", {
        ...form,
        budget: form.budget ? parseInt(form.budget) : null,
        next_date: form.next_date || null,
        next_action: form.next_action || null,
        notes: form.notes || null,
      });
      toast.success("Лид создан");
      onCreated();
    } catch {
      toast.error("Ошибка при создании");
    } finally {
      setLoading(false);
    }
  }

  const inputClass = "w-full border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 placeholder:text-slate-400";
  const labelClass = "text-xs font-semibold text-slate-400 dark:text-slate-500 mb-1 block";

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center p-0 md:p-4" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="bg-white dark:bg-slate-800 rounded-t-3xl md:rounded-2xl shadow-2xl w-full max-w-md max-h-[92vh] overflow-auto border border-slate-100 dark:border-slate-700">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-700 sticky top-0 bg-white dark:bg-slate-800 z-10">
          <div>
            <h3 className="font-bold text-lg text-slate-900 dark:text-slate-100">Новый лид</h3>
            <p className="text-xs text-slate-400 dark:text-slate-500">Score посчитается автоматически</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 text-xl">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className={labelClass}>Имя *</label>
            <input required placeholder="Иван Иванов" value={form.name} onChange={(e) => set("name", e.target.value)} className={inputClass} />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Телефон</label>
              <input placeholder="+7..." value={form.phone} onChange={(e) => set("phone", e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Email</label>
              <input placeholder="email@mail.ru" type="email" value={form.email} onChange={(e) => set("email", e.target.value)} className={inputClass} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Источник</label>
              <select value={form.source} onChange={(e) => set("source", e.target.value)} className={inputClass}>
                {SOURCES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
            <div>
              <label className={labelClass}>Стадия</label>
              <select value={form.stage} onChange={(e) => set("stage", e.target.value)} className={inputClass}>
                {STAGES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className={labelClass}>Бюджет (₽)</label>
            <input placeholder="3000000" type="number" value={form.budget} onChange={(e) => set("budget", e.target.value)} className={inputClass} />
          </div>

          <div>
            <label className={labelClass}>Теги</label>
            <div className="flex flex-wrap gap-1.5">
              {TAGS.map((tag) => {
                const active = form.tags.includes(tag);
                return (
                  <button key={tag} type="button" onClick={() => toggleTag(tag)}
                    className={`text-xs px-2.5 py-1 rounded-full font-semibold border transition ${
                      active
                        ? "bg-indigo-600 text-white border-indigo-600"
                        : "bg-slate-50 dark:bg-slate-700 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-600 hover:border-indigo-400"
                    }`}>
                    {tag}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label className={labelClass}>Следующее действие</label>
            <input placeholder="Позвонить, назначить показ, отправить подборку..." value={form.next_action} onChange={(e) => set("next_action", e.target.value)} className={inputClass} />
          </div>

          <div>
            <label className={labelClass}>Дата следующего действия</label>
            <input type="datetime-local" value={form.next_date} onChange={(e) => set("next_date", e.target.value)} className={inputClass} />
          </div>

          <div>
            <label className={labelClass}>Заметки</label>
            <textarea placeholder="Что важно знать о клиенте..." rows={3} value={form.notes} onChange={(e) => set("notes", e.target.value)} className={`${inputClass} resize-none`} />
          </div>

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose}
              className="flex-1 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-xl py-2.5 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-700 transition">
              Отмена
            </button>
            <button type="submit" disabled={loading}
              className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl py-2.5 text-sm font-semibold transition disabled:opacity-60">
              {loading ? "Создаём..." : "Создать"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
