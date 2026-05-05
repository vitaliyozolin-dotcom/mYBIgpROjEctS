import React, { useState, useEffect } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

const SOURCE_OPTIONS = [
  { value: "website", label: "Сайт" },
  { value: "avito", label: "Авито" },
  { value: "vk", label: "ВКонтакте" },
  { value: "instagram", label: "Instagram" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "telegram", label: "Telegram" },
];

function getUtmParams() {
  const params = new URLSearchParams(window.location.search);
  return {
    utm_source: params.get("utm_source") || "",
    utm_medium: params.get("utm_medium") || "",
    utm_campaign: params.get("utm_campaign") || "",
  };
}

export default function PublicForm() {
  const [form, setForm] = useState({ name: "", phone: "", email: "", source: "website", notes: "" });
  const [utms, setUtms] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const isEmbed = new URLSearchParams(window.location.search).get("embed") === "1";

  useEffect(() => {
    setUtms(getUtmParams());
    const src = new URLSearchParams(window.location.search).get("source");
    if (src) setForm((f) => ({ ...f, source: src }));
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const payload = {
        name: form.name,
        phone: form.phone || null,
        email: form.email || null,
        source: form.source,
        notes: form.notes || null,
        ...utms,
      };
      const res = await fetch(`${API_BASE}/webhooks/lead`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Ошибка сервера");
      setSubmitted(true);
      if (window.ym) {
        window.ym(window._ym_counter, "reachGoal", "lead_form_submit");
      }
      if (window.parent !== window) {
        window.parent.postMessage({ type: "crm_lead_submitted", name: form.name }, "*");
      }
    } catch {
      setError("Не удалось отправить заявку. Попробуйте позже.");
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className={`${isEmbed ? "min-h-0" : "min-h-screen bg-slate-50 flex items-center justify-center p-4"}`}>
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-slate-100 text-center max-w-sm w-full mx-auto">
          <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">✓</span>
          </div>
          <h2 className="font-bold text-slate-900 text-xl mb-2">Заявка принята!</h2>
          <p className="text-slate-500 text-sm">
            Мы свяжемся с вами в ближайшее время для обсуждения деталей.
          </p>
          <button
            onClick={() => setSubmitted(false)}
            className="mt-5 text-xs text-slate-400 hover:underline"
          >
            Отправить ещё одну заявку
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`${isEmbed ? "min-h-0" : "min-h-screen bg-slate-50 flex items-center justify-center p-4"}`}>
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 max-w-md w-full mx-auto">
        {!isEmbed && (
          <div className="px-6 pt-6 pb-2">
            <h1 className="font-bold text-slate-900 text-xl">Получить консультацию</h1>
            <p className="text-slate-500 text-sm mt-1">
              Готовый арендный бизнес от 2 млн ₽ · окупаемость 6–7 лет
            </p>
          </div>
        )}
        {isEmbed && (
          <div className="px-5 pt-5 pb-1">
            <h2 className="font-bold text-slate-900 text-lg">Оставить заявку</h2>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-5 space-y-3">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">Ваше имя *</label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Иван Петров"
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500 mb-1 block">Телефон</label>
            <input
              type="tel"
              value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
              placeholder="+7 (999) 000-00-00"
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500 mb-1 block">Email</label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              placeholder="ivan@example.com"
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500 mb-1 block">Откуда узнали о нас?</label>
            <select
              value={form.source}
              onChange={(e) => setForm((f) => ({ ...f, source: e.target.value }))}
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            >
              {SOURCE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs text-slate-500 mb-1 block">Комментарий (необязательно)</label>
            <textarea
              rows={2}
              value={form.notes}
              onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              placeholder="Интересует объект от 5 млн ₽..."
              className="w-full border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none"
            />
          </div>

          {error && <p className="text-xs text-red-500 text-center">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-indigo-600 text-white py-3 rounded-xl text-sm font-bold hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {loading ? "Отправка..." : "Отправить заявку"}
          </button>

          <p className="text-xs text-slate-400 text-center">
            Нажимая кнопку, вы соглашаетесь на обработку персональных данных
          </p>
        </form>
      </div>
    </div>
  );
}
