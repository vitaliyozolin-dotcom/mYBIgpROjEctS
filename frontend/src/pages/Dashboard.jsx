import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { ru } from "date-fns/locale";
import api from "../api/client.js";

const STAGE_LABELS = {
  new: "Новые", contacted: "Связались", qualified: "Квалифицированы",
  proposal: "Предложение", negotiation: "Переговоры", won: "Сделка", lost: "Отказ",
};

const SOURCE_LABELS = {
  manual: "Вручную", website: "Сайт", avito: "Авито",
  telegram: "Telegram", vk: "ВКонтакте", whatsapp: "WhatsApp", instagram: "Instagram",
};

function StatCard({ label, value, sub, color }) {
  return (
    <div className={`bg-white rounded-2xl p-5 border border-slate-100 shadow-sm`}>
      <p className="text-slate-500 text-sm mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color || "text-slate-900"}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function Dashboard() {
  const [leads, setLeads] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/leads").then((r) => setLeads(r.data)).catch(() => {});
  }, []);

  const total = leads.length;
  const won = leads.filter((l) => l.stage === "won").length;
  const active = leads.filter((l) => !["won", "lost"].includes(l.stage)).length;
  const totalValue = leads.filter((l) => l.stage === "won" && l.budget).reduce((s, l) => s + l.budget, 0);
  const conversion = total > 0 ? Math.round((won / total) * 100) : 0;
  const recent = [...leads].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Главная</h1>
        <p className="text-slate-500 text-sm mt-1">Обзор продаж в реальном времени</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Всего лидов" value={total} sub="за всё время" />
        <StatCard label="Активных" value={active} sub="в работе" color="text-indigo-600" />
        <StatCard label="Конверсия" value={`${conversion}%`} sub="из лидов в сделки" color={conversion >= 20 ? "text-emerald-600" : "text-amber-600"} />
        <StatCard
          label="Сумма сделок"
          value={totalValue > 0 ? `${(totalValue / 1_000_000).toFixed(1)}M ₽` : "—"}
          sub="закрытые сделки"
          color="text-emerald-600"
        />
      </div>

      {/* Recent leads */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden mb-6">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800">Последние лиды</h2>
          <button onClick={() => navigate("/board")} className="text-sm text-indigo-600 hover:underline">
            Открыть воронку →
          </button>
        </div>
        {recent.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-sm">Лидов пока нет</div>
        ) : (
          <div className="divide-y divide-slate-50">
            {recent.map((lead) => (
              <div
                key={lead.id}
                onClick={() => navigate(`/leads/${lead.id}`)}
                className="flex items-center gap-4 px-5 py-3.5 hover:bg-slate-50 cursor-pointer transition"
              >
                <div className="w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 font-bold text-sm flex items-center justify-center shrink-0">
                  {lead.name[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900 text-sm truncate">{lead.name}</p>
                  <p className="text-xs text-slate-400">{SOURCE_LABELS[lead.source] || lead.source}</p>
                </div>
                <div className="text-right shrink-0">
                  <StageBadge stage={lead.stage} />
                  <p className="text-xs text-slate-400 mt-1">
                    {formatDistanceToNow(new Date(lead.created_at), { locale: ru, addSuffix: true })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick actions */}
      <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-5">
        <h3 className="font-semibold text-indigo-900 mb-3">Быстрые действия</h3>
        <div className="flex flex-wrap gap-3">
          <button onClick={() => navigate("/board")} className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition">
            + Новый лид
          </button>
          <button onClick={() => navigate("/analytics")} className="bg-white border border-indigo-200 text-indigo-700 text-sm font-semibold px-4 py-2 rounded-lg hover:bg-indigo-50 transition">
            Смотреть аналитику
          </button>
        </div>
      </div>
    </div>
  );
}

function StageBadge({ stage }) {
  const colors = {
    new: "bg-slate-100 text-slate-600",
    contacted: "bg-blue-100 text-blue-700",
    qualified: "bg-yellow-100 text-yellow-700",
    proposal: "bg-orange-100 text-orange-700",
    negotiation: "bg-purple-100 text-purple-700",
    won: "bg-emerald-100 text-emerald-700",
    lost: "bg-red-100 text-red-600",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${colors[stage] || colors.new}`}>
      {STAGE_LABELS[stage] || stage}
    </span>
  );
}
