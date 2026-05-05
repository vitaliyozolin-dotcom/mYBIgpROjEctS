import React, { useEffect, useState, useCallback } from "react";
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
  { id: "new", label: "Новые", dot: "bg-slate-400", color: "text-slate-600" },
  { id: "contacted", label: "Связались", dot: "bg-blue-400", color: "text-blue-700" },
  { id: "qualified", label: "Квалифицированы", dot: "bg-yellow-400", color: "text-yellow-700" },
  { id: "proposal", label: "Предложение", dot: "bg-orange-400", color: "text-orange-700" },
  { id: "negotiation", label: "Переговоры", dot: "bg-purple-400", color: "text-purple-700" },
  { id: "won", label: "Сделка ✓", dot: "bg-emerald-500", color: "text-emerald-700" },
  { id: "lost", label: "Отказ", dot: "bg-red-400", color: "text-red-600" },
];

const SOURCE_LABELS = {
  manual: "Вручную", website: "Сайт", avito: "Авито",
  telegram: "TG", vk: "ВК", whatsapp: "WA", instagram: "IG",
};

// ─── Desktop kanban column ───────────────────────────────────────────────────

function Column({ stage, leads }) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.id });
  const total = leads.reduce((s, l) => s + (l.budget || 0), 0);

  return (
    <div className="flex flex-col w-52 shrink-0">
      <div className="flex items-center gap-1.5 mb-1.5 px-0.5">
        <span className={`w-2 h-2 rounded-full shrink-0 ${stage.dot}`} />
        <span className="font-semibold text-slate-700 text-xs flex-1 truncate">{stage.label}</span>
        <span className="text-xs text-slate-400 bg-white rounded-full px-1.5 border border-slate-200">{leads.length}</span>
      </div>
      {total > 0 && <p className="text-[10px] text-slate-400 px-0.5 mb-1.5">{total.toLocaleString("ru-RU")} ₽</p>}
      <div
        ref={setNodeRef}
        className={`flex flex-col gap-2 flex-1 rounded-xl p-2 min-h-[120px] transition-colors ${
          isOver ? "bg-indigo-50 border-2 border-indigo-300 border-dashed" : "bg-slate-100/70"
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
      className="w-full flex items-center gap-3 py-3 px-1 text-left border-b border-slate-50 last:border-0 active:bg-slate-50 rounded-lg transition-colors"
    >
      <div className="w-9 h-9 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center shrink-0">
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-slate-900 text-sm truncate">{lead.name}</p>
        <p className="text-xs text-slate-400 mt-0.5">
          {lead.phone || lead.email || SOURCE_LABELS[lead.source] || "—"}
        </p>
      </div>
      <div className="text-right shrink-0">
        {lead.budget ? (
          <p className="text-sm font-bold text-emerald-600">{(lead.budget / 1000000).toFixed(1)}M ₽</p>
        ) : (
          <p className="text-xs text-slate-300">—</p>
        )}
        <p className="text-[10px] text-slate-300 mt-0.5">
          {formatDistanceToNow(new Date(lead.created_at), { locale: ru })}
        </p>
      </div>
      <span className="text-slate-300 text-sm shrink-0">›</span>
    </button>
  );
}

// ─── Mobile stage section ─────────────────────────────────────────────────────

function MobileStageSection({ stage, leads }) {
  const [open, setOpen] = useState(leads.length > 0);

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3.5"
      >
        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${stage.dot}`} />
        <span className="font-semibold text-slate-800 text-sm flex-1 text-left">{stage.label}</span>
        <span className={`text-xs font-semibold rounded-full px-2 py-0.5 ${leads.length > 0 ? "bg-slate-100 text-slate-600" : "text-slate-300"}`}>
          {leads.length}
        </span>
        <span className="text-slate-300 text-xs ml-1">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className={`${leads.length > 0 ? "px-4 pb-2 border-t border-slate-50" : ""}`}>
          {leads.length === 0 ? null : leads.map((lead) => (
            <MobileLeadRow key={lead.id} lead={lead} />
          ))}
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

  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 5 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 200, tolerance: 8 } })
  );

  const fetchLeads = useCallback(() => {
    api.get("/leads").then((r) => setLeads(r.data)).catch(() => toast.error("Не удалось загрузить"));
  }, []);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

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
    } catch {
      toast.error("Ошибка");
      fetchLeads();
    }
  }

  const activeLead = activeId ? findLeadById(activeId) : null;
  const totalActive = leads.filter((l) => l.stage !== "won" && l.stage !== "lost").length;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-white sticky top-0 z-10">
        <div>
          <h1 className="text-base font-bold text-slate-900">Воронка продаж</h1>
          <p className="text-xs text-slate-400">{totalActive} активных · {leads.length} всего</p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-xl transition"
        >
          + Лид
        </button>
      </div>

      {/* Mobile view: vertical accordion by stage */}
      <div className="md:hidden flex-1 overflow-auto p-3 space-y-2">
        {STAGES.map((stage) => (
          <MobileStageSection
            key={stage.id}
            stage={stage}
            leads={leads.filter((l) => l.stage === stage.id)}
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
              <Column key={stage.id} stage={stage} leads={leads.filter((l) => l.stage === stage.id)} />
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
