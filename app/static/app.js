/* PlantCare – interfaz web.
 * Solo presenta datos y envía acciones a la API. Las reglas de negocio
 * (estados, vencimiento, validaciones) se calculan siempre en el servidor. */
"use strict";

// ---------- Presentación ----------
const CARE = {
  riego: { label: "Riego", icon: "💧" },
  fertilizacion: { label: "Fertilización", icon: "🌱" },
  poda: { label: "Poda", icon: "✂️" },
};
const STATUS_LABEL = { pendiente: "Pendiente", vencida: "Vencida", completada: "Completada" };
const FIELD_HINT = {
  plant_name: "Escribe el nombre de la planta (entre 1 y 100 caracteres).",
  care_type: "Elige un tipo de cuidado: riego, fertilización o poda.",
  scheduled_date: "Indica una fecha válida.",
  description: "La descripción no puede superar los 500 caracteres.",
};
const FORM_FIELDS = Object.keys(FIELD_HINT);

const $ = (selector) => document.querySelector(selector);

// ---------- Cliente de la API ----------
class ApiError extends Error {
  constructor(message, status, fieldErrors = {}) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors;
  }
}

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new ApiError("No se pudo conectar con el servidor. Comprueba que la API esté en ejecución.", 0);
  }

  let body = null;
  try { body = await response.json(); } catch { /* sin cuerpo JSON */ }

  if (response.ok) return body;

  if (response.status === 422) {
    const fieldErrors = {};
    for (const item of Array.isArray(body?.detail) ? body.detail : []) {
      const field = item.loc?.[item.loc.length - 1];
      if (FORM_FIELDS.includes(field)) fieldErrors[field] = FIELD_HINT[field];
    }
    throw new ApiError("Los datos enviados no son válidos. Revisa el formulario.", 422, fieldErrors);
  }
  if (response.status === 404) throw new ApiError("La tarea ya no existe.", 404);
  throw new ApiError("El servidor tuvo un problema. Inténtalo de nuevo en unos segundos.", response.status);
}

// ---------- Utilidades de DOM y fechas ----------
function el(tag, { className, text, attrs } = {}, children = []) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;   // textContent: nunca interpreta HTML
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
  for (const child of children) node.append(child);
  return node;
}

function formatDate(isoDate) {
  const [y, m, d] = isoDate.split("-").map(Number);       // evita desfases por zona horaria
  return new Date(y, m - 1, d).toLocaleDateString("es", {
    weekday: "short", day: "numeric", month: "short", year: "numeric",
  });
}

function todayLocalISO() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function relativeDays(n) {
  if (n < 0) return `Venció hace ${-n} ${-n === 1 ? "día" : "días"}`;
  if (n === 0) return "Es hoy";
  if (n === 1) return "Mañana";
  return `En ${n} días`;
}

// ---------- Mensajes ----------
let bannerTimer;
function showBanner(message, kind = "error") {
  const banner = $("#banner");
  banner.className = `banner banner--${kind}`;
  banner.setAttribute("role", kind === "error" ? "alert" : "status");
  banner.replaceChildren(el("span", { text: message }));
  const close = el("button", { text: "×", attrs: { type: "button", "aria-label": "Cerrar mensaje" } });
  close.addEventListener("click", hideBanner);
  banner.append(close);
  banner.hidden = false;
  clearTimeout(bannerTimer);
  if (kind === "ok") bannerTimer = setTimeout(hideBanner, 4000);
}
function hideBanner() { $("#banner").hidden = true; }

function showState(container, { icon, text, error = false, action }) {
  container.className = error ? "state state--error" : "state";
  container.replaceChildren(
    el("span", { className: "state__icon", text: icon, attrs: { "aria-hidden": "true" } }),
    el("p", { text }),
  );
  if (action) {
    const btn = el("button", { className: "btn btn--ghost", text: action.label, attrs: { type: "button" } });
    btn.addEventListener("click", action.onClick);
    container.append(btn);
  }
  container.hidden = false;
}

// ---------- Render ----------
function renderTask(task, { reminder = false } = {}) {
  const care = CARE[task.care_type] ?? { label: task.care_type, icon: "🪴" };
  const meta = reminder
    ? [el("span", { className: `task__time task__time--${task.status}`, text: relativeDays(task.days_until_due) }),
       document.createTextNode(` · ${care.label} · ${formatDate(task.scheduled_date)}`)]
    : [document.createTextNode(`${care.label} · ${formatDate(task.scheduled_date)}`)];

  const body = el("div", {}, [
    el("h3", { className: "task__title" }, [
      el("span", { text: task.plant_name }),
      el("span", { className: `badge badge--${task.status}`, text: STATUS_LABEL[task.status] ?? task.status }),
    ]),
    el("p", { className: "task__meta" }, meta),
  ]);
  if (task.description) body.append(el("p", { className: "task__desc", text: task.description }));
  if (task.completed_at && !reminder) {
    const done = new Date(task.completed_at).toLocaleDateString("es", { day: "numeric", month: "short", year: "numeric" });
    body.append(el("p", { className: "task__meta", text: `Completada el ${done}` }));
  }

  const item = el("li", { className: `task task--${task.status}` }, [
    el("span", { className: "task__icon", text: care.icon, attrs: { "aria-hidden": "true" } }),
    body,
  ]);

  if (task.status !== "completada") {
    const btn = el("button", {
      className: "btn btn--small", text: "✓ Completar",
      attrs: { type: "button", "aria-label": `Marcar como completada: ${care.label} de ${task.plant_name}` },
    });
    btn.addEventListener("click", () => completeTask(task.id, btn));
    item.append(btn);
  }
  return item;
}

