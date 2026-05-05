import React, { useEffect, useState } from "react";
import api from "../api/client.js";
import toast from "react-hot-toast";

const ROLE_LABELS = { admin: "Администратор", manager: "Менеджер" };

const EMPTY_FORM = { name: "", email: "", password: "", role: "manager" };

export default function Users() {
  const [users, setUsers] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [editId, setEditId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [loading, setLoading] = useState(false);

  async function fetchUsers() {
    try {
      const { data } = await api.get("/auth/users");
      setUsers(data);
    } catch {
      toast.error("Нет доступа");
    }
  }

  useEffect(() => { fetchUsers(); }, []);

  async function addUser(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/register", form);
      toast.success("Пользователь добавлен");
      setForm(EMPTY_FORM);
      setShowAdd(false);
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Ошибка");
    } finally {
      setLoading(false);
    }
  }

  async function saveEdit(userId) {
    try {
      await api.patch(`/auth/users/${userId}`, editForm);
      toast.success("Сохранено");
      setEditId(null);
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Ошибка");
    }
  }

  async function toggleActive(user) {
    try {
      await api.patch(`/auth/users/${user.id}`, { is_active: !user.is_active });
      toast.success(user.is_active ? "Деактивирован" : "Активирован");
      fetchUsers();
    } catch {
      toast.error("Ошибка");
    }
  }

  function startEdit(user) {
    setEditId(user.id);
    setEditForm({ name: user.name, email: user.email, role: user.role, telegram_id: user.telegram_id || "" });
  }

  return (
    <div className="h-full overflow-auto bg-slate-50">
      <div className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-4 sticky top-0 z-10">
        <h1 className="font-bold text-slate-900 text-lg flex-1">Управление пользователями</h1>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="bg-indigo-600 text-white px-4 py-2 rounded-xl text-sm font-semibold hover:bg-indigo-700 transition"
        >
          + Добавить
        </button>
      </div>

      <div className="max-w-3xl mx-auto p-5 space-y-5">
        {/* Add user form */}
        {showAdd && (
          <div className="bg-white rounded-2xl p-5 border border-slate-100 shadow-sm">
            <h2 className="font-semibold text-slate-800 mb-4">Новый пользователь</h2>
            <form onSubmit={addUser} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">Имя *</label>
                  <input
                    required value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    placeholder="Иван Петров"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">Email *</label>
                  <input
                    required type="email" value={form.email}
                    onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                    placeholder="ivan@company.ru"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">Пароль *</label>
                  <input
                    required type="password" value={form.password}
                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                    placeholder="Минимум 6 символов"
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">Роль</label>
                  <select
                    value={form.role}
                    onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                    className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                  >
                    <option value="manager">Менеджер</option>
                    <option value="admin">Администратор</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  type="submit" disabled={loading}
                  className="bg-indigo-600 text-white px-5 py-2 rounded-xl text-sm font-semibold hover:bg-indigo-700 transition disabled:opacity-50"
                >
                  {loading ? "Сохранение..." : "Создать"}
                </button>
                <button
                  type="button" onClick={() => setShowAdd(false)}
                  className="px-5 py-2 rounded-xl text-sm text-slate-500 hover:bg-slate-100 transition"
                >
                  Отмена
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Users list */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          {users.length === 0 ? (
            <p className="p-6 text-sm text-slate-400 text-center">Нет пользователей</p>
          ) : (
            <div className="divide-y divide-slate-100">
              {users.map((user) => (
                <div key={user.id}>
                  {editId === user.id ? (
                    <div className="p-4 bg-indigo-50">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                        <div>
                          <label className="text-xs text-slate-500 mb-1 block">Имя</label>
                          <input
                            value={editForm.name}
                            onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
                            className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-slate-500 mb-1 block">Email</label>
                          <input
                            type="email" value={editForm.email}
                            onChange={(e) => setEditForm((f) => ({ ...f, email: e.target.value }))}
                            className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-slate-500 mb-1 block">Новый пароль (опционально)</label>
                          <input
                            type="password" placeholder="Оставьте пустым, чтобы не менять"
                            onChange={(e) => setEditForm((f) => ({ ...f, password: e.target.value || undefined }))}
                            className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-slate-500 mb-1 block">Роль</label>
                          <select
                            value={editForm.role}
                            onChange={(e) => setEditForm((f) => ({ ...f, role: e.target.value }))}
                            className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                          >
                            <option value="manager">Менеджер</option>
                            <option value="admin">Администратор</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-xs text-slate-500 mb-1 block">Telegram ID</label>
                          <input
                            type="number" value={editForm.telegram_id || ""}
                            onChange={(e) => setEditForm((f) => ({ ...f, telegram_id: e.target.value ? parseInt(e.target.value) : null }))}
                            placeholder="Числовой ID из @userinfobot"
                            className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
                          />
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => saveEdit(user.id)}
                          className="bg-indigo-600 text-white px-4 py-1.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 transition"
                        >
                          Сохранить
                        </button>
                        <button
                          onClick={() => setEditId(null)}
                          className="px-4 py-1.5 rounded-lg text-sm text-slate-500 hover:bg-slate-200 transition"
                        >
                          Отмена
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className={`flex items-center gap-3 px-4 py-3 ${!user.is_active ? "opacity-50" : ""}`}>
                      <div className="w-10 h-10 rounded-full bg-indigo-100 text-indigo-700 font-bold text-sm flex items-center justify-center shrink-0">
                        {user.name[0]?.toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-semibold text-slate-900 text-sm">{user.name}</p>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${user.role === "admin" ? "bg-purple-100 text-purple-700" : "bg-blue-100 text-blue-700"}`}>
                            {ROLE_LABELS[user.role] || user.role}
                          </span>
                          {!user.is_active && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">Деактивирован</span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5">{user.email}</p>
                        {user.telegram_id && (
                          <p className="text-xs text-slate-400">TG: {user.telegram_id}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => startEdit(user)}
                          className="text-xs text-indigo-600 hover:underline px-2 py-1"
                        >
                          Изменить
                        </button>
                        <button
                          onClick={() => toggleActive(user)}
                          className={`text-xs px-2 py-1 rounded-lg transition ${user.is_active ? "text-red-500 hover:bg-red-50" : "text-emerald-600 hover:bg-emerald-50"}`}
                        >
                          {user.is_active ? "Деактив." : "Активир."}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Telegram tip */}
        <div className="bg-blue-50 border border-blue-100 rounded-2xl p-4">
          <p className="text-sm font-semibold text-blue-800 mb-1">Как привязать Telegram?</p>
          <p className="text-xs text-blue-700">
            1. Откройте бота CRM в Telegram и отправьте /start<br />
            2. Узнайте свой ID через @userinfobot или @getmyid_bot<br />
            3. Введите числовой ID в поле «Telegram ID» для вашего пользователя
          </p>
        </div>
      </div>
    </div>
  );
}
