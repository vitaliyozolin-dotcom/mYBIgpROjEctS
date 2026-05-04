import React, { useEffect, useState, useCallback } from "react";
import {
  DndContext, closestCenter, DragOverlay,
  useSensor, useSensors, MouseSensor, TouchSensor,
} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useDroppable } from "@dnd-kit/core";
import LeadCard from "../components/LeadCard.jsx";
import NewLeadModal from "../components/NewLeadModal.jsx";
import api from "../api/client.js";
import toast from "react-hot-toast";

const STAGES = [
  { id: "new", label: "Новые", dot: "bg-slate-400" },
  { id: "contacted", label: "Связались", dot: "bg-blue-400" },
  { id: "qualified", label: "Квалифицированы", dot: "bg-yellow-400" },
  { id: "proposal", label: "Предложение", dot: "bg-orange-400" },
  { id: "negotiation", label: "Переговоры", dot: "bg-purple-400" },
  { id: "won", label: "Сделка ✓", dot: "bg-emerald-500" },
  { id: "lost", label: "Отказ", dot: "bg-red-400" },
];

function Column({ stage, leads }) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.id });
  const total = leads.reduce((s, l) => s + (l.budget || 0), 0);

  return (
    <div className="flex flex-col w-[180px] sm:w-52 shrink-0">
      <div className="flex items-center gap-1.5 mb-1.5 px-0.5">
        <span className={`w-2 h-2 rounded-full shrink-0 ${stage.dot}`} />
        <span className="font-semibold text-slate-700 text-xs flex-1 truncate">{stage.label}</span>
        <span className="text-xs text-slate-400 bg-white rounded-full px-1.5 border border-slate-200">{leads.length}</span>
      </div>
      {total > 0 && <p className="text-[10px] text-slate-400 px-0.5 mb-1.5">{total.toLocaleString("ru-RU")} ₽</p>}
      <div
        ref={setNodeRef}
        className={`flex flex-col gap-2 flex-1 rounded-xl p-2 min-h-[100px] transition-colors ${
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

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-white">
        <div>
          <h1 className="text-base font-bold text-slate-900">Воронка продаж</h1>
          <p className="text-xs text-slate-400">{leads.length} лидов</p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-3 py-2 rounded-xl transition"
        >
          + Лид
        </button>
      </div>

      {/* Hint for mobile */}
      <div className="md:hidden px-4 py-2 bg-indigo-50 border-b border-indigo-100">
        <p className="text-xs text-indigo-600">Удерживайте карточку 0.2 сек для перетаскивания</p>
      </div>

      {/* Board - horizontal scroll */}
      <div className="flex-1 overflow-x-auto overflow-y-auto p-3">
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
