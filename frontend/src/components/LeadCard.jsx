import React from "react";
import { useNavigate } from "react-router-dom";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { formatDistanceToNow } from "date-fns";
import { ru } from "date-fns/locale";

const SOURCE_COLORS = {
  avito: "bg-emerald-500",
  website: "bg-blue-500",
  telegram: "bg-sky-500",
  vk: "bg-indigo-500",
  whatsapp: "bg-green-500",
  instagram: "bg-pink-500",
  manual: "bg-slate-400",
};

const SOURCE_LABELS = {
  manual: "Вручную", website: "Сайт", avito: "Авито",
  telegram: "TG", vk: "ВК", whatsapp: "WA", instagram: "IG",
};

export default function LeadCard({ lead }) {
  const navigate = useNavigate();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: lead.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  };

  const initials = lead.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => navigate(`/leads/${lead.id}`)}
      className="bg-white rounded-xl p-3.5 shadow-sm border border-slate-100 cursor-pointer hover:shadow-md hover:border-indigo-200 transition-all select-none group"
    >
      <div className="flex items-start gap-2.5 mb-2">
        <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-900 text-sm truncate leading-snug">{lead.name}</p>
          {lead.phone && <p className="text-xs text-slate-400 mt-0.5">{lead.phone}</p>}
        </div>
        <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${SOURCE_COLORS[lead.source] || SOURCE_COLORS.manual}`} title={SOURCE_LABELS[lead.source]} />
      </div>

      <div className="flex items-center justify-between">
        {lead.budget ? (
          <span className="text-sm font-bold text-emerald-600">
            {lead.budget.toLocaleString("ru-RU")} ₽
          </span>
        ) : (
          <span className="text-xs text-slate-300">Бюджет не указан</span>
        )}
        <span className="text-xs text-slate-300">
          {formatDistanceToNow(new Date(lead.created_at), { locale: ru, addSuffix: false })}
        </span>
      </div>

      {lead.assigned_to && (
        <div className="mt-2 pt-2 border-t border-slate-50 flex items-center gap-1.5">
          <div className="w-4 h-4 rounded-full bg-slate-200 text-slate-600 text-[9px] font-bold flex items-center justify-center">
            {lead.assigned_to.name[0]}
          </div>
          <span className="text-xs text-slate-400">{lead.assigned_to.name}</span>
        </div>
      )}
    </div>
  );
}
