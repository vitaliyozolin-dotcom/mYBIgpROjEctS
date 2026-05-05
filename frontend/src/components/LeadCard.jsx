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

function ScoreBadge({ score }) {
  const color = score >= 80
    ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
    : score >= 50
    ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-400"
    : "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400";

  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${color}`}>
      {score}
    </span>
  );
}

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
      className="bg-white dark:bg-slate-800 rounded-xl p-3.5 shadow-sm border border-slate-100 dark:border-slate-700 cursor-pointer hover:shadow-md hover:border-indigo-200 dark:hover:border-indigo-600 transition-all select-none"
    >
      <div className="flex items-start gap-2.5 mb-2">
        <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 font-bold text-xs flex items-center justify-center shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <p className="font-semibold text-slate-900 dark:text-slate-100 text-sm truncate leading-snug">{lead.name}</p>
            {lead.score != null && <ScoreBadge score={lead.score} />}
          </div>
          {lead.phone && <p className="text-xs text-slate-400 dark:text-slate-500">{lead.phone}</p>}
        </div>
        <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${SOURCE_COLORS[lead.source] || SOURCE_COLORS.manual}`}
          title={SOURCE_LABELS[lead.source]} />
      </div>

      {lead.tags && lead.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {lead.tags.slice(0, 3).map((tag) => (
            <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 font-medium">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center justify-between">
        {lead.budget ? (
          <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
            {lead.budget >= 1000000
              ? (lead.budget / 1000000).toFixed(1) + "M ₽"
              : lead.budget.toLocaleString("ru-RU") + " ₽"}
          </span>
        ) : (
          <span className="text-xs text-slate-300 dark:text-slate-600">Бюджет не указан</span>
        )}
        <span className="text-xs text-slate-300 dark:text-slate-600">
          {formatDistanceToNow(new Date(lead.created_at), { locale: ru })}
        </span>
      </div>

      {lead.next_action && (
        <div className="mt-2 pt-2 border-t border-slate-50 dark:border-slate-700 flex items-center gap-1.5">
          <span className="text-xs">⏰</span>
          <span className="text-xs text-slate-400 dark:text-slate-500 truncate">{lead.next_action}</span>
        </div>
      )}

      {lead.assigned_to && (
        <div className="mt-1.5 flex items-center gap-1.5">
          <div className="w-4 h-4 rounded-full bg-slate-200 dark:bg-slate-600 text-slate-600 dark:text-slate-300 text-[9px] font-bold flex items-center justify-center">
            {lead.assigned_to.name[0]}
          </div>
          <span className="text-xs text-slate-400 dark:text-slate-500">{lead.assigned_to.name}</span>
        </div>
      )}
    </div>
  );
}
