import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { format, formatDistanceToNow } from "date-fns";
import { ru } from "date-fns/locale";
import api from "../api/client.js";
import toast from "react-hot-toast";

const STAGES = [
  { id: "new", label: "Новый", color: "bg-slate-100 text-slate-600" },
  { id: "contacted", label: "Связались", color: "bg-blue-100 text-blue-700" },
  { id: "qualified", label: "Квалифицирован", color: "bg-yellow-100 text-yellow-700" },
  { id: "proposal", label: "Предложение", color: "bg-orange-100 text-orange-700" },
  { id: "negotiation", label: "Переговоры", color: "bg-purple-100 text-purple-700" },
  { id: "won", label: "Сделка", color: "bg-emerald-100 text-emerald-700" },
  { id: "lost", label: "Отказ", color: "bg-red-100 text-red-600" },
];

const SOURCE_LABELS = {
  manual: "Вручную", website: "Сайт", avito: "Авито",
  telegram: "Telegram", vk: "ВКонтакте", whatsapp: "WhatsApp", instagram: "Instagram",
};

export default function LeadDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [lead, setLead] = useState(null);
  const [comments, setComments] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [newComment, setNewComment] = useState("");
  const [newTask, setNewTask] = useState({ title: "", due_at: "" });
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({});

  const [stageHistory, setStageHistory] = useState([]);

  const fetchAll = useCallback(async () => {
    const [l, c, t, h] = await Promise.all([
      api.get(`/leads/${id}`),
      api.get(`/comments/lead/${id}`),
      api.get(`/tasks/lead/${id}`),
      api.get(`/leads/${id}/stage-history`),
    ]);
    setLead(l.data); setForm(l.data);
    setComments(c.data); setTasks(t.data);
    setStageHistory(h.data);
  }, [id]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  async function saveField(field, value) {
    try {
      const { data } = await api.patch(`/leads/${id}`, { [field]: value });
      setLead(data); setForm(data);
      toast.success("Сохранено");
    } catch { toast.error("Ошибка"); }
  }

  async function addComment(e) {
    e.preventDefault();
    if (!newComment.trim()) return;
    try {
      await api.post("/comments", { text: newComment, lead_id: parseInt(id) });
      setNewComment("");
      const { data } = await api.get(`/comments/lead/${id}`);
      setComments(data);
    } catch {
      toast.error("Не удалось добавить комментарий");
    }
  }

  async function addTask(e) {
    e.preventDefault();
    if (!newTask.title.trim()) return;
    try {
      await api.post("/tasks", { title: newTask.title, lead_id: parseInt(id), due_at: newTask.due_at || null });
      setNewTask({ title: "", due_at: "" });
      const { data } = await api.get(`/tasks/lead/${id}`);
      setTasks(data);
      toast.success("Задача добавлена");
    } catch {
      toast.error("Не удалось добавить задачу");
    }
  }

  async function toggleTask(task) {
    await api.patch(`/tasks/${task.id}`, { is_done: !task.is_done });
    api.get(`/tasks/lead/${id}`).then((r) => setTasks(r.data));
  }

  if (!lead) return (
    <div className="flex items-center justify-center h-full">
      <div className="w-8 h-8 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" />
    </div>
  );

  const stageObj = STAGES.find((s) => s.id === lead.stage);
  const initials = lead.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <div className="h-full overflow-auto bg-slate-50">
      {/* Top bar */}
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4 sticky top-0 z-10">
        <button onClick={() => navigate("/board")} className="text-slate-400 hover:text-slate-700 transition text-lg">←</button>
        <div className="flex-1 min-w-0">
          <h1 className="font-bold text-slate-900 text-lg truncate">{lead.name}</h1>
          <p className="text-xs text-slate-400">
            Создан {formatDistanceToNow(new Date(lead.created_at), { locale: ru, addSuffix: true })}
          </p>
        </div>
        <span className={`text-xs font-semibold px-3 py-1.5 rounded-full ${stageObj?.color || ""}`}>
          {stageObj?.label}
        </span>
      </div>

      <div className="max-w-4xl mx-auto p-5 grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Left: lead info */}
        <div className="space-y-4">
          {/* Card */}
          <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 rounded-full bg-indigo-100 text-indigo-700 font-bold text-lg flex items-center justify-center">
                {initials}
              </div>
              <div className="flex-1">
                {editing ? (
                  <input value={form.name || ""} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    onBlur={() => saveField("name", form.name)}
                    className="w-full font-bold text-slate-900 border-b border-indigo-300 outline-none pb-0.5" />
                ) : (
                  <p className="font-bold text-slate-900">{lead.name}</p>
                )}
                <p className="text-xs text-slate-400">{SOURCE_LABELS[lead.source] || lead.source}</p>
              </div>
              <button onClick={() => setEditing(!editing)}
                className="text-xs text-indigo-600 hover:underline">
                {editing ? "Готово" : "Изменить"}
              </button>
            </div>

            <div className="space-y-3">
              <InfoRow label="Телефон" value={form.phone} editing={editing}
                onChange={(v) => setForm((f) => ({ ...f, phone: v }))}
                onBlur={() => saveField("phone", form.phone)}
                href={form.phone ? `tel:${form.phone}` : null} />
              <InfoRow label="Email" value={form.email} editing={editing}
                onChange={(v) => setForm((f) => ({ ...f, email: v }))}
                onBlur={() => saveField("email", form.email)}
                href={form.email ? `mailto:${form.email}` : null} />
              <InfoRow label="Бюджет (₽)" value={form.budget} type="number" editing={editing}
                onChange={(v) => setForm((f) => ({ ...f, budget: v }))}
                onBlur={() => saveField("budget", form.budget ? parseInt(form.budget) : null)} />

              <div>
                <p className="text-xs text-slate-400 mb-1">Стадия</p>
                <select value={form.stage}
                  onChange={(e) => { setForm((f) => ({ ...f, stage: e.target.value })); saveField("stage", e.target.value); }}
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400">
                  {STAGES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
                </select>
              </div>
            </div>

            {editing && (
              <div className="mt-4">
                <p className="text-xs text-slate-400 mb-1">Заметки</p>
                <textarea rows={3} value={form.notes || ""}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  onBlur={() => saveField("notes", form.notes)}
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none" />
              </div>
            )}
            {!editing && lead.notes && (
              <div className="mt-4 p-3 bg-amber-50 rounded-xl border border-amber-100 text-xs text-amber-800">
                {lead.notes}
              </div>
            )}
          </div>

          {/* Quick contact */}
          {(lead.phone || lead.email) && (
            <div className="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Быстрый контакт</p>
              <div className="flex flex-col gap-2">
                {lead.phone && (
                  <a href={`tel:${lead.phone}`} className="flex items-center gap-2 text-sm text-indigo-600 hover:underline">
                    📞 {lead.phone}
                  </a>
                )}
                {lead.email && (
                  <a href={`mailto:${lead.email}`} className="flex items-center gap-2 text-sm text-indigo-600 hover:underline">
                    ✉️ {lead.email}
                  </a>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right: tasks + comments */}
        <div className="md:col-span-2 space-y-5">
          {/* Stage history */}
          {stageHistory.length > 0 && (
            <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
              <h3 className="font-semibold text-slate-800 mb-4 text-sm">⏱ Время в стадиях</h3>
              <div className="space-y-2">
                {stageHistory.map((h, i) => (
                  <div key={i} className={`flex items-center gap-3 p-2.5 rounded-xl ${h.is_current ? "bg-indigo-50 border border-indigo-100" : "bg-slate-50"}`}>
                    <div className={`w-2 h-2 rounded-full shrink-0 ${h.is_current ? "bg-indigo-500" : "bg-slate-300"}`} />
                    <span className="text-sm flex-1 text-slate-700">{h.label}</span>
                    <span className={`text-xs font-medium ${h.is_current ? "text-indigo-600" : "text-slate-400"}`}>
                      {h.days > 0 ? `${h.days}д ` : ""}{h.hours}ч
                      {h.is_current && " (сейчас)"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tasks */}
          <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
            <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
              ✓ Задачи
              <span className="text-xs text-slate-400 font-normal">
                {tasks.filter((t) => !t.is_done).length} активных
              </span>
            </h3>
            <form onSubmit={addTask} className="flex gap-2 mb-4">
              <input placeholder="Новая задача..." value={newTask.title}
                onChange={(e) => setNewTask((t) => ({ ...t, title: e.target.value }))}
                className="flex-1 border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
              <input type="datetime-local" value={newTask.due_at}
                onChange={(e) => setNewTask((t) => ({ ...t, due_at: e.target.value }))}
                className="border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 w-36" />
              <button type="submit" className="bg-indigo-600 text-white px-4 rounded-xl text-sm font-bold hover:bg-indigo-700 transition">
                +
              </button>
            </form>
            <div className="space-y-2">
              {tasks.length === 0 && <p className="text-sm text-slate-400">Задач нет</p>}
              {tasks.map((task) => (
                <div key={task.id} className={`flex items-start gap-3 p-3 rounded-xl border transition ${task.is_done ? "bg-slate-50 border-slate-100 opacity-60" : "bg-white border-slate-200"}`}>
                  <input type="checkbox" checked={task.is_done} onChange={() => toggleTask(task)}
                    className="mt-0.5 w-4 h-4 accent-indigo-600 cursor-pointer" />
                  <div className="flex-1">
                    <p className={`text-sm ${task.is_done ? "line-through text-slate-400" : "text-slate-800"}`}>{task.title}</p>
                    {task.due_at && (
                      <p className={`text-xs mt-0.5 ${new Date(task.due_at) < new Date() && !task.is_done ? "text-red-500" : "text-slate-400"}`}>
                        до {format(new Date(task.due_at), "d MMM, HH:mm", { locale: ru })}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Comments */}
          <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
            <h3 className="font-semibold text-slate-800 mb-4">💬 Комментарии</h3>
            <div className="space-y-4 mb-4 max-h-72 overflow-y-auto">
              {comments.length === 0 && <p className="text-sm text-slate-400">Комментариев нет</p>}
              {comments.map((c) => (
                <div key={c.id} className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center shrink-0">
                    {c.author?.name?.[0] || "?"}
                  </div>
                  <div className="flex-1 bg-slate-50 rounded-xl p-3">
                    <div className="flex items-baseline gap-2 mb-1">
                      <span className="text-xs font-semibold text-slate-700">{c.author?.name || "Система"}</span>
                      <span className="text-xs text-slate-400">{format(new Date(c.created_at), "d MMM, HH:mm", { locale: ru })}</span>
                    </div>
                    <p className="text-sm text-slate-800">{c.text}</p>
                  </div>
                </div>
              ))}
            </div>
            <form onSubmit={addComment} className="flex gap-2">
              <input value={newComment} onChange={(e) => setNewComment(e.target.value)}
                placeholder="Написать комментарий..."
                className="flex-1 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400" />
              <button type="submit" className="bg-indigo-600 text-white px-4 rounded-xl text-sm font-semibold hover:bg-indigo-700 transition">
                Отправить
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value, editing, onChange, onBlur, type = "text", href }) {
  return (
    <div>
      <p className="text-xs text-slate-400 mb-0.5">{label}</p>
      {editing ? (
        <input type={type} value={value || ""} onChange={(e) => onChange(e.target.value)} onBlur={onBlur}
          className="w-full text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400" />
      ) : href ? (
        <a href={href} className="text-sm font-medium text-indigo-600 hover:underline" onClick={(e) => e.stopPropagation()}>
          {value || "—"}
        </a>
      ) : (
        <p className="text-sm font-medium text-slate-800">
          {type === "number" && value ? parseInt(value).toLocaleString("ru-RU") + " ₽" : value || "—"}
        </p>
      )}
    </div>
  );
}
