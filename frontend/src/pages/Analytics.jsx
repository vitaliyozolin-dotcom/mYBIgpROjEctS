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
  useEffect(() => { api.get("/leads").then((r) => setLeads(r.data)).catch(() => {}); }, []);

  const total = leads.length;
  const won = leads.filter((l) => l.stage === "won").length;
  const conversion = total > 0 ? ((won / total) * 100).toFixed(1) : 0;
  const wonValue = leads.filter((l) => l.stage === "won" && l.budget).reduce((s, l) => s + l.budget, 0);
  const avgDeal = won > 0 ? Math.round(wonValue / won) : 0;

  const byStage = STAGES.map((s) => ({
    ...s,
    count: leads.filter((l) => l.stage === s.id).length,
    value: leads.filter((l) => l.stage === s.id && l.budget).reduce((sum, l) => sum + l.budget, 0),
  }));
  const maxCount = Math.max(...byStage.map((s) => s.count), 1);

  const sourceCounts = {};
  leads.forEach((l) => { sourceCounts[l.source] = (sourceCounts[l.source] || 0) + 1; });
  const bySource = Object.entries(sourceCounts).sort((a, b) => b[1] - a[1]);
  const maxSource = Math.max(...bySource.map((s) => s[1]), 1);

  return (
    <div className="p-4 max-w-2xl mx-auto">
      <div className="mb-5 pt-1">
        <h1 className="text-xl font-bold text-slate-900">Аналитика</h1>
        <p className="text-slate-400 text-xs mt-0.5">Конверсия и воронка</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        {[
          { label: "Всего лидов", value: total, color: "text-slate-900" },
          { label: "Конверсия", value: `${conversion}%`, color: "text-indigo-600" },
          { label: "Сделок", value: won, color: "text-emerald-600" },
          { label: "Средний чек", value: avgDeal > 0 ? `${(avgDeal / 1_000_000).toFixed(1)}M ₽` : "—", color: "text-emerald-600" },
        ].map((k) => (
          <div key={k.label} className="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm">
            <p className="text-slate-400 text-xs mb-1">{k.label}</p>
            <p className={`text-2xl font-bold ${k.color}`}>{k.value}</p>
          </div>
        ))}
      </div>

      {/* Funnel */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 mb-4">
        <h2 className="font-semibold text-slate-800 mb-4 text-sm">Воронка по стадиям</h2>
        {total === 0 ? <p className="text-slate-400 text-sm">Нет данных</p> : (
          <div className="space-y-3">
            {byStage.map((stage) => (
              <div key={stage.id}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${stage.color}`} />
                  <span className="text-sm text-slate-700 flex-1">{stage.label}</span>
                  <span className="text-sm font-semibold text-slate-800">{stage.count}</span>
                  <span className="text-xs text-slate-400 w-8 text-right">
                    {total > 0 ? `${Math.round((stage.count / total) * 100)}%` : "0%"}
                  </span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${stage.color}`} style={{ width: `${(stage.count / maxCount) * 100}%` }} />
                </div>
                {stage.value > 0 && (
                  <p className="text-xs text-emerald-600 mt-0.5 ml-4">{stage.value.toLocaleString("ru-RU")} ₽</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* By source */}
      {bySource.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 mb-4">
          <h2 className="font-semibold text-slate-800 mb-4 text-sm">Источники лидов</h2>
          <div className="space-y-3">
            {bySource.map(([source, count]) => (
              <div key={source}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-slate-700">{SOURCE_LABELS[source] || source}</span>
                  <span className="text-sm font-semibold text-slate-800">{count}</span>
                </div>
                <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full rounded-full bg-indigo-400" style={{ width: `${(count / maxSource) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Coming soon */}
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4">
        <p className="font-semibold text-amber-900 text-sm mb-2">Скоро появится</p>
        <ul className="text-xs text-amber-800 space-y-1 list-disc list-inside">
          <li>Время в каждой стадии</li>
          <li>Аналитика по менеджерам</li>
          <li>Записи и транскрибация звонков</li>
        </ul>
      </div>
    </div>
  );
}