// ---------- Carga de datos ----------
const filters = () => ({ status: $("#filter-status").value, plant: $("#filter-plant").value.trim() });
const filtersActive = () => Object.values(filters()).some(Boolean);
let tasksRequest = 0;
let remindersRequest = 0;

async function loadTasks() {
  const request = ++tasksRequest;
  const { status, plant } = filters();
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (plant) params.set("plant_name", plant);
  const list = $("#task-list"), state = $("#tasks-state");

  showState(state, { icon: "⏳", text: "Cargando tareas…" });
  try {
    const tasks = await api(`/tasks${params.size ? `?${params}` : ""}`);
    if (request !== tasksRequest) return;                  // respuesta obsoleta
    list.replaceChildren(...tasks.map((t) => renderTask(t)));
    if (tasks.length) {
      state.hidden = true;
    } else if (filtersActive()) {
      showState(state, { icon: "🔍", text: "Ninguna tarea coincide con los filtros.",
        action: { label: "Limpiar filtros", onClick: clearFilters } });
    } else {
      showState(state, { icon: "🪴", text: "Aún no hay tareas. Crea la primera con el formulario." });
    }
  } catch (err) {
    if (request !== tasksRequest) return;
    list.replaceChildren();
    showState(state, { icon: "⚠️", text: err.message, error: true,
      action: { label: "Reintentar", onClick: loadTasks } });
  }
}

async function loadReminders() {
  const request = ++remindersRequest;
  const days = $("#days-ahead").value;
  const list = $("#reminders-list"), state = $("#reminders-state");

  showState(state, { icon: "⏳", text: "Cargando recordatorios…" });
  try {
    const reminders = await api(`/reminders?days_ahead=${encodeURIComponent(days)}`);
    if (request !== remindersRequest) return;
    list.replaceChildren(...reminders.map((r) => renderTask(r, { reminder: true })));
    if (reminders.length) state.hidden = true;
    else showState(state, { icon: "🎉", text: `Nada pendiente en los próximos ${days} días. ¡Tus plantas están al día!` });
  } catch (err) {
    if (request !== remindersRequest) return;
    list.replaceChildren();
    showState(state, { icon: "⚠️", text: err.message, error: true,
      action: { label: "Reintentar", onClick: loadReminders } });
  }
}

// Sugerencias de plantas conocidas (el filtro de la API busca el nombre exacto).
async function loadPlantOptions() {
  try {
    const tasks = await api("/tasks");
    const names = [...new Set(tasks.map((t) => t.plant_name))].sort((a, b) => a.localeCompare(b, "es"));
    $("#plant-options").replaceChildren(...names.map((n) => el("option", { attrs: { value: n } })));
  } catch { /* las sugerencias son opcionales */ }
}

const refreshAll = () => Promise.all([loadTasks(), loadReminders()]);

// ---------- Acciones ----------
async function completeTask(id, button) {
  button.disabled = true;
  try {
    await api(`/tasks/${encodeURIComponent(id)}/complete`, { method: "POST" });
    showBanner("Tarea marcada como completada.", "ok");
  } catch (err) {
    showBanner(err.message, "error");
  }
  await refreshAll();       // también tras un 404, para reflejar el estado real
}

function clearFieldErrors() {
  for (const field of FORM_FIELDS) {
    $(`#err-${field}`).textContent = "";
    $(`#${field}`).removeAttribute("aria-invalid");
  }
}

function showFieldErrors(fieldErrors) {
  let first = null;
  for (const [field, message] of Object.entries(fieldErrors)) {
    $(`#err-${field}`).textContent = message;
    $(`#${field}`).setAttribute("aria-invalid", "true");
    first ??= $(`#${field}`);
  }
  first?.focus();
}

async function submitTask(event) {
  event.preventDefault();
  clearFieldErrors();
  hideBanner();

  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  const payload = {
    plant_name: data.plant_name,
    care_type: data.care_type,
    scheduled_date: data.scheduled_date,
    description: data.description || null,
  };
  // Pistas inmediatas para campos vacíos; la validación definitiva la hace la API.
  const local = {};
  if (!payload.plant_name.trim()) local.plant_name = FIELD_HINT.plant_name;
  if (!payload.scheduled_date) local.scheduled_date = FIELD_HINT.scheduled_date;
  if (Object.keys(local).length) return showFieldErrors(local);

  const button = $("#submit-btn");
  button.disabled = true;
  button.textContent = "Registrando…";
  try {
    const task = await api("/tasks", { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    $("#scheduled_date").value = todayLocalISO();
    showBanner(`Tarea registrada: ${CARE[task.care_type]?.label ?? task.care_type} de ${task.plant_name}.`, "ok");
    await Promise.all([refreshAll(), loadPlantOptions()]);
  } catch (err) {
    if (err.status === 422 && Object.keys(err.fieldErrors).length) showFieldErrors(err.fieldErrors);
    showBanner(err.message, "error");
  } finally {
    button.disabled = false;
    button.textContent = "Registrar tarea";
  }
}

function clearFilters() {
  $("#filter-status").value = "";
  $("#filter-plant").value = "";
  loadTasks();
}

// ---------- Inicio ----------
let debounce;
function init() {
  $("#scheduled_date").value = todayLocalISO();
  $("#task-form").addEventListener("submit", submitTask);
  $("#filters").addEventListener("submit", (e) => e.preventDefault());
  $("#filter-status").addEventListener("change", loadTasks);
  $("#filter-plant").addEventListener("input", () => {
    clearTimeout(debounce);
    debounce = setTimeout(loadTasks, 300);
  });
  $("#clear-filters").addEventListener("click", clearFilters);
  $("#days-ahead").addEventListener("change", loadReminders);
  refreshAll();
  loadPlantOptions();
}

document.addEventListener("DOMContentLoaded", init);
