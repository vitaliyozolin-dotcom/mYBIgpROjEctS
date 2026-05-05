import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import {
  DndContext, closestCenter, DragOverlay,
  useSensor, useSensors, MouseSensor, TouchSensor,
} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useDroppable } from "@dnd-kit/core";
import { formatDistanceToNow } from "date-fns";
import { ru } from "date-fns/locale";
import LeadCard from "../components/LeadCard.jsx";
import NewLeadModal from "../components/NewLeadModal.jsx";
import api from "../api/client.js";
import toast from "react-hot-toast";

const STAGES = [
  { id: "new", label: "Новая заявка", dot: "bg-slate-400", color: "text-slate-600 dark:text-slate-300" },
  { id: "no_answer", label: "Не дозвонились", dot: "bg-slate-500", color: "text-slate-600 dark:text-slate-300" },
  { id: "contacted", label: "Первичный контакт", dot: "bg-blue-400", color: "text-blue-700 dark:text-blue-300" },
  { id: "qualified", label: "Квалификация", dot: "bg-yellow-400", color: "text-yellow-700 dark:text-yellow-300" },
  { id: "selection", label: "Подбор объекта", dot: "bg-cyan-400", color: "text-cyan-700 dark:text-cyan-300" },
  { id: "showing_scheduled", label: "Показ назначен", dot: "bg-orange-400", color: "text-orange-700 dark:text-orange-300" },
  { id: "showing_done", label: "Показ проведён", dot: "bg-purple-400", color: "text-purple-700 dark:text-purple-300" },
  { id: "booking", label: "Бронь / Аванс", dot: "bg-emerald-500", color: "text-emerald-700 dark:text-emerald-300" },
  { id: "documents", label: "Документы / Ипотека", dot: "bg-teal-500", color: "text-teal-700 dark:text-teal-300" },
  { id: "won", label: "Сделка ✓", dot: "bg-emerald-600", color: "text-emerald-700 dark:text-emerald-300" },
  { id: "lost", label: "Отказ / Архив", dot: "bg-red-400", color: "text-red-600 dark:text-red-300" },
];

const SOURCE_LABELS = {
  manual: "Вручную", website: "Сайт", avito: "Авито",
  telegram: "TG", vk: "ВК", whatsapp: "WA", instagram: "IG",
  partners: "Партнёры", referral: "Рекомендация",
};

