import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { ru } from "date-fns/locale";
import api from "../api/client.js";

const STAGE_LABELS = {
  new: "Новый", contacted: "Связались", qualified: "Квалифицирован",
  proposal: "Предложение", negotiation: "Переговоры", won: "Сделка", lost: "Отказ",
};
const STAGE_COLORS = {
  new: "bg-slate-100 text-slate-600", contacted: "bg-blue-100 text-blue-700",
  qualified: "bg-yellow-100 text-yellow-700", proposal: "bg-orange-100 text-orange-700",
  negotiation: "bg-purple-100 text-purple-700", won: "bg-emerald-100 text-emerald-700",
  lost: "bg-red-100 text-red-600",
};
const SOURCE_LABELS = {
  manual: "Вручную", website: "Сайт", avito: "Авито",
  telegram: "Telegram", vk: "ВКонтакте", whatsapp: "WhatsApp", instagram: "Instagram",
};

export default function Dashboard() {
  const [leads, setLeads] = useState([]);
  const navigate = useNavigate();

  useEffect(() => { api.get("/leads").then((r) => setLeads(r.data)).catch(() => {}); }, []);

  const total = leads.length;
  const won = leads.filter((l) => l.stage === "won").length;
  const active = leads.filter((l) => !["won", "lost"].includes(l.stage)).length;
  const wonValue = leads.filter((l) => l.stage === "won" && l.budget).reduce((s, l) => s + l.budget, 0);
  const conversion = total > 0 ? Math.round((won / total) * 100) : 0;
  const recent = [...leads].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 8);

  return (
    <div className="p-4 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-5 pt-1">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Главная</h1>
          <p className="text-slate-400 text-xs mt-0.5">Инвест Недвижимость</p>
        </div>
        <button
          onClick={() => navigate("/board")}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-xl transition"
        >
          + Лид
        </button>
      </div>

      {/* Stats 2x2 */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        <StatCard label="Лидов" value={total} color="text-slate-900" />
        <StatCard label="В работе" value={active} color="text-indigo-600" />
        <StatCard label="Конверсия" value={`${conversion}%`} color={conversion >= 20 ? "text-emerald-600" : "text-amber-600"} />
        <StatCard
          label="Сумма сделок"
          value={wonValue > 0 ? `${(wonValue / 1_000_000).toFixed(1)}M ₽` : "—"}
          color="text-emerald-600"
        />
      </div>

      {/* Recent leads */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800 text-sm">Последние лиды</h2>
          <button onClick={() => navigate("/board")} className="text-xs text-indigo-600">Все →</button>
        </div>
        {recent.length === 0 ? (
          <div className="py-10 text-center">
            <p className="text-slate-400 text-sm">Лидов пока нет</p>
            <button onClick={() => navigate("/board")} className="mt-3 text-sm text-indigo-600 font-semibold">
              Добавить первый лид
            </button>
          </div>
        ) : (
          <div className="divide-y divide-slate-50">
            {recent.map((lead) => (
              <div
                key={lead.id}
                onClick={() => navigate(`/leads/${lead.id}`)}
                className="flex items-center gap-3 px-4 py-3 active:bg-slate-50 cursor-pointer"
              >
                <div className="w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 font-bold text-sm flex items-center justify-center shrink-0">
                  {lead.name[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 text-sm truncate">{lead.name}</p>
                  <p className="text-xs text-slate-400 truncate">
                    {SOURCE_LABELS[lead.source] || lead.source} · {formatDistanceToNow(new Date(lead.created_at), { locale: ru, addSuffix: true })}
                  </p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${STAGE_COLORS[lead.stage]}`}>
                  {STAGE_LABELS[lead.stage]}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, color }) {
  return (
    <div className="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm">
      <p className="text-slate-400 text-xs mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}
