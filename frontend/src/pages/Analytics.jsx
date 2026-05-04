import React, { useEffect, useState } from "react";
import api from "../api/client.js";

const STAGES = [
  { id: "new", label: "Новые", color: "bg-slate-400" },
  { id: "contacted", label: "Связались", color: "bg-blue-400" },
  { id: "qualified", label: "Квалифицированы", color: "bg-yellow-400" },
  { id: "proposal", label: "Предложение", color: "bg-orange-400" },
  { id: "negotiation", label: "Переговоры", color: "bg-purple-400" },
  { id: "won", label: "Сделки", color: "bg-emerald-500" },
  { id: "lost", label: "Отказы", color: "bg-red-400" },
];

const SOURCE_LABELS = {
  manual: "Вручную", website: "Сайт", avito: "Авито",
  telegram: "Telegram", vk: "ВКонтакте", whatsapp: "WhatsApp", instagram: "Instagram",
};

export default function Analytics() {
  const [leads, setLeads] = useState([]);

  useEffect(() => {
    api.get("/leads").then((r) => setLeads(r.data)).catch(() => {});
  }, []);

  const total = leads.length;
  const won = leads.filter((l) => l.stage === "won").length;
  const lost = leads.filter((l) => l.stage === "lost").length;
  const active = leads.filter((l) => !["won", "lost"].includes(l.stage)).length;
  const conversion = total > 0 ? ((won / total) * 100).toFixed(1) : 0;
  const wonValue = leads.filter((l) => l.stage === "won" && l.budget).reduce((s, l) => s + l.budget, 0);
  const avgDeal = won > 0 ? Math.round(wonValue / won) : 0;

  // By stage
  const byStage = STAGES.map((s) => ({
    ...s,
    count: leads.filter((l) => l.stage === s.id).length,
    value: leads.filter((l) => l.stage === s.id && l.budget).reduce((sum, l) => sum + l.budget, 0),
  }));
  const maxCount = Math.max(...byStage.map((s) => s.count), 1);

  // By source
  const sourceCounts = {};
  leads.forEach((l) => { sourceCounts[l.source] = (sourceCounts[l.source] || 0) + 1; });
  const bySource = Object.entries(sourceCounts).sort((a, b) => b[1] - a[1]);
  const maxSource = Math.max(...bySource.map((s) => s[1]), 1);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Аналитика</h1>
        <p className="text-slate-500 text-sm mt-1">Конверсия и эффективность воронки</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Всего лидов", value: total, color: "text-slate-900" },
          { label: "Конверсия", value: `${conversion}%`, color: "text-indigo-600" },
          { label: "Закрыто сделок", value: won, color: "text-emerald-600" },
          { label: "Средний чек", value: avgDeal > 0 ? `${(avgDeal / 1_000_000).toFixed(1)}M ₽` : "—", color: "text-emerald-600" },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
            <p className="text-slate-500 text-sm mb-1">{kpi.label}</p>
            <p className={`text-3xl font-bold ${kpi.color}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Funnel */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 mb-6">
        <h2 className="font-semibold text-slate-800 mb-4">Воронка по стадиям</h2>
        {total === 0 ? (
          <p className="text-slate-400 text-sm">Нет данных</p>
        ) : (
          <div className="space-y-3">
            {byStage.map((stage) => (
              <div key={stage.id}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${stage.color}`} />
                    <span className="text-sm text-slate-700 font-medium">{stage.label}</span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-slate-500">{stage.count} лидов</span>
                    {stage.value > 0 && (
                      <span className="text-emerald-600 font-medium">{stage.value.toLocaleString("ru-RU")} ₽</span>
                    )}
                    {total > 0 && (
                      <span className="text-slate-400 w-10 text-right">{Math.round((stage.count / total) * 100)}%</span>
                    )}
                  </div>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${stage.color}`}
                    style={{ width: `${(stage.count / maxCount) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* By source */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 mb-6">
        <h2 className="font-semibold text-slate-800 mb-4">Источники лидов</h2>
        {bySource.length === 0 ? (
          <p className="text-slate-400 text-sm">Нет данных</p>
        ) : (
          <div className="space-y-3">
            {bySource.map(([source, count]) => (
              <div key={source}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-slate-700">{SOURCE_LABELS[source] || source}</span>
                  <span className="text-sm font-semibold text-slate-800">{count}</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-indigo-400 transition-all"
                    style={{ width: `${(count / maxSource) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info block */}
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5">
        <h3 className="font-semibold text-amber-900 mb-2">Скоро появится</h3>
        <ul className="text-sm text-amber-800 space-y-1 list-disc list-inside">
          <li>Среднее время в каждой стадии</li>
          <li>Аналитика по менеджерам</li>
          <li>Записи и транскрибация звонков</li>
          <li>История переписки с клиентом</li>
        </ul>
      </div>
    </div>
  );
}