const SOURCE_OPTIONS = [
  { value: "all", label: "Все источники" },
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

function formatMoney(value) {
  if (!value) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M ₽`;
  return `${Math.round(value / 1000)}K ₽`;
}

function scoreClass(score = 0) {
  if (score >= 80) return "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300";
  if (score >= 50) return "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300";
  return "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300";
}

// ─── Desktop kanban column ───────────────────────────────────────────────────

function Column({ stage, leads }) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.id });
  const total = leads.reduce((s, l) => s + (l.budget || 0), 0);

  return (
    <div className="flex flex-col w-56 shrink-0">
      <div className="flex items-center gap-1.5 mb-1.5 px-0.5">
        <span className={`w-2 h-2 rounded-full shrink-0 ${stage.dot}`} />
        <span className={`font-semibold text-xs flex-1 truncate ${stage.color}`}>{stage.label}</span>
        <span className="text-xs text-slate-400 dark:text-slate-500 bg-white dark:bg-slate-800 rounded-full px-1.5 border border-slate-200 dark:border-slate-700">{leads.length}</span>
      </div>
      {total > 0 && <p className="text-[10px] text-slate-400 dark:text-slate-500 px-0.5 mb-1.5">{total.toLocaleString("ru-RU")} ₽</p>}
      <div
        ref={setNodeRef}
        className={`flex flex-col gap-2 flex-1 rounded-xl p-2 min-h-[120px] transition-colors ${
          isOver ? "bg-indigo-50 dark:bg-indigo-950/40 border-2 border-indigo-300 dark:border-indigo-600 border-dashed" : "bg-slate-100/70 dark:bg-slate-900/70"
        }`}
      >
        <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
          {leads.map((lead) => <LeadCard key={lead.id} lead={lead} />)}
        </SortableContext>
      </div>
    </div>
  );
}

// ─── Mobile lead row ─────────────────────────────────────────────────────────

function MobileLeadRow({ lead }) {
  const navigate = useNavigate();
  const initials = lead.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <button
      onClick={() => navigate(`/leads/${lead.id}`)}
      className="w-full flex items-start gap-3 py-3 px-1 text-left border-b border-slate-50 dark:border-slate-800 last:border-0 active:bg-slate-50 dark:active:bg-slate-800 rounded-lg transition-colors"
    >
      <div className="w-9 h-9 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 font-bold text-xs flex items-center justify-center shrink-0">
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm truncate">{lead.name}</p>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${scoreClass(lead.score ?? 0)}`}>
            {lead.score ?? 0}
          </span>
        </div>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
          {lead.phone || lead.email || SOURCE_LABELS[lead.source] || "—"}
        </p>
        {lead.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {lead.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
                {tag}
              </span>
            ))}
          </div>
        )}
        {lead.next_action && (
          <p className="text-xs text-indigo-500 dark:text-indigo-400 mt-1.5 truncate">⏰ {lead.next_action}</p>
        )}
      </div>
      <div className="text-right shrink-0">
        <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400">{formatMoney(lead.budget)}</p>
        <p className="text-[10px] text-slate-300 dark:text-slate-600 mt-0.5">
          {formatDistanceToNow(new Date(lead.created_at), { locale: ru })}
        </p>
      </div>
      <span className="text-slate-300 dark:text-slate-600 text-sm shrink-0 mt-1">›</span>
    </button>
  );
}

// ─── Mobile stage section ─────────────────────────────────────────────────────

