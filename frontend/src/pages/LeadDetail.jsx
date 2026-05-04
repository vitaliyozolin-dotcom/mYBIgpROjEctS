import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { format } from "date-fns";
import { ru } from "date-fns/locale";
import Header from "../components/Header.jsx";
import api from "../api/client.js";
import toast from "react-hot-toast";

const STAGES = [
  { id: "new", label: "Новый" },
  { id: "contacted", label: "Связались" },
  { id: "qualified", label: "Квалифицирован" },
  { id: "proposal", label: "Предложение" },
  { id: "negotiation", label: "Переговоры" },
  { id: "won", label: "Сделка" },
  { id: "lost", label: "Отказ" },
];

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

  const fetchAll = useCallback(async () => {
    const [leadRes, commRes, taskRes] = await Promise.all([
      api.get(`/leads/${id}`),
      api.get(`/comments/lead/${id}`),
      api.get(`/tasks/lead/${id}`),
    ]);
    setLead(leadRes.data);
    setForm(leadRes.data);
    setComments(commRes.data);
    setTasks(taskRes.data);
  }, [id]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  async function saveField(field, value) {
    try {
      const { data } = await api.patch(`/leads/${id}`, { [field]: value });
      setLead(data);
      setForm(data);
    } catch {
      toast.error("Ошибка сохранения");
    }
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
      toast.error("Ошибка");
    }
  }

  async function addTask(e) {
    e.preventDefault();
    if (!newTask.title.trim()) return;
    try {
      await api.post("/tasks", { ...newTask, lead_id: parseInt(id), due_at: newTask.due_at || null });
      setNewTask({ title: "", due_at: "" });
      const { data } = await api.get(`/tasks/lead/${id}`);
      setTasks(data);
    } catch {
      toast.error("Ошибка");
    }
  }

  async function toggleTask(task) {
    await api.patch(`/tasks/${task.id}`, { is_done: !task.is_done });
    const { data } = await api.get(`/tasks/lead/${id}`);
    setTasks(data);
  }

  if (!lead) return <div className="flex items-center justify-center h-screen text-gray-400">Загрузка...</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title={lead.name} />
      <div className="max-w-5xl mx-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">

        {/* Левая колонка — инфо о лиде */}
        <div className="md:col-span-1 space-y-4">
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-bold text-lg text-gray-900">{lead.name}</h2>
              <button onClick={() => setEditing(!editing)} className="text-xs text-blue-600 hover:underline">
                {editing ? "Готово" : "Редактировать"}
              </button>
            </div>

            <div className="space-y-3 text-sm">
              <Field label="Телефон" value={form.phone} editing={editing}
                onChange={(v) => setForm((f) => ({ ...f, phone: v }))}
                onBlur={() => saveField("phone", form.phone)} />
              <Field label="Email" value={form.email} editing={editing}
                onChange={(v) => setForm((f) => ({ ...f, email: v }))}
                onBlur={() => saveField("email", form.email)} />
              <Field label="Бюджет (₽)" value={form.budget} editing={editing} type="number"
                onChange={(v) => setForm((f) => ({ ...f, budget: v }))}
                onBlur={() => saveField("budget", form.budget ? parseInt(form.budget) : null)} />

              <div>
                <p className="text-gray-400 text-xs mb-1">Стадия</p>
                {editing ? (
                  <select value={form.stage} onChange={(e) => { setForm((f) => ({ ...f, stage: e.target.value })); saveField("stage", e.target.value); }}
                    className="w-full border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    {STAGES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
                  </select>
                ) : (
                  <p className="font-medium">{STAGES.find((s) => s.id === lead.stage)?.label}</p>
                )}
              </div>

              <div>
                <p className="text-gray-400 text-xs mb-1">Источник</p>
                <p className="font-medium capitalize">{lead.source}</p>
              </div>

              <div>
                <p className="text-gray-400 text-xs mb-1">Создан</p>
                <p className="font-medium">{format(new Date(lead.created_at), "d MMM yyyy, HH:mm", { locale: ru })}</p>
              </div>
            </div>

            {editing && (
              <div className="mt-4">
                <p className="text-gray-400 text-xs mb-1">Заметки</p>
                <textarea rows={4} value={form.notes || ""} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  onBlur={() => saveField("notes", form.notes)}
                  className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
              </div>
            )}

            {!editing && lead.notes && (
              <div className="mt-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                <p className="text-xs text-yellow-700">{lead.notes}</p>
              </div>
            )}
          </div>

          <button onClick={() => navigate("/")} className="text-sm text-gray-400 hover:text-gray-700 transition">
            ← Назад к доске
          </button>
        </div>

        {/* Правая колонка — комментарии и задачи */}
        <div className="md:col-span-2 space-y-6">

          {/* Задачи */}
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <h3 className="font-bold text-gray-800 mb-4">Задачи</h3>
            <form onSubmit={addTask} className="flex gap-2 mb-4">
              <input placeholder="Новая задача..." value={newTask.title}
                onChange={(e) => setNewTask((t) => ({ ...t, title: e.target.value }))}
                className="flex-1 border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <input type="datetime-local" value={newTask.due_at}
                onChange={(e) => setNewTask((t) => ({ ...t, due_at: e.target.value }))}
                className="border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <button type="submit" className="bg-blue-800 text-white px-4 rounded-lg text-sm font-semibold hover:bg-blue-900 transition">
                +
              </button>
            </form>
            <div className="space-y-2">
              {tasks.length === 0 && <p className="text-sm text-gray-400">Задач нет</p>}
              {tasks.map((task) => (
                <div key={task.id} className={`flex items-start gap-3 p-3 rounded-lg border ${task.is_done ? "bg-gray-50 border-gray-100" : "bg-white border-gray-200"}`}>
                  <input type="checkbox" checked={task.is_done} onChange={() => toggleTask(task)}
                    className="mt-0.5 accent-blue-800 w-4 h-4 cursor-pointer" />
                  <div className="flex-1">
                    <p className={`text-sm ${task.is_done ? "line-through text-gray-400" : "text-gray-800"}`}>{task.title}</p>
                    {task.due_at && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        до {format(new Date(task.due_at), "d MMM, HH:mm", { locale: ru })}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Комментарии */}
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <h3 className="font-bold text-gray-800 mb-4">Комментарии</h3>
            <div className="space-y-3 mb-4 max-h-80 overflow-y-auto">
              {comments.length === 0 && <p className="text-sm text-gray-400">Комментариев нет</p>}
              {comments.map((c) => (
                <div key={c.id} className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-bold text-xs shrink-0">
                    {c.author?.name?.[0] || "?"}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="text-xs font-semibold text-gray-700">{c.author?.name || "Система"}</span>
                      <span className="text-xs text-gray-400">{format(new Date(c.created_at), "d MMM, HH:mm", { locale: ru })}</span>
                    </div>
                    <p className="text-sm text-gray-800 mt-0.5">{c.text}</p>
                  </div>
                </div>
              ))}
            </div>
            <form onSubmit={addComment} className="flex gap-2">
              <input value={newComment} onChange={(e) => setNewComment(e.target.value)}
                placeholder="Написать комментарий..."
                className="flex-1 border rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <button type="submit" className="bg-blue-800 text-white px-4 rounded-lg text-sm font-semibold hover:bg-blue-900 transition">
                Отправить
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, editing, onChange, onBlur, type = "text" }) {
  return (
    <div>
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      {editing ? (
        <input type={type} value={value || ""} onChange={(e) => onChange(e.target.value)} onBlur={onBlur}
          className="w-full border rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
      ) : (
        <p className="font-medium">{value || "—"}</p>
      )}
    </div>
  );
}
