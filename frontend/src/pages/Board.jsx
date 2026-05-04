import React, { useEffect, useState, useCallback } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  DragOverlay,
} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useDroppable } from "@dnd-kit/core";
import Header from "../components/Header.jsx";
import LeadCard from "../components/LeadCard.jsx";
import NewLeadModal from "../components/NewLeadModal.jsx";
import api from "../api/client.js";
import toast from "react-hot-toast";

const STAGES = [
  { id: "new", label: "Новые", color: "border-gray-300 bg-gray-50" },
  { id: "contacted", label: "Связались", color: "border-blue-300 bg-blue-50" },
  { id: "qualified", label: "Квалифицированы", color: "border-yellow-300 bg-yellow-50" },
  { id: "proposal", label: "Предложение", color: "border-orange-300 bg-orange-50" },
  { id: "negotiation", label: "Переговоры", color: "border-purple-300 bg-purple-50" },
  { id: "won", label: "Сделка закрыта", color: "border-green-400 bg-green-50" },
  { id: "lost", label: "Отказ", color: "border-red-300 bg-red-50" },
];

function Column({ stage, leads, activeId }) {
  const { setNodeRef } = useDroppable({ id: stage.id });

  return (
    <div className={`flex flex-col rounded-xl border-2 ${stage.color} min-w-[220px] w-56 shrink-0`}>
      <div className="px-3 py-2 flex items-center justify-between">
        <span className="font-semibold text-sm text-gray-700">{stage.label}</span>
        <span className="text-xs text-gray-400 bg-white rounded-full px-2 py-0.5 border">
          {leads.length}
        </span>
      </div>
      <div ref={setNodeRef} className="flex flex-col gap-2 p-2 min-h-[100px] flex-1">
        <SortableContext items={leads.map((l) => l.id)} strategy={verticalListSortingStrategy}>
          {leads.map((lead) => (
            <LeadCard key={lead.id} lead={lead} />
          ))}
        </SortableContext>
      </div>
    </div>
  );
}

export default function Board() {
  const [leads, setLeads] = useState([]);
  const [showNewModal, setShowNewModal] = useState(false);
  const [activeId, setActiveId] = useState(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  const fetchLeads = useCallback(async () => {
    try {
      const { data } = await api.get("/leads");
      setLeads(data);
    } catch {
      toast.error("Не удалось загрузить лиды");
    }
  }, []);

  useEffect(() => { fetchLeads(); }, [fetchLeads]);

  function getLeadsForStage(stageId) {
    return leads.filter((l) => l.stage === stageId);
  }

  function findLeadById(id) {
    return leads.find((l) => l.id === id);
  }

  function findStageByLeadId(id) {
    return leads.find((l) => l.id === id)?.stage;
  }

  async function handleDragEnd({ active, over }) {
    setActiveId(null);
    if (!over) return;

    const lead = findLeadById(active.id);
    const newStage = STAGES.find((s) => s.id === over.id)?.id || findStageByLeadId(over.id);

    if (!lead || !newStage || lead.stage === newStage) return;

    setLeads((prev) => prev.map((l) => (l.id === lead.id ? { ...l, stage: newStage } : l)));

    try {
      await api.patch(`/leads/${lead.id}`, { stage: newStage });
    } catch {
      toast.error("Ошибка при перемещении");
      fetchLeads();
    }
  }

  const activeLead = activeId ? findLeadById(activeId) : null;

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <Header />
      <div className="flex items-center justify-between px-6 py-4">
        <h2 className="text-xl font-bold text-gray-800">Воронка продаж</h2>
        <button
          onClick={() => setShowNewModal(true)}
          className="bg-blue-800 hover:bg-blue-900 text-white text-sm font-semibold px-4 py-2 rounded-lg transition"
        >
          + Новый лид
        </button>
      </div>

      <div className="flex-1 overflow-x-auto px-6 pb-6">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={({ active }) => setActiveId(active.id)}
          onDragEnd={handleDragEnd}
        >
          <div className="flex gap-4 h-full">
            {STAGES.map((stage) => (
              <Column
                key={stage.id}
                stage={stage}
                leads={getLeadsForStage(stage.id)}
                activeId={activeId}
              />
            ))}
          </div>
          <DragOverlay>
            {activeLead && <LeadCard lead={activeLead} />}
          </DragOverlay>
        </DndContext>
      </div>

      {showNewModal && (
        <NewLeadModal
          onClose={() => setShowNewModal(false)}
          onCreated={() => { setShowNewModal(false); fetchLeads(); }}
        />
      )}
    </div>
  );
}
