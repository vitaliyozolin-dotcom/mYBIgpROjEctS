import React from "react";
import { useNavigate } from "react-router-dom";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

const SOURCE_LABELS = {
  manual: "Вручную",
  website: "Сайт",
  avito: "Авито",
  telegram: "Telegram",
  vk: "ВКонтакте",
  whatsapp: "WhatsApp",
  instagram: "Instagram",
};

const SOURCE_COLORS = {
  avito: "bg-green-100 text-green-800",
  website: "bg-blue-100 text-blue-800",
  telegram: "bg-sky-100 text-sky-800",
  vk: "bg-indigo-100 text-indigo-800",
  whatsapp: "bg-emerald-100 text-emerald-800",
  instagram: "bg-pink-100 text-pink-800",
  manual: "bg-gray-100 text-gray-600",
};

export default function LeadCard({ lead }) {
  const navigate = useNavigate();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: lead.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => navigate(`/leads/${lead.id}`)}
      className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 cursor-pointer hover:shadow-md hover:border-blue-200 transition select-none"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="font-semibold text-gray-900 text-sm leading-snug">{lead.name}</p>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${SOURCE_COLORS[lead.source] || SOURCE_COLORS.manual}`}>
          {SOURCE_LABELS[lead.source] || lead.source}
        </span>
      </div>

      {lead.phone && (
        <p className="text-xs text-gray-500 mb-1">📞 {lead.phone}</p>
      )}

      {lead.budget && (
        <p className="text-xs text-blue-700 font-medium">
          {lead.budget.toLocaleString("ru-RU")} ₽
        </p>
      )}

      {lead.assigned_to && (
        <p className="text-xs text-gray-400 mt-2">👤 {lead.assigned_to.name}</p>
      )}
    </div>
  );
}
