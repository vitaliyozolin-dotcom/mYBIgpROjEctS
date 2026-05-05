import React, { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { format, formatDistanceToNow } from "date-fns";
import { ru } from "date-fns/locale";
import api from "../api/client.js";
import { askAI } from "../api/ai.js";
import toast from "react-hot-toast";

const STAGES = [
  { id: "new", label: "Новая заявка", color: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300" },
  { id: "no_answer", label: "Не дозвонились", color: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300" },
  { id: "contacted", label: "Первичный контакт", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300" },
  { id: "qualified", label: "Квалификация", color: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300" },
  { id: "selection", label: "Подбор объекта", color: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/40 dark:text-cyan-300" },
  { id: "showing_scheduled", label: "Показ назначен", color: "bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300" },
  { id: "showing_done", label: "Показ проведён", color: "bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300" },
  { id: "booking", label: "Бронь / Аванс", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" },
  { id: "documents", label: "Документы / Ипотека", color: "bg-teal-100 text-teal-700 dark:bg-teal-900/40 dark:text-teal-300" },
  { id: "won", label: "Сделка", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300" },
  { id: "lost", label: "Отказ / Архив", color: "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300" },
];

const SOURCE_LABELS = {
  manual: "Вручную", website: "Сайт", avito: "Авито", telegram: "Telegram",
  vk: "ВКонтакте", whatsapp: "WhatsApp", instagram: "Instagram", partners: "Партнёры", referral: "Рекомендация",
};

const ALL_TAGS = ["Горячий", "VIP", "Ипотека", "Инвестор", "Срочно", "Повторный", "Семья", "Корпоратив"];

const PROFILE_FIELDS = [
  { key: "property_type", label: "Тип объекта", placeholder: "Квартира, дом, коммерция..." },
  { key: "location", label: "Локация / район", placeholder: "Район, ЖК, город" },
  { key: "rooms", label: "Комнаты", placeholder: "1к, 2к, 3к, студия" },
  { key: "desired_area", label: "Площадь", placeholder: "от 45 м²" },
  { key: "purchase_goal", label: "Цель покупки", placeholder: "Для себя, инвестиция, детям..." },
  { key: "payment_method", label: "Способ оплаты", placeholder: "Наличные, ипотека, рассрочка" },
  { key: "mortgage_status", label: "Ипотека", placeholder: "Одобрена, нужна помощь, нет" },
  { key: "purchase_timeline", label: "Срок покупки", placeholder: "Срочно, месяц, 3–6 месяцев" },
  { key: "main_objection", label: "Главное возражение", placeholder: "Дорого, думает, боится ипотеки..." },
];

function fmtMoney(value) {
  if (!value) return "—";
  return parseInt(value).toLocaleString("ru-RU") + " ₽";
}

function scoreMeta(score = 0) {
  if (score >= 80) return { label: "Горячий", tone: "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/40 dark:text-emerald-300 dark:border-emerald-800" };
  if (score >= 50) return { label: "Тёплый", tone: "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:border-amber-800" };
  return { label: "Холодный", tone: "bg-red-100 text-red-600 border-red-200 dark:bg-red-900/40 dark:text-red-300 dark:border-red-800" };
}

function getScoreReasons(lead) {
  const reasons = [];
  if (lead.budget) reasons.push(`бюджет ${fmtMoney(lead.budget)}`);
  if ((lead.tags || []).includes("Горячий")) reasons.push("тег Горячий");
  if ((lead.tags || []).includes("Ипотека")) reasons.push("ипотека");
  if (lead.next_action) reasons.push("есть следующий шаг");
  if (lead.next_date) reasons.push("назначено касание");
  if (lead.property_type || lead.location || lead.purchase_goal) reasons.push("заполнена потребность");
  return reasons.length ? reasons.slice(0, 4).join(" · ") : "мало данных по потребности и следующему шагу";
}

function getRiskLabel(lead) {
  if (lead.stage === "lost") return { label: "Архив", tone: "text-slate-400" };
  if (!lead.next_action) return { label: "Риск: нет следующего шага", tone: "text-red-500" };
  if (!lead.next_date) return { label: "Риск: нет даты касания", tone: "text-amber-500" };
  return { label: "Под контролем", tone: "text-emerald-500" };
}

function buildAISummary(lead) {
  const stage = STAGES.find((s) => s.id === lead.stage)?.label || lead.stage;
  const need = [lead.property_type, lead.location, lead.rooms, lead.purchase_goal].filter(Boolean).join(" · ");
  const next = lead.next_action ? `Следующий шаг: ${lead.next_action}.` : "Следующий шаг не задан.";
  const objection = lead.main_objection ? `Возражение: ${lead.main_objection}.` : "";
  return `${stage}. ${need || "Потребность пока не заполнена"}. Бюджет: ${fmtMoney(lead.budget)}. ${next} ${objection}`;
}

function ScoreBadge({ score }) {
  const meta = scoreMeta(score);
  return <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${meta.tone}`}>Score: {score} · {meta.label}</span>;
}

function AIChat({ lead }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatRef = useRef(null);

  useEffect(() => { if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight; }, [messages]);

  async function send(text) {
    const msg = text || input;
    if (!msg.trim()) return;
    const userMsg = { role: "user", content: msg };
    const newMsgs = [...messages, userMsg];
    setMessages(newMsgs);
    setInput("");
    setLoading(true);
    try {
      const context = `Лид: ${lead.name}; стадия: ${STAGES.find(s => s.id === lead.stage)?.label}; бюджет: ${fmtMoney(lead.budget)}; score: ${lead.score ?? 50}; теги: ${(lead.tags || []).join(", ") || "нет"}; потребность: ${buildAISummary(lead)}; заметки: ${lead.notes || "нет"}`;
      const reply = await askAI(newMsgs, context);
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "AI временно недоступен. Проверьте OPENAI_API_KEY на сервере и повторите запрос." }]);
    } finally {
      setLoading(false);
    }
  }

  const suggestions = ["Дай 3 следующих шага", "Напиши скрипт звонка", "Напиши WhatsApp-сообщение", "Почему такой score?"];

  return (
    <div className="flex flex-col" style={{ height: "420px" }}>
      <div ref={chatRef} className="flex-1 overflow-auto space-y-3 mb-3 pr-1">
        {messages.length === 0 && (
          <div className="pt-2">
            <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800/50 rounded-2xl p-3 mb-3">
              <p className="text-xs font-semibold text-indigo-700 dark:text-indigo-300 mb-1">AI-summary</p>
              <p className="text-sm text-indigo-900 dark:text-indigo-100 leading-relaxed">{buildAISummary(lead)}</p>
            </div>
            <div className="space-y-2">
              {suggestions.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="w-full text-left text-sm text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-100 dark:border-indigo-800 rounded-xl px-3 py-2 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 transition-colors">→ {s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] text-sm leading-relaxed px-3 py-2 rounded-2xl whitespace-pre-wrap ${m.role === "user" ? "bg-indigo-600 text-white rounded-br-sm" : "bg-slate-100 dark:bg-slate-700 text-slate-800 dark:text-slate-200 rounded-bl-sm"}`}>{m.content}</div>
          </div>
        ))}
        {loading && <div className="flex gap-1.5 px-3 py-2">{[0, 1, 2].map((i) => <div key={i} className="w-2 h-2 rounded-full bg-indigo-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />)}</div>}
      </div>
      <div className="flex gap-2">
        <input value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()} placeholder="Спросите AI..." className="flex-1 border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 placeholder:text-slate-400" />
        <button onClick={() => send()} disabled={loading} className="bg-indigo-600 text-white px-4 rounded-xl text-sm font-bold hover:bg-indigo-700 transition disabled:opacity-50">↑</button>
      </div>
    </div>
  );
}

function InfoRow({ label, value, editing, onChange, onBlur, type = "text", href, placeholder }) {
  return (
    <div>
      <p className="text-xs text-slate-400 dark:text-slate-500 mb-0.5">{label}</p>
      {editing ? (
        <input type={type} value={value || ""} placeholder={placeholder || ""} onChange={(e) => onChange(e.target.value)} onBlur={onBlur} className="w-full text-sm border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-400 placeholder:text-slate-400" />
      ) : href ? (
        <a href={href} className="text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:underline" onClick={(e) => e.stopPropagation()}>{value || "—"}</a>
      ) : (
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{type === "number" && value ? fmtMoney(value) : value || "—"}</p>
      )}
    </div>
  );
}

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
  const [activeTab, setActiveTab] = useState("info");

  const fetchAll = useCallback(async () => {
    const [l, c, t, h] = await Promise.all([api.get(`/leads/${id}`), api.get(`/comments/lead/${id}`), api.get(`/tasks/lead/${id}`), api.get(`/leads/${id}/stage-history`)]);
    setLead(l.data); setForm(l.data); setComments(c.data); setTasks(t.data); setStageHistory(h.data);
  }, [id]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  async function saveField(field, value) {
    try {
      const { data } = await api.patch(`/leads/${id}`, { [field]: value });
      setLead(data); setForm(data); toast.success("Сохранено");
    } catch { toast.error("Ошибка"); }
  }

  async function toggleTag(tag) {
    const current = form.tags || [];
    const next = current.includes(tag) ? current.filter((t) => t !== tag) : [...current, tag];
    setForm((f) => ({ ...f, tags: next }));
    await saveField("tags", next);
  }

  async function addComment(e) {
    e.preventDefault();
    if (!newComment.trim()) return;
    try {
      await api.post("/comments", { text: newComment, lead_id: parseInt(id) });
      setNewComment("");
      const { data } = await api.get(`/comments/lead/${id}`);
      setComments(data);
    } catch { toast.error("Не удалось добавить комментарий"); }
  }

  async function addTask(e) {
    e.preventDefault();
    if (!newTask.title.trim()) return;
    try {
      await api.post("/tasks", { title: newTask.title, lead_id: parseInt(id), due_at: newTask.due_at || null });
      setNewTask({ title: "", due_at: "" });
      const { data } = await api.get(`/tasks/lead/${id}`);
      setTasks(data); toast.success("Задача добавлена");
    } catch { toast.error("Не удалось добавить задачу"); }
  }

  async function toggleTask(task) {
    await api.patch(`/tasks/${task.id}`, { is_done: !task.is_done });
    api.get(`/tasks/lead/${id}`).then((r) => setTasks(r.data));
  }

  if (!lead) return <div className="flex items-center justify-center h-full bg-slate-50 dark:bg-slate-950"><div className="w-8 h-8 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin" /></div>;

  const stageObj = STAGES.find((s) => s.id === lead.stage);
  const initials = lead.name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const activeTasks = tasks.filter((t) => !t.is_done).length;
  const risk = getRiskLabel(lead);

  const TABS = [
    { id: "info", label: "Обзор" },
    { id: "tasks", label: activeTasks > 0 ? `Задачи (${activeTasks})` : "Задачи" },
    { id: "comments", label: comments.length > 0 ? `Комм. (${comments.length})` : "Комм." },
    { id: "history", label: "История" },
    { id: "ai", label: "🤖 AI" },
  ];

  return (
    <div className="h-full overflow-auto bg-slate-50 dark:bg-slate-950">
      <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-4 py-3 flex items-center gap-3 sticky top-0 z-10">
        <button onClick={() => navigate("/board")} className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition text-lg">←</button>
        <div className="flex-1 min-w-0">
          <h1 className="font-bold text-slate-900 dark:text-slate-100 text-base truncate">{lead.name}</h1>
          <p className="text-xs text-slate-400 dark:text-slate-500">{formatDistanceToNow(new Date(lead.created_at), { locale: ru, addSuffix: true })}</p>
        </div>
        <button onClick={() => setEditing(!editing)} className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline shrink-0">{editing ? "Готово" : "Изм."}</button>
      </div>

      {(lead.phone || lead.email) && (
        <div className="bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-slate-800 px-4 py-2 flex gap-4 overflow-x-auto">
          {lead.phone && <a href={`tel:${lead.phone}`} className="flex items-center gap-1.5 text-sm text-indigo-600 dark:text-indigo-400 hover:underline whitespace-nowrap">📞 {lead.phone}</a>}
          {lead.phone && <a href={`https://wa.me/${String(lead.phone).replace(/\D/g, "")}`} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-sm text-emerald-600 dark:text-emerald-400 hover:underline whitespace-nowrap">💬 WhatsApp</a>}
          {lead.email && <a href={`mailto:${lead.email}`} className="flex items-center gap-1.5 text-sm text-indigo-600 dark:text-indigo-400 hover:underline whitespace-nowrap">✉️ {lead.email}</a>}
        </div>
      )}

      <div className="bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-slate-800 flex overflow-x-auto sticky top-[56px] z-10">
        {TABS.map((tab) => <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`py-2.5 px-3 text-xs font-semibold whitespace-nowrap border-b-2 transition-colors ${activeTab === tab.id ? "border-indigo-600 text-indigo-600 dark:text-indigo-400 dark:border-indigo-400" : "border-transparent text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-400"}`}>{tab.label}</button>)}
      </div>

      <div className="max-w-2xl mx-auto p-4 space-y-4 pb-28">
        {activeTab === "info" && (
          <>
            <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-100 dark:border-slate-700 shadow-sm space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 font-bold text-lg flex items-center justify-center shrink-0">{initials}</div>
                <div className="flex-1 min-w-0">
                  {editing ? <input value={form.name || ""} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} onBlur={() => saveField("name", form.name)} className="font-bold text-slate-900 dark:text-slate-100 border-b border-indigo-300 dark:border-indigo-600 outline-none bg-transparent w-full text-base" /> : <p className="font-bold text-slate-900 dark:text-slate-100 truncate">{lead.name}</p>}
                  <div className="flex items-center gap-2 mt-1 flex-wrap"><p className="text-xs text-slate-400 dark:text-slate-500">{SOURCE_LABELS[lead.source] || lead.source}</p><ScoreBadge score={lead.score ?? 50} /></div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-xl bg-slate-50 dark:bg-slate-900/50 p-3 border border-slate-100 dark:border-slate-700"><p className="text-[11px] text-slate-400 mb-1">Стадия</p><span className={`text-xs font-semibold px-2 py-1 rounded-full ${stageObj?.color || "bg-slate-100"}`}>{stageObj?.label || lead.stage}</span></div>
                <div className="rounded-xl bg-slate-50 dark:bg-slate-900/50 p-3 border border-slate-100 dark:border-slate-700"><p className="text-[11px] text-slate-400 mb-1">Риск</p><p className={`text-xs font-semibold ${risk.tone}`}>{risk.label}</p></div>
                <div className="rounded-xl bg-slate-50 dark:bg-slate-900/50 p-3 border border-slate-100 dark:border-slate-700"><p className="text-[11px] text-slate-400 mb-1">Следующий шаг</p><p className="text-xs font-semibold text-slate-800 dark:text-slate-200">{lead.next_action || "Не задан"}</p></div>
                <div className="rounded-xl bg-slate-50 dark:bg-slate-900/50 p-3 border border-slate-100 dark:border-slate-700"><p className="text-[11px] text-slate-400 mb-1">Касание</p><p className="text-xs font-semibold text-slate-800 dark:text-slate-200">{lead.next_date ? format(new Date(lead.next_date), "d MMM, HH:mm", { locale: ru }) : "Не назначено"}</p></div>
              </div>

              <div className="rounded-xl bg-indigo-50 dark:bg-indigo-900/20 p-3 border border-indigo-100 dark:border-indigo-800/50"><p className="text-[11px] font-semibold text-indigo-700 dark:text-indigo-300 mb-1">Почему score {lead.score ?? 50}</p><p className="text-xs text-indigo-900 dark:text-indigo-100 leading-relaxed">{getScoreReasons(lead)}</p></div>
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-100 dark:border-slate-700 shadow-sm space-y-3">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">Контакт и сделка</h3>
              <InfoRow label="Телефон" value={form.phone} editing={editing} onChange={(v) => setForm((f) => ({ ...f, phone: v }))} onBlur={() => saveField("phone", form.phone)} href={form.phone ? `tel:${form.phone}` : null} />
              <InfoRow label="Email" value={form.email} editing={editing} onChange={(v) => setForm((f) => ({ ...f, email: v }))} onBlur={() => saveField("email", form.email)} href={form.email ? `mailto:${form.email}` : null} />
              <InfoRow label="Бюджет" value={form.budget} type="number" editing={editing} onChange={(v) => setForm((f) => ({ ...f, budget: v }))} onBlur={() => saveField("budget", form.budget ? parseInt(form.budget) : null)} />
              <div><p className="text-xs text-slate-400 dark:text-slate-500 mb-1">Стадия</p><select value={form.stage} onChange={(e) => { setForm((f) => ({ ...f, stage: e.target.value })); saveField("stage", e.target.value); }} className="w-full text-sm border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400">{STAGES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</select></div>
              <InfoRow label="Следующее действие" value={form.next_action} editing={editing} onChange={(v) => setForm((f) => ({ ...f, next_action: v }))} onBlur={() => saveField("next_action", form.next_action || null)} placeholder="Позвонить, отправить подборку..." />
              {editing && <InfoRow label="Дата следующего действия" value={form.next_date ? form.next_date.slice(0, 16) : ""} type="datetime-local" editing onChange={(v) => setForm((f) => ({ ...f, next_date: v }))} onBlur={() => saveField("next_date", form.next_date || null)} />}
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-100 dark:border-slate-700 shadow-sm space-y-3">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">Потребность по недвижимости</h3>
              {PROFILE_FIELDS.map((field) => <InfoRow key={field.key} label={field.label} value={form[field.key]} editing={editing} onChange={(v) => setForm((f) => ({ ...f, [field.key]: v }))} onBlur={() => saveField(field.key, form[field.key] || null)} placeholder={field.placeholder} />)}
            </div>

            <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-100 dark:border-slate-700 shadow-sm space-y-3">
              <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">Теги и заметки</h3>
              <div className="flex flex-wrap gap-1.5">{ALL_TAGS.map((tag) => { const on = (form.tags || []).includes(tag); return <button key={tag} onClick={() => toggleTag(tag)} className={`text-xs px-2.5 py-1 rounded-full font-medium border transition-colors ${on ? "bg-indigo-600 text-white border-indigo-600" : "bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 border-slate-200 dark:border-slate-600 hover:border-indigo-400"}`}>{tag}</button>; })}</div>
              {editing ? <textarea rows={3} value={form.notes || ""} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} onBlur={() => saveField("notes", form.notes)} placeholder="Заметки по клиенту..." className="w-full text-sm border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none placeholder:text-slate-400" /> : lead.notes ? <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-xl border border-amber-100 dark:border-amber-800/40 text-xs text-amber-800 dark:text-amber-300">{lead.notes}</div> : <p className="text-sm text-slate-400">Заметок нет</p>}
            </div>
          </>
        )}

        {activeTab === "tasks" && <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-100 dark:border-slate-700 shadow-sm"><form onSubmit={addTask} className="flex gap-2 mb-4"><input placeholder="Новая задача..." value={newTask.title} onChange={(e) => setNewTask((t) => ({ ...t, title: e.target.value }))} className="flex-1 border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 placeholder:text-slate-400" /><input type="datetime-local" value={newTask.due_at} onChange={(e) => setNewTask((t) => ({ ...t, due_at: e.target.value }))} className="border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-xl px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 w-32" /><button type="submit" className="bg-indigo-600 text-white px-4 rounded-xl text-sm font-bold hover:bg-indigo-700 transition">+</button></form><div className="space-y-2">{tasks.length === 0 && <p className="text-sm text-slate-400 dark:text-slate-500">Задач нет</p>}{tasks.map((task) => <div key={task.id} className={`flex items-start gap-3 p-3 rounded-xl border transition ${task.is_done ? "bg-slate-50 dark:bg-slate-900/50 border-slate-100 dark:border-slate-700/50 opacity-60" : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-600"}`}><input type="checkbox" checked={task.is_done} onChange={() => toggleTask(task)} className="mt-0.5 w-4 h-4 accent-indigo-600 cursor-pointer" /><div className="flex-1"><p className={`text-sm ${task.is_done ? "line-through text-slate-400 dark:text-slate-500" : "text-slate-800 dark:text-slate-200"}`}>{task.title}</p>{task.due_at && <p className={`text-xs mt-0.5 ${new Date(task.due_at) < new Date() && !task.is_done ? "text-red-500" : "text-slate-400 dark:text-slate-500"}`}>до {format(new Date(task.due_at), "d MMM, HH:mm", { locale: ru })}</p>}</div></div>)}</div></div>}

        {activeTab === "comments" && <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-100 dark:border-slate-700 shadow-sm"><div className="space-y-4 mb-4 max-h-80 overflow-y-auto">{comments.length === 0 && <p className="text-sm text-slate-400 dark:text-slate-500">Комментариев нет</p>}{comments.map((c) => <div key={c.id} className="flex gap-3"><div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 font-bold text-xs flex items-center justify-center shrink-0">{c.author?.name?.[0] || "?"}</div><div className="flex-1 bg-slate-50 dark:bg-slate-700/50 rounded-xl p-3"><div className="flex items-baseline gap-2 mb-1"><span className="text-xs font-semibold text-slate-700 dark:text-slate-300">{c.author?.name || "Система"}</span><span className="text-xs text-slate-400 dark:text-slate-500">{format(new Date(c.created_at), "d MMM, HH:mm", { locale: ru })}</span></div><p className="text-sm text-slate-800 dark:text-slate-200">{c.text}</p></div></div>)}</div><form onSubmit={addComment} className="flex gap-2"><input value={newComment} onChange={(e) => setNewComment(e.target.value)} placeholder="Написать комментарий..." className="flex-1 border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 placeholder:text-slate-400" /><button type="submit" className="bg-indigo-600 text-white px-4 rounded-xl text-sm font-semibold hover:bg-indigo-700 transition">→</button></form></div>}

        {activeTab === "history" && <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-100 dark:border-slate-700 shadow-sm"><h3 className="font-semibold text-slate-800 dark:text-slate-200 mb-4 text-sm">⏱ Время в стадиях</h3>{stageHistory.length === 0 ? <p className="text-sm text-slate-400 dark:text-slate-500">История пуста</p> : <div className="space-y-2">{stageHistory.map((h, i) => <div key={i} className={`flex items-center gap-3 p-2.5 rounded-xl ${h.is_current ? "bg-indigo-50 dark:bg-indigo-900/30 border border-indigo-100 dark:border-indigo-800/50" : "bg-slate-50 dark:bg-slate-700/30"}`}><div className={`w-2 h-2 rounded-full shrink-0 ${h.is_current ? "bg-indigo-500" : "bg-slate-300 dark:bg-slate-600"}`} /><span className="text-sm flex-1 text-slate-700 dark:text-slate-300">{h.label}</span><span className={`text-xs font-medium ${h.is_current ? "text-indigo-600 dark:text-indigo-400" : "text-slate-400 dark:text-slate-500"}`}>{h.days > 0 ? `${h.days}д ` : ""}{h.hours}ч{h.is_current && " (сейчас)"}</span></div>)}</div>}</div>}

        {activeTab === "ai" && <div className="bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-100 dark:border-slate-700 shadow-sm"><AIChat lead={lead} /></div>}
      </div>
    </div>
  );
}