function MobileStageSection({ stage, leads }) {
  const [open, setOpen] = useState(leads.length > 0);
  const total = leads.reduce((s, l) => s + (l.budget || 0), 0);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3.5"
      >
        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${stage.dot}`} />
        <span className="font-semibold text-slate-800 dark:text-slate-200 text-sm flex-1 text-left">{stage.label}</span>
        {total > 0 && <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-bold">{formatMoney(total)}</span>}
        <span className={`text-xs font-semibold rounded-full px-2 py-0.5 ${leads.length > 0 ? "bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300" : "text-slate-300 dark:text-slate-600"}`}>
          {leads.length}
        </span>
        <span className="text-slate-300 dark:text-slate-600 text-xs ml-1">{open ? "▲" : "▼"}</span>
      </button>
      {open && leads.length > 0 && (
        <div className="px-4 pb-2 border-t border-slate-50 dark:border-slate-800">
          {leads.map((lead) => <MobileLeadRow key={lead.id} lead={lead} />)}
        </div>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function Board() {
  const [leads, setLeads] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [activeId, setActiveId] = useState(null);
  const [search, setSearch] = useState("");
  const [stageFilter, setStageFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [scoreFilter, setScoreFilter] = useState("all");

  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 8 } })
  );

  const fetchLeads = useCallback(() => {
    api.get("/leads").then((r) => setLeads(r.data)).catch(() => toast.error("Не удалось загрузить"));
  }, []);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  const filteredLeads = useMemo(() => {
    const q = search.trim().toLowerCase();
    return leads.filter((lead) => {
      const matchesSearch = !q || [lead.name, lead.phone, lead.email]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(q));
      const matchesStage = stageFilter === "all" || lead.stage === stageFilter;
      const matchesSource = sourceFilter === "all" || lead.source === sourceFilter;
      const score = lead.score ?? 0;
      const matchesScore = scoreFilter === "all"
        || (scoreFilter === "hot" && score >= 80)
        || (scoreFilter === "warm" && score >= 50 && score < 80)
        || (scoreFilter === "cold" && score < 50);
      return matchesSearch && matchesStage && matchesSource && matchesScore;
    });
  }, [leads, search, stageFilter, sourceFilter, scoreFilter]);

  function findLeadById(id) { return leads.find((l) => l.id === id); }
  function findStageByLeadId(id) { return leads.find((l) => l.id === id)?.stage; }

  async function handleDragEnd({ active, over }) {
    setActiveId(null);
    if (!over) return;
    const lead = findLeadById(active.id);
    const newStage = STAGES.find((s) => s.id === over.id)?.id || findStageByLeadId(over.id);
    if (!lead || !newStage || lead.stage === newStage) return;
    setLeads((prev) => prev.map((l) => l.id === lead.id ? { ...l, stage: newStage } : l));
    try {
      await api.patch(`/leads/${lead.id}`, { stage: newStage });
      fetchLeads();
    } catch {
      toast.error("Ошибка");
      fetchLeads();
    }
  }

  const activeLead = activeId ? findLeadById(activeId) : null;
  const totalActive = filteredLeads.filter((l) => l.stage !== "won" && l.stage !== "lost").length;
  const hasFilters = search || stageFilter !== "all" || sourceFilter !== "all" || scoreFilter !== "all";

  return (
    <div className="flex flex-col h-full bg-slate-50 dark:bg-slate-950">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 sticky top-0 z-10">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div>
            <h1 className="text-base font-bold text-slate-900 dark:text-slate-100">Воронка продаж</h1>
            <p className="text-xs text-slate-400 dark:text-slate-500">{totalActive} активных · {filteredLeads.length} показано · {leads.length} всего</p>
          </div>
          <button
            onClick={() => setShowNew(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-xl transition shrink-0"
          >
            + Лид
          </button>
        </div>

        <div className="space-y-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск: имя, телефон, email..."
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <div className="grid grid-cols-3 gap-2">
            <select value={stageFilter} onChange={(e) => setStageFilter(e.target.value)}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-2 py-2 text-xs text-slate-700 dark:text-slate-200 focus:outline-none">
              <option value="all">Все стадии</option>
              {STAGES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
            </select>
            <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-2 py-2 text-xs text-slate-700 dark:text-slate-200 focus:outline-none">
              {SOURCE_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <select value={scoreFilter} onChange={(e) => setScoreFilter(e.target.value)}
              className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-2 py-2 text-xs text-slate-700 dark:text-slate-200 focus:outline-none">
              <option value="all">Любой score</option>
              <option value="hot">Горячие 80+</option>
              <option value="warm">Тёплые 50–79</option>
              <option value="cold">Холодные &lt;50</option>
            </select>
          </div>
          {hasFilters && (
            <button onClick={() => { setSearch(""); setStageFilter("all"); setSourceFilter("all"); setScoreFilter("all"); }}
              className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline">
              Сбросить фильтры
            </button>
          )}
        </div>
      </div>

      {/* Mobile view: vertical accordion by stage */}
      <div className="md:hidden flex-1 overflow-auto p-3 space-y-2 pb-24">
        {STAGES.map((stage) => (
          <MobileStageSection
            key={stage.id}
            stage={stage}
            leads={filteredLeads.filter((l) => l.stage === stage.id)}
          />
        ))}
      </div>

      {/* Desktop view: horizontal kanban with DnD */}
      <div className="hidden md:flex flex-1 overflow-x-auto overflow-y-auto p-3">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={({ active }) => setActiveId(active.id)}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-3 h-full pb-2 min-w-max">
            {STAGES.map((stage) => (
              <Column key={stage.id} stage={stage} leads={filteredLeads.filter((l) => l.stage === stage.id)} />
            ))}
          </div>
          <DragOverlay>{activeLead && <LeadCard lead={activeLead} />}</DragOverlay>
        </DndContext>
      </div>

      {showNew && (
        <NewLeadModal onClose={() => setShowNew(false)} onCreated={() => { setShowNew(false); fetchLeads(); }} />
      )}
    </div>
  );
}
