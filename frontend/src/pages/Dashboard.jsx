import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { ru } from "date-fns/locale";
import api from "../api/client.js";
import { askAI } from "../api/ai.js";

const STAGE_LABELS = {
  new: "Новая заявка",
  no_answer: "Не дозвонились",
  contacted: "Первичный контакт",
  qualified: "Квалификация",
  selection: "Подбор объекта",
  showing_scheduled: "Показ назначен",
  showing_done: "Показ проведён",
  booking: "Бронь / Аванс",
  documents: "Документы / Ипотека",
  won: "Сделка",
  lost: "Отказ / Архив",
  proposal: "Подбор объекта",
  negotiation: "Показ назначен",
};

const STAGE_COLORS = {
  new: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
  no_answer: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
  contacted: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300",
  qualified: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300",
  selection: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300",
  showing_scheduled: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
  showing_done: "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300",
  booking: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  documents: "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300",
  won: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  lost: "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300",
  proposal: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300",
  negotiation: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300",
};

function ScoreDot({ score }) {
  const c = score >= 80 ? "bg-emerald-500" : score >= 50 ? "bg-amber-400" : "bg-red-400";
  return <span className={`w-2 h-2 rounded-full shrink-0 ${c}`} title={`Score: ${score}`} />;
}

function StatCard({ label, value, sub, accent }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-100 dark:border-slate-700 shadow-sm">
      <p className="text-xs text-slate-400 dark:text-slate-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${accent || "text-slate-900 dark:text-slate-100"}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [leads, setLeads] = useState([]);
  const [me, setMe] = useState(null);
  const [aiInsights, setAiInsights] = useState([]);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiReady, setAiReady] = useState(false);

  useEffect(() => {
    Promise.all([api.get("/leads"), api.get("/auth/me")]).then(([l, m]) => {
      setLeads(l.data);
      setMe(m.data);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (leads.length === 0 || aiReady) return;
    generateInsights();
  }, [leads]);

  async function generateInsights() {
    setAiLoading(true);
    try {
      const summary = leads.slice(0, 8).map((l) =>
        `${l.name} (${STAGE_LABELS[l.stage] || l.stage}, score:${l.score ?? 50})`
      ).join("; ");
      const text = await askAI(
        [{
          role: "user",
          content: `Дай ровно 3 краткие подсказки менеджеру на сегодня по лидам недвижимости: ${summary}. Каждая подсказка — одна строка, начинается с эмодзи. Фокус: кому звонить, кого вести на показ, кто в риске.`,
        }]
      );
      const lines = text.split("\n").map((l) => l.trim()).filter((l) => l.length > 5).slice(0, 3);
      setAiInsights(lines);
      setAiReady(true);
    } catch {
      setAiInsights([]);
    } finally {
      setAiLoading(false);
    }
  }

  const active = leads.filter((l) => l.stage !== "won" && l.stage !== "lost");
  const won = leads.filter((l) => l.stage === "won");
  const conversion = leads.length ? Math.round((won.length / leads.length) * 100) : 0;
  const pipeline = active.reduce((s, l) => s + (l.budget || 0), 0);
  const revenue = won.reduce((s, l) => s + (l.budget || 0), 0);

  const fmt = (n) =>
    n >= 1e6 ? (n / 1e6).toFixed(1) + "M ₽" : n >= 1000 ? Math.round(n / 1000) + "K ₽" : n + " ₽";

  const hotLeads = leads
    .filter((l) => l.stage !== "won" && l.stage !== "lost")
    .sort((a, b) => (b.score ?? 50) - (a.score ?? 50))
    .slice(0, 5);

  return (
    <div className="h-full overflow-auto bg-slate-50 dark:bg-slate-950">
      <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-5 py-4">
        <h1 className="font-bold text-slate-900 dark:text-slate-100 text-xl">
          {me ? `Привет, ${me.name.split(" ")[0]} 👋` : "Главная"}
        </h1>
        <p className="text-sm text-slate-400 dark:text-slate-500 mt-0.5">
          {new Date().toLocaleDateString("ru-RU", { weekday: "long", day: "numeric", month: "long" })}
        </p>
      </div>

      <div className="p-4 space-y-4 max-w-2xl mx-auto">
        <div className="grid grid-cols-2 gap-3">
          <StatCard label="Всего лидов" value={leads.length} sub={`${active.length} активных`} />
          <StatCard label="В воронке" value={pipeline ? fmt(pipeline) : "—"}
            sub="потенциал" accent="text-blue-600 dark:text-blue-400" />
          <StatCard label="Конверсия" value={conversion + "%"} sub={`${won.length} сделок`}
            accent={conversion >= 20 ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"} />
          <StatCard label="Выручка" value={revenue ? fmt(revenue) : "—"}
            sub="закрытые сделки" accent="text-emerald-600 dark:text-emerald-400" />
        </div>

        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-950/60 dark:to-purple-950/60 border border-indigo-100 dark:border-indigo-800/40 rounded-2xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <span>✨</span>
            <p className="font-semibold text-indigo-700 dark:text-indigo-300 text-sm">AI-план продаж на сегодня</p>
            {aiLoading && (
              <div className="ml-auto flex gap-1">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </div>
            )}
          </div>
          {aiInsights.length > 0 ? (
            <div className="space-y-2">
              {aiInsights.map((hint, i) => (
                <p key={i} className="text-sm text-indigo-800 dark:text-indigo-200 leading-relaxed">{hint}</p>
              ))}
            </div>
          ) : !aiLoading && (
            <p className="text-sm text-indigo-400 dark:text-indigo-600">
              {leads.length === 0
                ? "Добавьте первый лид — AI начнёт давать советы"
                : "Укажите ANTHROPIC_API_KEY чтобы включить AI-подсказки"}
            </p>
          )}
        </div>

        {hotLeads.length > 0 && (
          <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-700">
              <p className="font-semibold text-slate-800 dark:text-slate-200 text-sm">🔥 Приоритетные лиды</p>
              <button onClick={() => navigate("/board")}
                className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
                Все →
              </button>
            </div>
            <div className="divide-y divide-slate-50 dark:divide-slate-700/50">
              {hotLeads.map((lead) => (
                <button key={lead.id} onClick={() => navigate(`/leads/${lead.id}`)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                  <ScoreDot score={lead.score ?? 50} />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900 dark:text-slate-100 text-sm truncate">{lead.name}</p>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${STAGE_COLORS[lead.stage] || STAGE_COLORS.new}`}>
                        {STAGE_LABELS[lead.stage] || lead.stage}
                      </span>
                      {lead.next_action && (
                        <span className="text-xs text-slate-400 dark:text-slate-500 truncate">⏰ {lead.next_action}</span>
                      )}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    {lead.budget && (
                      <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
                        {lead.budget >= 1e6 ? (lead.budget / 1e6).toFixed(1) + "M" : Math.round(lead.budget / 1000) + "K"}
                      </p>
                    )}
                    <p className="text-[10px] text-slate-300 dark:text-slate-600 mt-0.5">
                      {formatDistanceToNow(new Date(lead.created_at), { locale: ru })}
                    </p>
                  </div>
                  <span className="text-slate-300 dark:text-slate-600 text-sm">›</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {leads.length === 0 && (
          <div className="text-center py-12">
            <p className="text-4xl mb-3">📋</p>
            <p className="font-semibold text-slate-700 dark:text-slate-300">Лидов пока нет</p>
            <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">
              Добавьте первый лид через воронку или настройте интеграцию с сайтом
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
