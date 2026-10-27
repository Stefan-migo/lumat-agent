import { useCallback, useEffect, useRef, useState } from "react";
import { Archive, ArrowDown, ArrowUp, Bell, BookOpen, Bot, CalendarDays, ClipboardList, CircleHelp, Clock3, Coins, Database, DoorOpen, Eye, Files, FileText, FolderOpen, FolderPlus, GitMerge, Globe, Globe2, Headset, History, Info, LayoutDashboard, Maximize2, MessageCircle, MessagesSquare, Paperclip, Pencil, Plus, Receipt, Search, ShieldAlert, ShieldCheck, SlidersHorizontal, SquarePen, Trash2, UserRound, Users, Wrench, Zap } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { ApiError, apiFetch, deleteModelApiKey, deleteSmtpPassword, fetchTechnicians, getAssistantCapabilities, postJson, saveEmailSettings, saveModelApiKey, saveSmtpPassword, type ModelApiKeyStatus } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { AssistantCapabilities, Settings as SettingsData, SmtpEmailSettings, UserRef } from "../../types";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Accordion } from "../primitives/Accordion";
import { Card } from "../primitives/Card";
import { HelpPanel } from "../primitives/HelpPanel";
import { Popover } from "../primitives/Popover";
import { Input } from "../primitives/Input";
import { Select } from "../primitives/Select";
import { Menu } from "../primitives/Menu";
import { SearchInput } from "../primitives/SearchInput";
import { Tabs } from "../primitives/Tabs";
import { Textarea } from "../primitives/Textarea";
import { Dialog } from "../primitives/Dialog";
import { MessagePreview } from "../primitives/MessagePreview";
import { DayToggle } from "../primitives/DayToggle";
import { StatCard } from "../shared/StatCard";
import { TechnicianScheduleEditor } from "../shared/TechnicianScheduleEditor";
import { WEEKDAY_NAMES } from "../shared/agendaTime";
import { PageFrame } from "../shared/PageFrame";
import { Markdown } from "../shared/Markdown";
import { StateMessage } from "../shared/StateMessage";
import { SettingsVersionHistory } from "../domain/SettingsVersionHistory";
import "./Settings.css";

export type SettingsState = AsyncDataState | "saved" | "saving" | "validation" | "server-error" | "stale";
export interface SettingsProps { data?: SettingsData | null; state?: SettingsState; onRetry?: () => void; capabilities?: AssistantCapabilities; }
const EMPTY_MESSAGES = { greeting: "", greeting_short: "", greeting_name: "", greeting_short_name: "", smalltalk: "", cannot_answer: "", clarification: "", cannot_understand_offer: "", kb_miss_offer: "", farewell: "", out_of_hours: "" };
const MONTHS_SHORT = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const MONTHS_FULL = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
type SettingsOptions = { tones: string[]; tarifa_labels: Partial<Record<keyof SettingsData["tarifa"], string>> };
// `options` is additive: a panel served against a backend that predates it must keep
// rendering, degrading to the current value and the raw service keys instead of crashing.
const EMPTY_OPTIONS: SettingsOptions = { tones: [], tarifa_labels: {} };
const settingsOptions = (data: SettingsData): SettingsOptions => (data as SettingsData & { options?: SettingsOptions }).options ?? EMPTY_OPTIONS;
const EMPTY_TARIFA: SettingsData["tarifa"] = {
  visita_tecnica: [], mantencion_calefont: [], mantencion_caldera: [], lavado_red: [],
};
function formatShortDate(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) return value;
  const [, year, month, day] = match;
  return `${Number(day)} ${MONTHS_SHORT[Number(month) - 1] ?? month} ${year}`;
}
const TIMEZONES = typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [];
const GROUPS = [
  { id: "chatbot", label: "Chatbot", sections: [
    { id: "agent", label: "Agente" }, { id: "persona", label: "Persona" }, { id: "conduct", label: "Conducta" }, { id: "messages", label: "Mensajes" },
  ] },
  { id: "operation", label: "Operación", sections: [
    { id: "schedule", label: "Horarios y avisos" }, { id: "coverage", label: "Cobertura" }, { id: "tarifa", label: "Tarifas" },
  ] },
  { id: "integrations", label: "Integraciones", sections: [
    { id: "capabilities", label: "Capacidades" }, { id: "model-api-key", label: "API key de modelos" }, { id: "email", label: "Correo" },
  ] },
  { id: "cost-group", label: "Costos", sections: [{ id: "costs", label: "Costos" }] },
];
const SECTIONS = GROUPS.flatMap(({ sections }) => sections);
const SECTION_META: Record<string, { title: string; description: string }> = {
  agent: { title: "Agente", description: "Define qué puede resolver y cómo actúa ante una emergencia." },
  persona: { title: "Persona", description: "Define quién es Max y cómo conversa con tus clientes." },
  conduct: { title: "Conducta", description: "Organiza los datos que solicita el bot y los mensajes de cada situación." },
  schedule: { title: "Horarios y avisos", description: "Configura la atención del equipo y la disponibilidad para visitas." },
};
const sectionGroup = (sectionId: string) => GROUPS.find(({ sections }) => sections.some(({ id }) => id === sectionId)) ?? GROUPS[0];
const MESSAGE_TEMPLATES = [
  { id: "greeting", label: "Saludo cuando falta el nombre", description: "Inicio de conversación; pregunta el nombre del cliente", icon: MessageCircle },
  { id: "greeting_name", label: "Saludo con nombre", description: "Inicio de conversación cuando el nombre ya está cargado", icon: MessageCircle },
  { id: "greeting_short", label: "Saludo corto cuando falta el nombre", description: "Cuando el cliente ya contó qué necesita; pregunta su nombre", icon: MessageCircle },
  { id: "greeting_short_name", label: "Saludo corto con nombre", description: "Cuando el cliente ya contó qué necesita y su nombre está cargado", icon: MessageCircle },
  { id: "smalltalk", label: "Cortesía", description: "Respuesta a agradecimientos y conversación social", icon: MessageCircle },
  { id: "cannot_answer", label: "Cuando no puede responder", description: "Derivación a un asesor", icon: Headset },
  { id: "clarification", label: "Aclaración", description: "Mensaje no entendido", icon: CircleHelp },
  { id: "cannot_understand_offer", label: "Oferta tras segundo fallo", description: "Ofrece coordinar una visita o hablar con una persona", icon: Headset },
  { id: "kb_miss_offer", label: "Oferta cuando falta un dato", description: "Ofrece coordinar una visita o hablar con una persona", icon: Headset },
  { id: "farewell", label: "Despedida", description: "Cierre de conversación", icon: DoorOpen },
  { id: "out_of_hours", label: "Fuera de horario", description: "Atención no disponible", icon: Clock3 },
] as const;
const DERIVACION_LABELS: Record<string, string> = {
  cobertura: "Comuna fuera de cobertura",
};
/**
 * S4: the five derivations whose wording the customer reads. Every other
 * reason (inyección, emergencia, límites de costo, KB) reuses the generic
 * "Derivación a un asesor" reply text, so the panel never offers copy nobody reviewed.
 */
const DERIVACION_CASES: Array<{ key: string; label: string; when: string }> = [
  {
    key: "handoff_cobertura",
    label: "Comuna sin cobertura",
    when: "Pide una visita en una comuna donde todavía no se atiende. Usa el dato de la comuna.",
  },
  {
    key: "handoff_persona",
    label: "Pide hablar con una persona",
    when: "Dice que quiere hablar con alguien del equipo.",
  },
  {
    key: "handoff_unknown_intent_thrice",
    label: "Tres mensajes sin entender",
    when: "Tres mensajes seguidos y no se logra entender qué necesita.",
  },
  {
    key: "handoff_campo_sin_respuesta",
    label: "Un dato no se logró tomar",
    when: "Se preguntó dos veces el mismo dato y el cliente no lo respondió.",
  },
  {
    key: "handoff_booking_unavailable",
    label: "No hay horarios para agendar",
    when: "Se intentó agendar la visita y no quedó ningún horario disponible.",
  },
];
const REPLY_TEXT_GROUPS: Array<{ title: string; keys: string[] }> = [
  { title: "Agendar", keys: ["booking_offer", "booking_no_more_today", "booking_unclear", "booking_confirmed"] },
  { title: "Gestionar una visita", keys: [
    "manage_no_visits", "manage_confirm_cancel", "manage_select", "manage_slots_offer",
    "manage_expired", "manage_appointment_unclear", "manage_slots_unclear", "manage_kept",
    "manage_reschedule_unavailable", "manage_rescheduled", "manage_cancel_prompt",
    "manage_cancel_unavailable", "manage_cancelled",
  ] },
  { title: "Derivar a una persona", keys: ["handoff"] },
  { title: "Captura", keys: ["capture_evidence", "capture_consent"] },
];
const REPLY_TEXT_KEYS = [...DERIVACION_CASES.map(({ key }) => key), ...REPLY_TEXT_GROUPS.flatMap(({ keys }) => keys)];
const REPLY_TEXT_LABELS: Record<string, string> = {
  booking_offer: "Oferta de horarios",
  booking_no_more_today: "Sin más horarios para ese día",
  booking_unclear: "No se entendió el horario pedido",
  booking_confirmed: "Visita agendada",
  manage_no_visits: "No tiene visitas",
  manage_confirm_cancel: "Confirmar la cancelación",
  manage_select: "Elegir una visita",
  manage_slots_offer: "Ofrecer nuevos horarios",
  manage_expired: "La visita ya pasó",
  manage_appointment_unclear: "No se entendió la visita",
  manage_slots_unclear: "No se entendió el horario",
  manage_kept: "La visita sigue igual",
  manage_reschedule_unavailable: "Sin horarios para reagendar",
  manage_rescheduled: "Visita reagendada",
  manage_cancel_prompt: "Pedir confirmación para cancelar",
  manage_cancel_unavailable: "No se puede cancelar",
  manage_cancelled: "Visita cancelada",
  handoff: "Derivación a un asesor",
  capture_evidence: "Pedir evidencia",
  capture_consent: "Pedir consentimiento",
};
type HoursData = SettingsData["hours"];
type Drafts = {
  scope: string; keywords: string; tone: string; messages: SettingsData["messages"]; templates: SettingsData["templates"]; hours: HoursData; tarifa: SettingsData["tarifa"]; coverage: string;
  conversationLimit: string; dailyLimit: string; metaCost: string; leadHours: string;
  persona: { orchestrator: string; orchestrator_brief: string };
  emergencyProtocol: { safety_instructions: string; contacts: string; notify_message: string };
  conduct: { orden: string[]; max_preguntas_por_mensaje: number; derivaciones: string[] };
  captureQuestions: Record<string, string>;
  replyTexts: Record<string, string>;
  serviceDurations: Array<{ name: string; minutes: string }>;
};
type DraftKey = keyof Drafts;
const GENERIC_NOTE = "Los cambios se aplican al guardar.";
const SCHEDULE_NOTE = "Completa los días y las horas para guardar.";

function draftsFrom(data?: SettingsData | null): Drafts {
  return {
    scope: data ? Object.entries(data.scope_rules).sort(([a], [b]) => a.localeCompare(b)).map(([category, mode]) => `${category}=${mode}`).join("\n") : "",
    keywords: data?.keywords.join("\n") ?? "", tone: data?.tone ?? "", messages: { ...EMPTY_MESSAGES, ...data?.messages },
    templates: data?.templates ?? [],
    hours: data?.hours ?? { timezone: "America/Santiago", schedule: [] },
    tarifa: data?.tarifa ?? EMPTY_TARIFA,
    coverage: (data?.coverage ?? []).join("\n"),
    conversationLimit: String(data?.conversation_limit ?? ""), dailyLimit: String(data?.daily_limit ?? ""), metaCost: String(data?.meta_cost ?? ""), leadHours: String(data?.booking?.lead_hours ?? 2),
    persona: { orchestrator: data?.persona?.orchestrator ?? "", orchestrator_brief: data?.persona?.orchestrator_brief ?? "" },
    emergencyProtocol: {
      safety_instructions: (data?.emergency?.safety_instructions ?? []).join("\n"),
      contacts: (data?.emergency?.contacts ?? []).join("\n"),
      notify_message: data?.emergency?.notify_message ?? "",
    },
    conduct: {
      orden: data?.conduct?.orden ?? [],
      max_preguntas_por_mensaje: data?.conduct?.max_preguntas_por_mensaje ?? 1,
      derivaciones: data?.conduct?.derivaciones ?? [],
    },
    captureQuestions: data?.capture_questions?.questions ?? {},
    replyTexts: data?.reply_texts?.texts ?? {},
    serviceDurations: Object.entries(data?.service_durations ?? {}).map(([name, minutes]) => ({ name, minutes: String(minutes) })),
  };
}

function isValidHours(hours: HoursData) {
  return hours.timezone.trim() !== "" && hours.schedule.length > 0 && hours.schedule.every((entry) =>
    entry.days.length > 0 && entry.open !== "" && entry.close !== "" && entry.open < entry.close);
}

function isTarifaValid(tarifa: SettingsData["tarifa"], labels: SettingsOptions["tarifa_labels"]) {
  return (Object.keys(labels) as Array<keyof SettingsData["tarifa"]>).every((service) => {
    const ranges = tarifa[service];
    return ranges.length > 0 && ranges.every((rango) =>
      Number.isInteger(rango.valor) && rango.valor > 0);
  });
}

function isValidNonNegative(value: string) {
  // Reference bounds are pending the owner's visual pass; accept any finite non-negative number.
  return value.trim() !== "" && Number.isFinite(Number(value)) && Number(value) >= 0;
}

function isValidPositive(value: string) {
  // S19: a spend limit of 0 reads as "no cap" and switches the cost gate off,
  // so the panel requires > 0 (the API rejects 0 too).
  return value.trim() !== "" && Number.isFinite(Number(value)) && Number(value) > 0;
}

function isDurationListValid(entries: Array<{ name: string; minutes: string }>) {
  const valid = entries.every(({ name, minutes }) => name.trim() !== ""
    && Number.isInteger(Number(minutes)) && Number(minutes) >= 1 && Number(minutes) <= 1440);
  const normalized = entries.map(({ name }) => name.trim().toLowerCase());
  return entries.length > 0 && valid && new Set(normalized).size === normalized.length;
}

function templateIdFromText(text: string) {
  const stopWords = new Set(["a", "al", "con", "de", "del", "el", "en", "la", "las", "los", "mes", "meses", "un", "una", "y", "tenemos", "tiene", "por", "para"]);
  const words = text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase().match(/[a-z0-9]+/g) ?? [];
  const meaningful = words.filter((word) => !stopWords.has(word) && !/^\d+$/.test(word));
  return meaningful.slice(0, 4).join("_") || "respuesta";
}

const SAMPLE_TEMPLATE_DATA: Record<string, string> = {
  nombre: "Ana", comuna: "Las Condes", direccion: "Av. Siempre Viva 123", equipo: "calefont",
  problema: "no enciende", disponibilidad: "martes por la mañana", visita: "martes a las 10:00",
};
function previewTemplate(text: string) {
  return text.replace(/{{\s*([^{}]+?)\s*}}/g, (_match, slot: string) => SAMPLE_TEMPLATE_DATA[slot] ?? "dato de ejemplo");
}
function templateSlots(text: string) {
  return [...new Set(Array.from(text.matchAll(/{{\s*([^{}]+?)\s*}}/g), (match) => match[1].trim()))];
}

function isScopeValid(value: string) {
  return value.split("\n").map((line) => line.trim()).filter(Boolean).every((line) => {
    const [category, mode, ...rest] = line.split("=").map((part) => part.trim());
    return Boolean(category) && rest.length === 0 && ["bot_resolve", "always_escalate"].includes(mode);
  });
}

function sameValue(left: unknown, right: unknown) {
  return typeof left === "object" && left !== null && typeof right === "object" && right !== null
    ? JSON.stringify(left) === JSON.stringify(right)
    : Object.is(left, right);
}

const SECTION_DRAFT_KEYS: Record<string, DraftKey[]> = {
  agent: ["scope", "keywords", "emergencyProtocol"], persona: ["persona"],
  conduct: ["conduct", "captureQuestions", "replyTexts"], messages: ["tone", "messages", "templates"],
  schedule: ["leadHours", "hours", "serviceDurations"], tarifa: ["tarifa"], coverage: ["coverage"],
  costs: ["conversationLimit", "dailyLimit", "metaCost"], capabilities: [], "model-api-key": [], email: [],
};

function stateMessage(state: SettingsState, errorDetail?: string | null) {
  if (state === "loading") return <StateMessage tone="info" role="status" spinner title="Cargando configuración" />;
  if (state === "denied") return <StateMessage tone="danger" role="alert" title="No tienes permiso para ver este panel" />;
  if (state === "error") return <StateMessage tone="danger" role="alert" title="No pudimos cargar la configuración" />;
  if (state === "saved") return <StateMessage tone="success" role="status" title="Configuración guardada" detail="Los cambios quedaron aplicados." />;
  if (state === "saving") return <StateMessage tone="info" role="status" spinner title="Guardando cambios" detail="Aplicando la configuración seleccionada." />;
  if (state === "validation") return <StateMessage tone="danger" role="alert" title="Sintaxis no válida" detail="Revisa las reglas avanzadas: cada línea debe tener categoría=mode con mode bot_resolve o always_escalate." />;
  if (state === "server-error") return <StateMessage tone="danger" role="alert" title="No pudimos guardar los cambios" detail={errorDetail || "Ocurrió un error del servidor. Reintenta en unos minutos."} />;
  if (state === "stale") return <StateMessage tone="warning" role="status" title="Datos posiblemente desactualizados" detail="La última consulta no pudo completarse. Mostramos la información disponible." />;
  return null;
}

function TarifaEditor({ tarifa, labels, onChange }: { tarifa: SettingsData["tarifa"]; labels: SettingsOptions["tarifa_labels"]; onChange: (tarifa: SettingsData["tarifa"]) => void }) {
  const setValor = (service: keyof SettingsData["tarifa"], index: number, valor: number) => {
    const ranges = tarifa[service].map((rango, current) => current === index ? { ...rango, valor } : rango);
    onChange({ ...tarifa, [service]: ranges });
  };

  return <div className="settings-tarifa">
    {(Object.entries(labels) as Array<[keyof SettingsData["tarifa"], string]>).map(([service, label]) => <fieldset className="settings-tarifa__service" key={service}>
      <legend>{label}</legend>
      <div className="settings-tarifa__ranges">
        {tarifa[service].map((rango, index) => {
          const periodo = rango.desde_mes === 1 && rango.hasta_mes === 12
            ? "todo el año"
            : `${MONTHS_FULL[rango.desde_mes - 1]} a ${MONTHS_FULL[rango.hasta_mes - 1]}`;
          return <Input
            key={`${rango.desde_mes}-${rango.hasta_mes}`}
            label={`${label} (${periodo})`}
            type="number"
            min={1}
            suffix="CLP"
            value={rango.valor === 0 ? "" : String(rango.valor)}
            onChange={(event) => setValor(service, index, Number(event.target.value))}
          />;
        })}
      </div>
    </fieldset>)}
  </div>;
}

function HoursEditor({ hours, onChange }: { hours: HoursData; onChange: (hours: HoursData) => void }) {
  const [newDays, setNewDays] = useState<string[]>([]);
  const [newOpen, setNewOpen] = useState("09:00");
  const [newClose, setNewClose] = useState("18:00");
  const usedDays = hours.schedule.flatMap((entry) => entry.days).map((day) => WEEKDAY_NAMES[day - 1]);
  const addSchedule = () => {
    const days = newDays.map((day) => WEEKDAY_NAMES.indexOf(day) + 1).filter((day) => day > 0 && !usedDays.includes(WEEKDAY_NAMES[day - 1]));
    if (!days.length || !newOpen || !newClose || newOpen >= newClose) return;
    onChange({ ...hours, schedule: [...hours.schedule, { days, open: newOpen, close: newClose }] });
    resetDraft();
  };
  const resetDraft = () => { setNewDays([]); setNewOpen("09:00"); setNewClose("18:00"); };
  const timezoneOptions = [...new Set([hours.timezone, ...TIMEZONES])].filter(Boolean).sort((left, right) => left.localeCompare(right));
  return <>
    <div className="settings-hours__timezone"><Globe2 aria-hidden="true" /><Select label="Zona horaria" value={hours.timezone} onChange={(event) => onChange({ ...hours, timezone: event.target.value })} options={timezoneOptions.map((timezone) => ({ value: timezone, label: timezone }))} /></div>
    <section className="settings-hours__weekly" aria-label="Horarios semanales"><h3>Horarios semanales</h3>
    {hours.schedule.length ? <div className="settings-hours__list" aria-label="Horarios configurados">{hours.schedule.map((entry, index) => <div className="settings-hours__item" key={index}>
      <strong>Horario {index + 1}</strong><span>{entry.days.map((day) => WEEKDAY_NAMES[day - 1]).join(", ") || "Sin días seleccionados"}</span><span>{entry.open} – {entry.close}</span>
      <Button variant="tertiary" aria-label={`Eliminar horario ${index + 1}`} onClick={() => onChange({ ...hours, schedule: hours.schedule.filter((_, currentIndex) => currentIndex !== index) })}><Trash2 aria-hidden="true" /> Eliminar</Button>
    </div>)}</div> : <p className="settings-hours__empty">No hay horarios guardados.</p>}</section>
    <div className="settings-hours__new"><div className="settings-hours__new-header"><h3>Nuevo horario</h3><Badge tone="neutral">Sin guardar</Badge><Button variant="tertiary" className="settings-hours__reset" aria-label="Restablecer nuevo horario" onClick={resetDraft}><Trash2 aria-hidden="true" /></Button></div>
      <span className="settings-hours__day-label">Días de atención</span><DayToggle label="Días de atención" value={newDays} onChange={(value) => setNewDays(value.filter((day) => !usedDays.includes(day)))} />
      <div className="settings-hours__times"><Input label="Inicio" type="time" value={newOpen} onChange={(event) => setNewOpen(event.target.value)} /><Input label="Fin" type="time" value={newClose} onChange={(event) => setNewClose(event.target.value)} /></div>
      <p className="settings-hours__info"><Info aria-hidden="true" />Cada día puede pertenecer a un solo horario.</p>
    </div><Button variant="tertiary" className="settings-hours__add" disabled={!newDays.some((day) => !usedDays.includes(day)) || !newOpen || !newClose || newOpen >= newClose} onClick={addSchedule}><Plus aria-hidden="true" />Agregar otro horario</Button>
  </>;
}

export function AssistantCapabilitiesView({ capabilities }: { capabilities: AssistantCapabilities }) {
  const [query, setQuery] = useState("");
  const [access, setAccess] = useState("all");
  const toolAccess = (tool: AssistantCapabilities["tools"][number]) => tool.write ? "write" : tool.read_only ? "read" : "limited";
  const filteredTools = capabilities.tools.filter((tool) => {
    const matchesAccess = access === "all" || toolAccess(tool) === access;
    const search = query.trim().toLocaleLowerCase();
    return matchesAccess && (!search || `${tool.name} ${tool.description}`.toLocaleLowerCase().includes(search));
  });
  const categories = [
    { id: "operacion", title: "Operación" },
    { id: "conocimiento", title: "Conocimiento y memoria" },
    { id: "web", title: "Web" },
    { id: "automatizaciones", title: "Automatizaciones y proyectos" },
    { id: "sistema", title: "Sistema" },
  ];
  const namespaceCategories: Record<string, string> = {
    appointments: "operacion", agenda: "operacion", cases: "operacion", customers: "operacion", conversations: "operacion", dashboard: "operacion",
    kb: "conocimiento", memory: "conocimiento", web: "web", automation: "automatizaciones", project: "automatizaciones", artifact: "automatizaciones",
    assistant: "sistema", system: "sistema",
  };
  const categoryFor = (name: string) => {
    if (name === "list_project_files" || name === "read_project_file") return "automatizaciones";
    const namespace = name.includes(".") ? name.split(".")[0] : "system";
    return namespaceCategories[namespace] ?? namespace;
  };
  const categoryTitles = Object.fromEntries(categories.map(({ id, title }) => [id, title]));
  const groupedTools = new Map<string, AssistantCapabilities["tools"]>();
  filteredTools.forEach((tool) => {
    const category = categoryFor(tool.name);
    groupedTools.set(category, [...(groupedTools.get(category) ?? []), tool]);
  });
  const groups = [...categories.map(({ id, title }) => ({ id, title, tools: groupedTools.get(id) ?? [] })).filter(({ tools }) => tools.length),
    ...[...groupedTools].filter(([id]) => !categories.some(({ id: known }) => id === known)).map(([id, tools]) => ({ id, title: categoryTitles[id] ?? id.charAt(0).toUpperCase() + id.slice(1), tools }))];
  const toolPresentation: Record<string, { label: string; icon: LucideIcon }> = {
    "assistant.capabilities": { label: "Capacidades del asistente", icon: Bot },
    "customers.search": { label: "Buscar clientes", icon: Search }, "customers.list": { label: "Listar clientes", icon: Users },
    "conversations.search": { label: "Buscar conversaciones", icon: Search }, "conversations.list": { label: "Listar conversaciones", icon: MessagesSquare },
    "appointments.upcoming": { label: "Próximas citas", icon: CalendarDays }, "customers.operational_history": { label: "Historial del cliente", icon: History },
    "cases.list": { label: "Listar casos", icon: ClipboardList }, "kb.retrieve": { label: "Consultar base de conocimientos", icon: BookOpen },
    "memory.read": { label: "Leer memoria", icon: FileText }, "memory.search": { label: "Buscar en memoria", icon: Search },
    "memory.write": { label: "Crear memoria", icon: Plus }, "memory.update": { label: "Actualizar memoria", icon: SquarePen },
    "memory.delete": { label: "Eliminar memoria", icon: Trash2 }, "dashboard.summary": { label: "Resumen del panel", icon: LayoutDashboard },
    "web.search": { label: "Buscar en la web", icon: Globe }, "web.fetch": { label: "Leer página web", icon: Globe },
    "automation.create_rule": { label: "Crear regla de automatización", icon: Zap }, "project.list": { label: "Listar proyectos", icon: FolderOpen },
    "project.find": { label: "Buscar proyecto", icon: Search }, "list_project_files": { label: "Listar archivos del proyecto", icon: Files },
    "read_project_file": { label: "Leer archivo del proyecto", icon: FileText }, "artifact.save": { label: "Guardar archivo", icon: Paperclip },
    "project.create": { label: "Crear proyecto", icon: FolderPlus }, "project.rename": { label: "Renombrar proyecto", icon: SquarePen },
    "project.archive": { label: "Archivar proyecto", icon: Archive }, "project.merge": { label: "Combinar proyectos", icon: GitMerge },
  };
  const accessOptions = [{ value: "all", label: "Todos los accesos" }, { value: "read", label: "Solo lectura" }, { value: "write", label: "Puede escribir" }, { value: "limited", label: "Acceso limitado" }];
  const availability = (available: boolean) => <span className={`settings-capabilities__availability${available ? " is-available" : ""}`}><span aria-hidden="true" />{available ? "Disponible" : "No disponible"}</span>;
  return <div className="settings-capabilities__layout">
    <Card title="Herramientas del asistente" description="Consulta las herramientas disponibles y su tipo de acceso." headerAction={<Badge tone="neutral">{capabilities.tools.length}</Badge>}>
      <div className="settings-capabilities__filters"><SearchInput aria-label="Buscar herramientas" placeholder="Buscar herramientas..." onSearch={setQuery} /><Select aria-label="Acceso" label="Acceso" value={access} onChange={(event) => setAccess(event.target.value)} options={accessOptions} /></div>
      <div className="settings-capabilities__groups">{groups.map(({ id, title, tools }) => <Accordion key={id} title={title} count={tools.length}>
        <ul className="settings-capabilities__tools">{tools.map((tool) => <li className="settings-capabilities__tool" key={tool.name}>
          {(() => { const presentation = toolPresentation[tool.name]; const ToolIcon = presentation?.icon ?? Wrench; const label = presentation?.label ?? (tool.name.split(".").at(-1) ?? tool.name).replaceAll("_", " ").replace(/^./, (letter) => letter.toLocaleUpperCase()); const kind = toolAccess(tool); const AccessIcon = kind === "write" ? Pencil : BookOpen; return <><ToolIcon aria-hidden="true" /><span className="settings-capabilities__tool-copy"><strong>{label}</strong><code>{tool.name}</code></span><Badge tone={kind === "write" ? "success" : "neutral"}>{kind !== "limited" ? <AccessIcon aria-hidden="true" /> : null}{kind === "write" ? "Puede escribir" : kind === "read" ? "Solo lectura" : "Acceso limitado"}</Badge></>; })()}
        </li>)}</ul>
      </Accordion>)}</div>
      {!filteredTools.length ? <p className="settings-capabilities__empty">No hay herramientas que coincidan con la búsqueda.</p> : null}
      <p className="settings__footer-note">{capabilities.tools.length} herramientas disponibles.</p>
    </Card>
    <Card title="Configuración activa" description="Información actual de la configuración del asistente." headerAction={<a className="settings-capabilities__consult" href="/panel/app/kb">Consultar</a>}>
      <div className="settings-capabilities__availability-list"><div className="settings-capabilities__availability-row"><BookOpen aria-hidden="true" /><span>Base de conocimientos</span>{availability(capabilities.kb_available)}</div>
      <div className="settings-capabilities__availability-row"><Database aria-hidden="true" /><span>Memoria</span>{availability(capabilities.memory_available)}</div></div>
      <section className="settings-capabilities__paths"><div className="settings-capabilities__path-section"><h3>Persona</h3><p>Archivo que define el comportamiento, objetivos y características del asistente.</p>{capabilities.personas.length ? capabilities.personas.map((path) => <code className="settings-capabilities__path" key={path}>{path}</code>) : <code className="settings-capabilities__path">Sin configurar</code>}</div>
      <div className="settings-capabilities__path-section"><h3>Prompts</h3><p>Archivos de prompts que utiliza el asistente.</p>{capabilities.prompts.length ? capabilities.prompts.map((path) => <code className="settings-capabilities__path" key={path}>{path}</code>) : <code className="settings-capabilities__path">Sin configurar</code>}</div></section>
      <p className="settings-capabilities__config-footer">Configuración técnica del asistente.</p>
    </Card>
  </div>;
}

function ConductOrderEditor({ order, options, onChange }: {
  order: string[];
  options: SettingsData["conduct"]["options"];
  onChange: (order: string[]) => void;
}) {
  const label = (value: string) => options.fields.find((field) => field.value === value)?.label ?? value;
  const move = (index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= order.length) return;
    const next = [...order];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };
  const remaining = options.fields.filter((field) => !order.includes(field.value));

  return <div className="settings-conduct__order">
    <ol className="settings-conduct__list">
      {order.map((field, index) => <li className="settings-conduct__item" key={field}>
        <span className="settings-conduct__label">{label(field)}</span>
        <div className="settings-conduct__actions">
          <Button variant="tertiary" aria-label={`Subir ${label(field)}`} disabled={index === 0} onClick={() => move(index, -1)}><ArrowUp aria-hidden="true" /></Button>
          <Button variant="tertiary" aria-label={`Bajar ${label(field)}`} disabled={index === order.length - 1} onClick={() => move(index, 1)}><ArrowDown aria-hidden="true" /></Button>
          <Button variant="tertiary" aria-label={`Quitar ${label(field)}`} disabled={order.length === 1} onClick={() => onChange(order.filter((each) => each !== field))}><Trash2 aria-hidden="true" /></Button>
        </div>
      </li>)}
    </ol>
    {remaining.length ? <div className="settings-conduct__add">
      <Menu label="Agregar campo" ariaLabel="Agregar campo" showChevron items={remaining.map((field) => ({ value: field.value, label: field.label }))} onSelect={(value) => onChange([...order, value])} />
    </div> : null}
  </div>;
}

export function Settings({ data: controlledData, state: controlledState, onRetry, capabilities: controlledCapabilities }: SettingsProps = {}) {
  const fetchSettings = useCallback(() => apiFetch<SettingsData>("/panel/api/settings"), []);
  const fetched = useAsyncData(fetchSettings, controlledData === undefined);
  const fetchCapabilities = useCallback(() => getAssistantCapabilities(), []);
  const fetchedCapabilities = useAsyncData(fetchCapabilities, controlledCapabilities === undefined);
  const data = controlledData ?? fetched.data;
  const capabilities = controlledCapabilities ?? fetchedCapabilities.data;
  const capabilityData = capabilities && Array.isArray(capabilities.tools) && Array.isArray(capabilities.personas) && Array.isArray(capabilities.prompts) ? capabilities : null;
  const pageState = controlledState ?? (controlledData !== undefined ? "ready" : fetched.state);
  const baseline = useRef(draftsFrom(data));
  const [draft, setDraft] = useState<Drafts>(() => draftsFrom(data));
  const [activeSection, setActiveSectionState] = useState(() => window.location.hash === "#schedule" ? "schedule" : "agent");
  const [activeGroup, setActiveGroup] = useState(() => sectionGroup(window.location.hash === "#schedule" ? "schedule" : "agent").id);
  const setActiveSection = (sectionId: string) => {
    setActiveSectionState(sectionId);
    setActiveGroup(sectionGroup(sectionId).id);
  };
  const selectGroup = (groupId: string) => {
    const group = GROUPS.find(({ id }) => id === groupId) ?? GROUPS[0];
    setActiveGroup(group.id);
    setActiveSectionState(group.sections.some(({ id }) => id === activeSection) ? activeSection : group.sections[0].id);
  };
  const [activeMessage, setActiveMessage] = useState<(typeof MESSAGE_TEMPLATES)[number]["id"]>("greeting");
  const [keywordEntry, setKeywordEntry] = useState("");
  const [scopeDisclosureOpen, setScopeDisclosureOpen] = useState(false);
  const [personaMode, setPersonaMode] = useState<"preview" | "edit">("preview");
  const [personaDialogOpen, setPersonaDialogOpen] = useState(false);
  const [pending, setPending] = useState<Partial<Record<DraftKey, boolean>>>({});
  const [saveState, setSaveState] = useState<SettingsState | null>(null);
  const [personaVersion, setPersonaVersion] = useState(0);
  const [emergencyVersion, setEmergencyVersion] = useState(0);
  const [saveErrorDetail, setSaveErrorDetail] = useState<string | null>(null);
  const [modelApiKeyStatus, setModelApiKeyStatus] = useState<ModelApiKeyStatus | undefined>(data?.model_api_key);
  const [modelApiKey, setModelApiKey] = useState("");
  const [modelApiKeyBusy, setModelApiKeyBusy] = useState(false);
  const [modelApiKeyFeedback, setModelApiKeyFeedback] = useState("");
  const [emailDraft, setEmailDraft] = useState<Omit<SmtpEmailSettings, "password">>({ host: "", port: 25, from_address: "", user: "", tls: "none" });
  const [emailPasswordStatus, setEmailPasswordStatus] = useState<SmtpEmailSettings["password"] | undefined>(data?.email?.password);
  const [emailPassword, setEmailPassword] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailFeedback, setEmailFeedback] = useState("");
  const [manualTemplateIds, setManualTemplateIds] = useState<number[]>([]);
  const [technicians, setTechnicians] = useState<UserRef[]>([]);
  const [techniciansState, setTechniciansState] = useState<"idle" | "loading" | "ready" | "error">("idle");

  useEffect(() => { if (data?.model_api_key) setModelApiKeyStatus(data.model_api_key); }, [data?.model_api_key]);

  useEffect(() => {
    if (activeSection !== "schedule" || techniciansState !== "idle") return;
    setTechniciansState("loading");
    void fetchTechnicians().then(({ technicians: loaded }) => {
      setTechnicians(Array.isArray(loaded) ? loaded : []);
      setTechniciansState("ready");
    }).catch(() => setTechniciansState("error"));
  }, [activeSection, techniciansState]);

  useEffect(() => {
    if (!data?.email) return;
    const { password, ...connection } = data.email;
    setEmailDraft(connection);
    setEmailPasswordStatus(password);
  }, [data?.email]);

  const saveModelKey = async () => {
    setModelApiKeyBusy(true); setModelApiKeyFeedback("");
    try {
      const result = await saveModelApiKey(modelApiKey);
      setModelApiKeyStatus(result.model_api_key);
      setModelApiKey("");
      setModelApiKeyFeedback(result.validation === "valid" ? "Clave validada." : "Clave válida, pero la cuenta no tiene saldo.");
    } catch (error) {
      setModelApiKeyFeedback(error instanceof ApiError && error.status === 400 ? "Clave inválida." : error instanceof ApiError && error.status === 502 ? "No se pudo validar la clave." : "No se pudo guardar la clave.");
    } finally { setModelApiKeyBusy(false); }
  };

  const deleteModelKey = async () => {
    setModelApiKeyBusy(true); setModelApiKeyFeedback("");
    try {
      const result = await deleteModelApiKey();
      setModelApiKeyStatus(result.model_api_key);
      setModelApiKeyFeedback("Clave eliminada del panel.");
    } catch (error) {
      setModelApiKeyFeedback(error instanceof Error ? error.message : "No se pudo borrar la clave.");
    } finally { setModelApiKeyBusy(false); }
  };

  const modelApiKeyOrigin = modelApiKeyStatus?.source === "env" ? "Configurada en el servidor (variable de entorno)"
    : modelApiKeyStatus?.source === "panel" ? "Configurada desde el panel" : "No configurada";

  const emailPasswordOrigin = emailPasswordStatus?.configured ? "Contraseña guardada en el panel" : "Sin contraseña guardada";
  const port = Number(emailDraft.port);
  const emailValid = emailDraft.host.trim() !== "" && emailDraft.from_address.trim() !== "" && Number.isInteger(port) && port >= 1 && port <= 65535;

  const saveEmail = async () => {
    setEmailBusy(true); setEmailFeedback("");
    try {
      const result = await saveEmailSettings({ ...emailDraft, host: emailDraft.host.trim(), from_address: emailDraft.from_address.trim(), user: emailDraft.user.trim() });
      setEmailPasswordStatus(result.email.password);
      setEmailFeedback("Configuración de correo guardada.");
    } catch {
      setEmailFeedback("No se pudo guardar la configuración.");
    } finally { setEmailBusy(false); }
  };

  const saveSmtpPasswordHandler = async () => {
    setEmailBusy(true); setEmailFeedback("");
    try {
      const result = await saveSmtpPassword(emailPassword);
      setEmailPasswordStatus(result.email.password);
      setEmailPassword("");
      setEmailFeedback("Contraseña guardada.");
    } catch {
      setEmailFeedback("No se pudo guardar la contraseña.");
    } finally { setEmailBusy(false); }
  };

  const deleteSmtpPasswordHandler = async () => {
    setEmailBusy(true); setEmailFeedback("");
    try {
      const result = await deleteSmtpPassword();
      setEmailPasswordStatus(result.email.password);
      setEmailFeedback("Contraseña eliminada del panel.");
    } catch {
      setEmailFeedback("No se pudo borrar la contraseña.");
    } finally { setEmailBusy(false); }
  };

  useEffect(() => {
    if (!data) return;
    const next = draftsFrom(data);
    const previous = baseline.current;
    setDraft((current) => {
      const merged = { ...current };
      (Object.keys(next) as DraftKey[]).forEach((key) => {
        if (sameValue(current[key], previous[key])) (merged as Drafts)[key] = next[key] as never;
      });
      return merged;
    });
    baseline.current = next;
  }, [data]);

  const update = <K extends DraftKey>(key: K, value: Drafts[K]) => setDraft((current) => ({ ...current, [key]: value }));
  const save = async (key: DraftKey, path: string, body: unknown, savedValue: Drafts[DraftKey]) => {
    setPending((current) => ({ ...current, [key]: true }));
    setSaveState("saving"); setSaveErrorDetail(null);
    try {
      await postJson(path, body);
      baseline.current = { ...baseline.current, [key]: savedValue };
      if (key === "conversationLimit") baseline.current.dailyLimit = draft.dailyLimit;
      setDraft((current) => {
        const next = sameValue(current[key], savedValue) ? { ...current, [key]: savedValue } : current;
        return key === "conversationLimit" && sameValue(current.dailyLimit, draft.dailyLimit) ? { ...next, dailyLimit: draft.dailyLimit } : next;
      });
      setSaveState("saved");
    } catch (error) {
      setSaveErrorDetail(error instanceof Error ? error.message : null); setSaveState("server-error");
    } finally { setPending((current) => ({ ...current, [key]: false })); }
  };
  const saveScope = async () => {
    if (!isScopeValid(draft.scope)) { setSaveState("validation"); return; }
    const rules: Record<string, string> = {};
    for (const line of draft.scope.split("\n").map((value) => value.trim()).filter(Boolean)) {
      const [category, mode] = line.split("=").map((value) => value.trim());
      rules[category] = mode;
    }
    await save("scope", "/panel/api/settings/scope", { rules }, draft.scope);
  };
  const savePersona = async () => {
    if (!draft.persona.orchestrator.trim() || !draft.persona.orchestrator_brief.trim()) { setSaveState("validation"); return; }
    await save("persona", "/panel/api/settings/persona", draft.persona, draft.persona);
    setPersonaVersion((current) => current + 1);
  };
  const saveEmergencyProtocol = async () => {
    const instructions = draft.emergencyProtocol.safety_instructions.split("\n").map((value) => value.trim()).filter(Boolean);
    const contacts = draft.emergencyProtocol.contacts.split("\n").map((value) => value.trim()).filter(Boolean);
    const notify = draft.emergencyProtocol.notify_message.trim();
    if (!instructions.length || !contacts.length || !notify) { setSaveState("validation"); return; }
    const saved = { safety_instructions: instructions.join("\n"), contacts: contacts.join("\n"), notify_message: notify };
    await save("emergencyProtocol", "/panel/api/settings/emergency", { safety_instructions: instructions, contacts, notify_message: notify }, saved);
    setEmergencyVersion((current) => current + 1);
  };
  const saveConduct = async () => {
    if (!draft.conduct.orden.length || !draft.conduct.derivaciones.length) { setSaveState("validation"); return; }
    await save("conduct", "/panel/api/settings/conduct", { conduct: draft.conduct }, draft.conduct);
    // The capture-question form is keyed by the order this save may have changed.
    retry();
  };
  const saveCaptureQuestions = async () => {
    const values = Object.values(draft.captureQuestions);
    if (!values.length || values.some((value) => !value.trim()) || values.some((value) => value.includes("{{") || value.includes("}}"))) { setSaveState("validation"); return; }
    await save("captureQuestions", "/panel/api/settings/capture-questions", { questions: draft.captureQuestions }, draft.captureQuestions);
  };
  const replyTextsValid = REPLY_TEXT_KEYS.every((key) => Boolean(draft.replyTexts[key]?.trim()));
  const saveReplyTexts = async () => {
    if (!replyTextsValid) { setSaveState("validation"); return; }
    await save("replyTexts", "/panel/api/settings/reply-texts", { texts: draft.replyTexts }, draft.replyTexts);
  };
  const saveLeadHours = async () => {
    const hours = Number(draft.leadHours);
    if (!Number.isInteger(hours) || hours < 1 || hours > 48) { setSaveState("validation"); return; }
    await save("leadHours", "/panel/api/settings/booking-lead", { hours }, draft.leadHours);
  };
  const saveDurations = async () => {
    if (!isDurationListValid(draft.serviceDurations)) { setSaveState("validation"); return; }
    const map: Record<string, number> = {};
    for (const { name, minutes } of draft.serviceDurations) map[name.trim()] = Number(minutes);
    await save("serviceDurations", "/panel/api/settings/durations", { service_durations: map }, draft.serviceDurations);
  };
  const sectionKeys = SECTION_DRAFT_KEYS[activeSection] ?? [];
  const pendingDraftKeys = sectionKeys.filter((key) => !sameValue(draft[key], baseline.current[key]));
  const hasPendingChanges = pendingDraftKeys.length > 0;
  const savePendingChanges = async () => {
    const valid = pendingDraftKeys.every((key) => {
      if (key === "scope") return isScopeValid(draft.scope);
      if (key === "persona") return Boolean(draft.persona.orchestrator.trim() && draft.persona.orchestrator_brief.trim());
      if (key === "emergencyProtocol") return Boolean(draft.emergencyProtocol.safety_instructions.trim() && draft.emergencyProtocol.contacts.trim() && draft.emergencyProtocol.notify_message.trim());
      if (key === "conduct") return Boolean(draft.conduct.orden.length && draft.conduct.derivaciones.length);
      if (key === "captureQuestions") return Boolean(Object.values(draft.captureQuestions).length && Object.values(draft.captureQuestions).every((value) => value.trim() && !value.includes("{{") && !value.includes("}}")));
      if (key === "replyTexts") return replyTextsValid;
      if (key === "leadHours") return Number.isInteger(Number(draft.leadHours)) && Number(draft.leadHours) >= 1 && Number(draft.leadHours) <= 48;
      if (key === "hours") return isValidHours(draft.hours);
      if (key === "serviceDurations") return isDurationListValid(draft.serviceDurations);
      if (key === "tarifa") return isTarifaValid(draft.tarifa, settingsOptions(data! as SettingsData).tarifa_labels);
      if (key === "conversationLimit" || key === "dailyLimit") return numericLimitsValid;
      if (key === "metaCost") return isValidNonNegative(draft.metaCost);
      if (key === "tone") return Boolean(draft.tone.trim());
      if (key === "messages") return Object.values(draft.messages).every((value) => value.trim());
      if (key === "templates") return draft.templates.every(({ id, text }) => id.trim() && text.trim());
      return true;
    });
    if (!valid) { setSaveState("validation"); return; }
    // The two spend limits share one endpoint, so either dirty key saves both once.
    let limitsSaved = false;
    for (const key of pendingDraftKeys) {
      if (key === "scope") await saveScope();
      else if (key === "keywords") await save("keywords", "/panel/api/settings/keywords", { keywords: draft.keywords.split("\n").map((value) => value.trim()).filter(Boolean) }, draft.keywords);
      else if (key === "persona") await savePersona();
      else if (key === "emergencyProtocol") await saveEmergencyProtocol();
      else if (key === "conduct") await saveConduct();
      else if (key === "captureQuestions") await saveCaptureQuestions();
      else if (key === "replyTexts") await saveReplyTexts();
      else if (key === "tone") await save("tone", "/panel/api/settings/tone", { tone: draft.tone }, draft.tone);
      else if (key === "messages") await save("messages", "/panel/api/settings/messages", draft.messages, draft.messages);
      else if (key === "templates") await save("templates", "/panel/api/settings/message-templates", { templates: draft.templates }, draft.templates);
      else if (key === "leadHours") await saveLeadHours();
      else if (key === "hours") await save("hours", "/panel/api/settings/hours", draft.hours, draft.hours);
      else if (key === "serviceDurations") await saveDurations();
      else if (key === "tarifa") await save("tarifa", "/panel/api/settings/tarifa", { precios: draft.tarifa }, draft.tarifa);
      else if (key === "coverage") await save("coverage", "/panel/api/settings/coverage", { communes: draft.coverage.split("\n").map((value) => value.trim()).filter(Boolean) }, draft.coverage);
      else if (key === "conversationLimit" || key === "dailyLimit") {
        if (limitsSaved) continue;
        limitsSaved = true;
        await save("conversationLimit", "/panel/api/settings/limits", { conversation_limit: Number(draft.conversationLimit), daily_limit: Number(draft.dailyLimit) }, draft.conversationLimit);
      }
      else if (key === "metaCost") await save("metaCost", "/panel/api/settings/meta", { service_message_cost: Number(draft.metaCost) }, draft.metaCost);
    }
  };
  const discardPendingChanges = () => setDraft((current) => {
    const next = { ...current };
    pendingDraftKeys.forEach((key) => { (next as Drafts)[key] = baseline.current[key] as never; });
    return next;
  });
  const addKeyword = () => {
    const phrase = keywordEntry.trim();
    if (!phrase) return;
    const keywords = draft.keywords.split("\n").map((value) => value.trim()).filter(Boolean);
    if (!keywords.includes(phrase)) update("keywords", [...keywords, phrase].join("\n"));
    setKeywordEntry("");
  };
  const snapshot = data?.snapshot;
  const state = saveState ?? pageState;
  const retry = onRetry ?? fetched.retry;
  const capabilityState = controlledCapabilities ? "ready" : fetchedCapabilities.state;
  const capabilityHost = capabilityState === "loading" ? <Card title="Capacidades del asistente"><StateMessage tone="info" role="status" spinner title="Cargando capacidades del asistente" /></Card>
    : capabilityState === "error" || capabilityState === "denied" ? <Card title="Capacidades del asistente"><StateMessage tone="danger" role="alert" title="No pudimos cargar las capacidades del asistente" /></Card>
      : capabilityData ? <AssistantCapabilitiesView capabilities={capabilityData} /> : null;
  const footer = (note = GENERIC_NOTE) => <p className="settings__footer-note">{note}</p>;
  const saving = (key: DraftKey) => Boolean(pending[key]);
  const numericLimitsValid = isValidPositive(draft.conversationLimit) && isValidPositive(draft.dailyLimit);
  if (!data || state === "loading" || state === "error" || state === "denied") return <PageFrame title="Configuración" meta="Preferencias globales del asistente" state={stateMessage(state)}>{null}</PageFrame>;
  return <PageFrame title="Configuración" meta="Preferencias globales del asistente" className="settings-page" actions={activeSection === "agent" ? <SettingsVersionHistory scope="emergency" triggerLabel="Historial" refreshToken={emergencyVersion} onRestored={retry} /> : activeSection === "persona" ? <SettingsVersionHistory scope="persona" triggerLabel="Historial" refreshToken={personaVersion} onRestored={retry} /> : undefined} state={stateMessage(state, saveErrorDetail)}>
    <div className="settings-tabs">
      <div className="settings-tabs__select">
        <Menu label={GROUPS.find(({ id }) => id === activeGroup)?.label ?? "Chatbot"} ariaLabel="Grupo de configuración" showChevron items={GROUPS.map(({ id, label }) => ({ value: id, label }))} onSelect={selectGroup} />
        <Menu label={SECTIONS.find(({ id }) => id === activeSection)?.label ?? "Agente"} ariaLabel="Sección de configuración" showChevron items={sectionGroup(activeSection).sections.map(({ id, label }) => ({ value: id, label }))} onSelect={setActiveSection} />
      </div>
    <Tabs ariaLabel="Super-secciones de configuración" tabs={GROUPS} activeTab={activeGroup} onTabChange={selectGroup}>
      {() => <Tabs layout="vertical" ariaLabel="Secciones de configuración" tabs={sectionGroup(activeSection).sections} activeTab={activeSection} onTabChange={setActiveSection}>
      {(active) => <div className="settings-tabs__content">
        {SECTION_META[active] ? <header className="settings-section-head"><h2>{SECTION_META[active].title}</h2><p>{SECTION_META[active].description}</p></header> : null}
        {active === "agent" ? <>
          <div className="settings-agent__row">
            <Card className="settings-agent__card" title="Alcance del agente" description="Define en qué categorías el agente responde de forma automática y en cuáles siempre deriva a una persona." icon={Bot} headerAction={<><Badge tone="neutral">Avanzado</Badge><Popover title="Cómo funciona" triggerLabel="Ayuda: Alcance del agente" trigger="?"><HelpPanel icon={CircleHelp} title="Cómo funciona"><p>El agente responde de forma automática en las categorías configuradas y deriva a una persona cuando la regla lo indica.</p><p>Usa una categoría por línea. Conserva las reglas actuales si no estás seguro del efecto de un cambio.</p></HelpPanel></Popover></>}>
              {draft.scope.trim() ? <ul className="settings-agent__rules">{draft.scope.split("\n").map((line) => line.trim()).filter(Boolean).map((line) => { const [category, mode] = line.split("=").map((part) => part.trim()); return <li key={line}><span>{category}</span><Badge tone={mode === "always_escalate" ? "warning" : "neutral"}>{mode}</Badge></li>; })}</ul> : <div className="settings-agent__empty"><strong>No hay reglas personalizadas</strong><p>Agrega categorías o revisa la configuración avanzada.</p><Button variant="secondary" onClick={() => setScopeDisclosureOpen(true)}>+ Agregar regla</Button></div>}
              <details open={scopeDisclosureOpen} onToggle={(event) => setScopeDisclosureOpen(event.currentTarget.open)}><summary>Configuración avanzada<span className="visually-hidden"> Sintaxis avanzada</span></summary><div className="settings-agent__advanced"><Textarea label="Reglas de alcance" rows={4} placeholder="Ej: reparación=bot_resolve" value={draft.scope} onChange={(event) => update("scope", event.target.value)} /><p>Escribe una categoría y un modo en cada línea, separados por un signo igual. <code>bot_resolve</code> significa que el agente responde por su cuenta; <code>always_escalate</code> significa que deriva la conversación a una persona. Por ejemplo: <code>presupuesto=bot_resolve</code>.</p></div></details>
            </Card>
          </div>
          <div className="settings-agent__row">
            <Card className="settings-agent__card" title="Detección de emergencias" description="Palabras que activan un aviso de emergencia. Se detectan en el próximo mensaje entrante." icon={ShieldAlert} headerAction={<Popover title="Consideraciones" triggerLabel="Ayuda: Detección de emergencias" trigger="?"><HelpPanel icon={ShieldAlert} title="Consideraciones"><p>Las palabras clave se revisan en cada mensaje entrante y activan el aviso correspondiente.</p><p>Incluye términos claros y evita agregar palabras ambiguas que puedan generar avisos innecesarios.</p></HelpPanel></Popover>}>
              <div className="settings-agent__keywords">
                <ul className="settings-agent__chips" aria-label="Frases de emergencia">{draft.keywords.split("\n").map((value) => value.trim()).filter(Boolean).map((phrase, index) => <li key={`${phrase}-${index}`}><span>{phrase}</span><Button variant="tertiary" aria-label={`Quitar palabra clave ${phrase}`} onClick={() => update("keywords", draft.keywords.split("\n").map((item) => item.trim()).filter((item) => item && item !== phrase).join("\n"))}>×</Button></li>)}</ul>
                <div className="settings-agent__keyword-add"><Input label="Escribe una frase y presiona Enter" value={keywordEntry} onChange={(event) => setKeywordEntry(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addKeyword(); } }} /><Button variant="secondary" onClick={addKeyword}>Agregar</Button></div>
                <p className="settings-agent__helper">Usa expresiones claras para evitar activaciones innecesarias.</p>
                <p className="settings-agent__info"><Info aria-hidden="true" />La detección se evalúa antes de generar la respuesta.</p>
              </div>
            </Card>
          </div>
          <div className="settings-agent__row">
            <Card className="settings-agent__card" title="Protocolo de emergencia" description="Lo que Max responde cuando detecta riesgo. La detección de la emergencia no depende de este texto: se revisa antes, en cada mensaje." icon={FileText} headerAction={data.emergency?.customized ? <Badge tone="success">Personalizado</Badge> : <Badge tone="neutral">Original</Badge>}>
              <div className="settings-agent__form settings-agent__protocol">
                <div><Textarea label="Instrucciones de seguridad" rows={6} value={draft.emergencyProtocol.safety_instructions} onChange={(event) => update("emergencyProtocol", { ...draft.emergencyProtocol, safety_instructions: event.target.value })} /><p className="settings-agent__helper">Una instrucción por línea.</p></div>
                <div><Textarea label="Contactos de emergencia" rows={4} value={draft.emergencyProtocol.contacts} onChange={(event) => update("emergencyProtocol", { ...draft.emergencyProtocol, contacts: event.target.value })} /><p className="settings-agent__helper">Un contacto por línea.</p></div>
                <div className="settings-agent__protocol-message"><Textarea label="Mensaje al notificar" rows={3} value={draft.emergencyProtocol.notify_message} onChange={(event) => update("emergencyProtocol", { ...draft.emergencyProtocol, notify_message: event.target.value })} /><p className="settings-agent__helper">Se envía cuando se notifica al equipo.</p></div>
              </div>
            </Card>
          </div>
        </> : null}
        {active === "persona" ? <>
          <Card title="Persona del asistente" description="Estas instrucciones se aplican en el siguiente mensaje." icon={UserRound} headerAction={<div className="settings-persona__header-actions">{data.persona?.customized ? <Badge tone="success">Personalizada</Badge> : <Badge tone="neutral">Original</Badge>}<Button variant="tertiary" onClick={() => setPersonaDialogOpen(true)}><Maximize2 aria-hidden="true" />Ampliar</Button></div>}>
            <div className="settings-persona__content">
              <div className="settings-persona__toolbar">
                <div className="settings-persona__segments" role="group" aria-label="Modo de edición de la persona">
                  <Button variant={personaMode === "preview" ? "secondary" : "tertiary"} aria-pressed={personaMode === "preview"} onClick={() => setPersonaMode("preview")}><Eye aria-hidden="true" />Vista previa</Button>
                  <Button variant={personaMode === "edit" ? "secondary" : "tertiary"} aria-pressed={personaMode === "edit"} onClick={() => setPersonaMode("edit")}><Pencil aria-hidden="true" />Editar Markdown</Button>
                </div>
              </div>
              {personaMode === "preview" ? <div className="settings-persona__preview" role="region" aria-label="Vista previa del documento Markdown"><Markdown content={draft.persona.orchestrator} /></div>
                : <Textarea label="Texto de la persona" rows={18} value={draft.persona.orchestrator} onChange={(event) => update("persona", { ...draft.persona, orchestrator: event.target.value })} />}
              <p className="settings-persona__info"><Info aria-hidden="true" />Los datos del cliente se agregan automáticamente. No incluyas variables como <code>{"{{nombre}}"}</code>.</p>
            </div>
          </Card>
          <Card title="Instrucción de brevedad" description="Se utiliza cuando queda poco presupuesto de conversación." icon={FileText}>
            <Textarea label="Instrucción de brevedad" rows={4} value={draft.persona.orchestrator_brief} onChange={(event) => update("persona", { ...draft.persona, orchestrator_brief: event.target.value })} />
          </Card>
          <div className="settings-persona__dialog">
            <Dialog open={personaDialogOpen} onClose={() => setPersonaDialogOpen(false)} title="Vista previa de la persona" size="wide" closeLabel="Cerrar vista ampliada">
              <div className="settings-persona__dialog-preview"><Markdown content={draft.persona.orchestrator} /></div>
            </Dialog>
          </div>
        </> : null}
        {active === "conduct" ? <>
          <Card title="Conducta de la conversación" description="Qué datos pide el bot, en qué orden y cuándo deriva a una persona." icon={SlidersHorizontal} headerAction={data.conduct?.customized ? <Badge tone="success">Personalizada</Badge> : <Badge tone="neutral">Original</Badge>}>
            <h3 className="settings-conduct__title">Orden de captura</h3>
            <p className="settings-agent__helper">Un campo que quitas no se vuelve a preguntar. El nombre, el correo y la dirección van siempre después de la disponibilidad.</p>
            <ConductOrderEditor order={draft.conduct.orden} options={data.conduct.options} onChange={(orden) => update("conduct", { ...draft.conduct, orden })} />
            <div className="settings-conduct__row">
              <span className="settings-conduct__row-label">Preguntas por mensaje</span>
              <Menu label={String(draft.conduct.max_preguntas_por_mensaje)} ariaLabel="Preguntas por mensaje" showChevron items={data.conduct.options.max_preguntas_por_mensaje.map((value) => ({ value: String(value), label: value === 1 ? "Una pregunta" : `${value} preguntas` }))} onSelect={(value) => update("conduct", { ...draft.conduct, max_preguntas_por_mensaje: Number(value) })} />
            </div>
            <fieldset className="settings-conduct__derivaciones">
              <legend>Derivar a una persona cuando</legend>
              {data.conduct.options.derivaciones.map((rule) => <label className="settings-conduct__check" key={rule}>
                <input type="checkbox" checked={draft.conduct.derivaciones.includes(rule)} onChange={(event) => update("conduct", {
                  ...draft.conduct,
                  derivaciones: event.target.checked ? [...draft.conduct.derivaciones, rule] : draft.conduct.derivaciones.filter((each) => each !== rule),
                })} />
                <span>{DERIVACION_LABELS[rule] ?? rule}</span>
              </label>)}
            </fieldset>
            <p className="settings-agent__helper">Solo se muestran las reglas que el bot ya aplica. Si apagas la cobertura, una comuna fuera de la lista queda sin salida a un asesor.</p>
            <div className="settings-agent__footer">{footer("Los cambios se aplican al siguiente mensaje.")}<Button disabled={saving("conduct") || !draft.conduct.orden.length} onClick={() => void saveConduct()}>Guardar conducta</Button></div>
          </Card>
          <Card title="Preguntas de captura" description="El texto exacto que recibe el cliente para cada dato. Se envía tal cual: sin llaves.">
            <p className="settings-agent__helper">El orden lo define la tarjeta de arriba. Guarda el orden antes de editar los textos.</p>
            {Object.entries(draft.captureQuestions).map(([field, text]) => <Textarea key={field} label={data.conduct.options.fields.find((each) => each.value === field)?.label ?? field} rows={2} value={text} onChange={(event) => update("captureQuestions", { ...draft.captureQuestions, [field]: event.target.value })} />)}
            <div className="settings-agent__footer">{footer("El cliente recibe este texto literal.")}<Button disabled={saving("captureQuestions") || Object.values(draft.captureQuestions).some((value) => !value.trim() || value.includes("{{") || value.includes("}}"))} onClick={() => void saveCaptureQuestions()}>Guardar preguntas</Button></div>
          </Card>
          <Card title="Derivaciones" description="Todos los textos deterministas que recibe el cliente en las derivaciones, agenda, visitas y captura.">
            <p className="settings-agent__helper">Cualquier otro motivo de derivación responde con el texto genérico de <strong>Derivar a una persona</strong>. Los cinco casos específicos se muestran primero.</p>
            <div className="settings-messages__reply-group">
              {DERIVACION_CASES.map(({ key, label, when }) => {
                const slots = data.reply_texts?.slots?.[key] ?? [];
                return <div className="settings-messages__reply" key={key}>
                  <Textarea label={label} rows={3} value={draft.replyTexts[key] ?? ""} onChange={(event) => update("replyTexts", { ...draft.replyTexts, [key]: event.target.value })} />
                  <p className="settings-agent__helper">{when}{slots.length ? <> Datos: <code>{slots.map((slot) => `{{${slot}}}`).join(", ")}</code></> : null}</p>
                </div>;
              })}
            </div>
            {REPLY_TEXT_GROUPS.map((group) => <Accordion key={group.title} title={group.title} count={group.keys.length}>
              <div className="settings-messages__reply-group">
                {group.keys.map((key) => {
                  const slots = data.reply_texts?.slots?.[key] ?? [];
                  return <div className="settings-messages__reply" key={key}>
                    <Textarea label={REPLY_TEXT_LABELS[key] ?? key} rows={3} value={draft.replyTexts[key] ?? ""} onChange={(event) => update("replyTexts", { ...draft.replyTexts, [key]: event.target.value })} />
                    {slots.length ? <p className="settings-agent__helper">Datos: <code>{slots.map((slot) => `{{${slot}}}`).join(", ")}</code></p> : <p className="settings-agent__helper">Sin datos variables.</p>}
                  </div>;
                })}
              </div>
            </Accordion>)}
            <div className="settings-agent__footer">{footer("El cliente recibe este texto tal cual.")}{footer()}<Button disabled={saving("replyTexts") || !replyTextsValid} onClick={() => void saveReplyTexts()}>Guardar respuestas</Button></div>
          </Card>
        </> : null}
        {active === "messages" ? <>
          <Card title="Tono del asistente" description="Define cómo suenan las respuestas en cada conversación." className="settings-messages__tone" headerAction={<div className="settings-messages__tone-row"><Menu label={draft.tone ? draft.tone[0].toUpperCase() + draft.tone.slice(1) : "Selecciona un tono"} ariaLabel="Tono" showChevron items={(settingsOptions(data).tones.length ? settingsOptions(data).tones : [draft.tone]).filter(Boolean).map((tone) => ({ value: tone, label: tone[0].toUpperCase() + tone.slice(1) }))} onSelect={(value) => update("tone", value)} /><Button disabled={saving("tone") || !draft.tone.trim()} onClick={() => void save("tone", "/panel/api/settings/tone", { tone: draft.tone }, draft.tone)}>Guardar tono</Button></div>} >{null}</Card>
           <Card title="Mensajes del asistente" className="settings-messages__editor">
              <div className="settings-messages__panel">
                <div className="settings-messages__layout">
                  <div className="settings-messages__mobile-selector">
                    <label>Plantilla</label>
                    <Menu label={MESSAGE_TEMPLATES.find(({ id }) => id === activeMessage)?.label ?? MESSAGE_TEMPLATES[0].label} ariaLabel="Plantilla" showChevron items={MESSAGE_TEMPLATES.map(({ id, label }) => ({ value: id, label }))} onSelect={(id) => setActiveMessage(id as typeof activeMessage)} />
                    <p>{MESSAGE_TEMPLATES.find(({ id }) => id === activeMessage)?.description}</p>
                  </div>
                <Tabs layout="vertical" ariaLabel="Plantillas de mensajes" tabs={[...MESSAGE_TEMPLATES]} activeTab={activeMessage} onTabChange={(id) => setActiveMessage(id as typeof activeMessage)}>
                {(selected) => {
                  const template = MESSAGE_TEMPLATES.find(({ id }) => id === selected) ?? MESSAGE_TEMPLATES[0];
                  return <div className="settings-messages__edit">
                    <h3>{template.label}</h3>
                    <Textarea label="Texto del mensaje" rows={5} value={draft.messages[template.id]} onChange={(event) => update("messages", { ...draft.messages, [template.id]: event.target.value })} />
                    <p className="settings-messages__info"><Info aria-hidden="true" />Este mensaje se usa como respuesta automática para esta situación.</p>
                  </div>;
                }}
                </Tabs>
                <div className="settings-messages__preview"><h3>Vista previa</h3><MessagePreview message={draft.messages[activeMessage]} note="Menú de categorías automático" avatarSrc="/panel/app/brand/lumat-mark.png" /></div>
                </div>
              </div>
              <div className="settings-messages__footer">{footer()}<Button disabled={saving("messages") || Object.values(draft.messages).some((value) => !value.trim())} onClick={() => void save("messages", "/panel/api/settings/messages", draft.messages, draft.messages)}>Guardar mensajes</Button></div>
           </Card>
           <Card title="Respuestas prediseñadas" description="Plantillas que el bot elige solo según lo que pregunta el cliente. Se envían con los datos reales ya cargados (nombre, comuna, equipo o la visita agendada).">
             <p className="settings-messages__info">A diferencia de los Mensajes del asistente de arriba —que son fijos y se disparan solos en momentos puntuales (saludo, derivación, fuera de horario)— estas respuestas las selecciona el bot en cada conversación.</p>
             <p className="settings-messages__helper" role="note">Si a la conversación le falta uno de esos datos, el bot omite esta respuesta y responde normalmente.</p>
             <div className="settings-messages__templates" aria-label="Respuestas prediseñadas">
               {draft.templates.map((template, index) => {
                 const slots = templateSlots(template.text);
                 const editingId = manualTemplateIds.includes(index);
                 return <div className="settings-messages__template" key={index}>
                   <div className="settings-messages__template-id">
                     <Input label={`ID de respuesta ${index + 1}`} value={template.id} readOnly={!editingId} onChange={(event) => update("templates", draft.templates.map((item, current) => current === index ? { ...item, id: event.target.value } : item))} />
                     <Button variant="tertiary" aria-label={`Regenerar ID de respuesta ${index + 1}`} onClick={() => { update("templates", draft.templates.map((item, current) => current === index ? { ...item, id: templateIdFromText(item.text) } : item)); setManualTemplateIds((ids) => ids.filter((entry) => entry !== index)); }}>Regenerar</Button>
                     <Button variant="tertiary" aria-label={`Editar id de respuesta ${index + 1}`} onClick={() => setManualTemplateIds((ids) => ids.includes(index) ? ids : [...ids, index])}>Editar id</Button>
                   </div>
                   <p className="settings-messages__helper">El cliente nunca ve este ID.</p>
                   <Textarea label={`Texto de respuesta ${index + 1}`} rows={3} value={template.text} onChange={(event) => update("templates", draft.templates.map((item, current) => current === index ? { ...item, text: event.target.value, ...(!editingId ? { id: templateIdFromText(event.target.value) } : {}) } : item))} />
                   <p className="settings-messages__helper">{slots.length ? <>Datos disponibles: {slots.map((slot, slotIndex) => <code key={slot}>{slotIndex ? ", " : ""}{"{{"}{slot}{"}}"}</code>)}</> : "Sin datos variables."}</p>
                   <div className="settings-messages__preview"><h3>Vista previa de la respuesta {index + 1}</h3><MessagePreview message={previewTemplate(template.text)} note="Vista previa con datos de ejemplo" avatarSrc="/panel/app/brand/lumat-mark.png" /></div>
                   <Button variant="tertiary" aria-label={`Eliminar respuesta ${index + 1}`} onClick={() => { update("templates", draft.templates.filter((_, current) => current !== index)); setManualTemplateIds((ids) => ids.filter((entry) => entry !== index).map((entry) => entry > index ? entry - 1 : entry)); }}><Trash2 aria-hidden="true" /></Button>
                 </div>;
               })}
             </div>
             <div className="settings-messages__footer">
               <Button variant="tertiary" onClick={() => update("templates", [...draft.templates, { id: "", text: "" }])}><Plus aria-hidden="true" />Agregar respuesta</Button>
               <Button disabled={saving("templates") || draft.templates.some(({ id, text }) => !id.trim() || !text.trim())} onClick={() => void save("templates", "/panel/api/settings/message-templates", { templates: draft.templates }, draft.templates)}>Guardar respuestas</Button>
             </div>
           </Card>
        </> : null}
        {active === "schedule" ? <>
        <div className="settings-hours__layout">
          <Card title="Anticipación mínima" description="Tiempo mínimo entre ahora y la primera hora que se puede ofrecer para una visita.">
            <Input label="Anticipación mínima" type="number" min={1} max={48} suffix="horas" value={draft.leadHours} onChange={(event) => update("leadHours", event.target.value)} />
            <div className="settings-hours__footer"><Button variant="secondary" disabled={saving("leadHours") || !Number.isInteger(Number(draft.leadHours)) || Number(draft.leadHours) < 1 || Number(draft.leadHours) > 48} onClick={() => void saveLeadHours()}>Guardar anticipación</Button>{footer("Entre 1 y 48 horas.")}</div>
          </Card>
          <Card title="Horarios de atención" description="Define los días y las horas en que atiende tu equipo."><HoursEditor hours={draft.hours} onChange={(value) => update("hours", value)} /><div className="settings-hours__footer"><Button variant="secondary" disabled={saving("hours") || !isValidHours(draft.hours)} onClick={() => void save("hours", "/panel/api/settings/hours", draft.hours, draft.hours)}>Guardar horarios</Button>{footer(SCHEDULE_NOTE)}</div></Card>
          <div className="settings-hours__aside"><Card title="Notificaciones push" icon={Bell}><p>Configura los avisos del navegador para este dispositivo.</p><a href="/panel/app/push">Configurar notificaciones push →</a></Card><Card title="Fuera de horario" icon={Clock3}><p>{draft.messages.out_of_hours || "Configura el mensaje que recibirán las personas fuera del horario de atención."}</p><Button variant="tertiary" className="settings-hours__edit-message" onClick={() => { setActiveSection("messages"); setActiveMessage("out_of_hours"); }}>Editar mensaje →</Button></Card></div>
        </div>
          <Card title="Horarios de técnicos" description="Define cuándo puede recibir visitas cada técnico.">
            {techniciansState === "loading" ? <StateMessage tone="info" role="status" spinner title="Cargando técnicos" /> : null}
            {techniciansState === "error" ? <div><StateMessage tone="danger" role="alert" title="No pudimos cargar los técnicos" detail="Intenta nuevamente más tarde." /><Button variant="secondary" onClick={() => setTechniciansState("idle")}>Reintentar</Button></div> : null}
            {techniciansState === "ready" && technicians.length === 0 ? <p>No hay técnicos disponibles.</p> : null}
            {techniciansState === "ready" ? technicians.map((technician) => <section key={technician.id} className="settings-hours__technician"><h3>{technician.username}</h3><TechnicianScheduleEditor technician={technician} onSaved={() => undefined} /></section>) : null}
          </Card>
          <Card title="Duraciones por servicio" description="Cuánto ocupa cada servicio en la agenda. El nombre debe coincidir con el servicio que se conversa.">
            <div className="settings-conduct__durations">
              {draft.serviceDurations.map((entry, index) => <div className="settings-conduct__duration" key={index}>
                <Input label={`Servicio ${index + 1}`} value={entry.name} onChange={(event) => update("serviceDurations", draft.serviceDurations.map((item, current) => current === index ? { ...item, name: event.target.value } : item))} />
                <Input label={`Minutos ${index + 1}`} inputMode="numeric" value={entry.minutes} onChange={(event) => update("serviceDurations", draft.serviceDurations.map((item, current) => current === index ? { ...item, minutes: event.target.value } : item))} />
                <Button variant="tertiary" aria-label={`Eliminar servicio ${index + 1}`} onClick={() => update("serviceDurations", draft.serviceDurations.filter((_, current) => current !== index))}><Trash2 aria-hidden="true" /></Button>
              </div>)}
            </div>
            <div className="settings-agent__footer">
              <Button variant="tertiary" onClick={() => update("serviceDurations", [...draft.serviceDurations, { name: "", minutes: "60" }])}><Plus aria-hidden="true" />Agregar servicio</Button>
              <Button disabled={saving("serviceDurations") || !isDurationListValid(draft.serviceDurations)} onClick={() => void saveDurations()}>Guardar duraciones</Button>
            </div>
            {footer("Entre 1 y 1440 minutos por servicio, sin nombres repetidos.")}
          </Card>
        </> : null}
        {active === "tarifa" ? <>
          <Card title="Tarifario" description="Precios que el asistente informa según la fecha. Solo se menciona el precio vigente; las temporadas nunca se nombran al cliente." icon={Coins}>
            <div className="settings-agent__layout">
              <div className="settings-agent__form">
                <TarifaEditor tarifa={draft.tarifa} labels={settingsOptions(data).tarifa_labels} onChange={(value) => update("tarifa", value)} />
                <div className="settings-agent__footer">{footer("El asistente solo informa el precio que corresponde a la fecha de hoy.")}<Button disabled={saving("tarifa") || !isTarifaValid(draft.tarifa, settingsOptions(data).tarifa_labels)} onClick={() => void save("tarifa", "/panel/api/settings/tarifa", { precios: draft.tarifa }, draft.tarifa)}>Guardar tarifas</Button></div>
              </div>
              <HelpPanel icon={Coins} title="Cómo se aplica"><p>El asistente resuelve el precio con la fecha de hoy en la zona horaria configurada y solo recibe los precios vigentes.</p><p>Si un precio no está configurado, el asistente no inventa una cifra: deriva la consulta a un asesor.</p></HelpPanel>
            </div>
          </Card>
        </> : null}
          {active === "coverage" ? <>
          <Card title="Cobertura" description="Comunas donde se agenda una visita. Fuera de esta lista el asistente no rechaza el trabajo: coordina con un asesor." icon={Globe}>
            <div className="settings-agent__layout">
              <div className="settings-agent__form">
                <Textarea label="Comunas con cobertura" rows={8} value={draft.coverage} onChange={(event) => update("coverage", event.target.value)} />
                <p className="settings-agent__helper">Una comuna por línea. Se comparan sin tildes y sin distinguir mayúsculas.</p>
                <div className="settings-agent__footer">{footer()}<Button disabled={saving("coverage") || !draft.coverage.split("\n").some((value) => value.trim())} onClick={() => void save("coverage", "/panel/api/settings/coverage", { communes: draft.coverage.split("\n").map((value) => value.trim()).filter(Boolean) }, draft.coverage)}>Guardar cobertura</Button></div>
              </div>
              <HelpPanel icon={Globe} title="Cómo se aplica"><p>El asistente reconoce la comuna aunque el cliente la escriba sin tildes o en minúsculas.</p><p>Una comuna fuera de la lista se coordina con un asesor; nunca se rechaza el trabajo.</p></HelpPanel>
            </div>
          </Card>
        </> : null}
        {active === "costs" ? <div className="settings-costs">
            <Card title="Gasto actual" description="Resumen del consumo en el periodo actual." headerAction={snapshot ? <Badge tone="neutral"><CalendarDays aria-hidden="true" />{formatShortDate(snapshot.date)}</Badge> : undefined}>
              {snapshot ? <StatCard metrics={[
                { label: "Gasto diario", value: `USD ${snapshot.daily_spend.toFixed(4)}`, context: snapshot.conversation_percent !== null ? `Conversación: ${snapshot.conversation_percent}% de USD ${snapshot.conversation_limit.toFixed(2)}` : undefined },
                { label: "Límite diario", value: `USD ${snapshot.daily_limit.toFixed(2)}` },
                { label: "Del límite utilizado", value: `${snapshot.daily_percent.toFixed(1)}%` },
              ]} /> : null}
            </Card>
            <div className="settings-costs__pair">
              <Card title="Límites de gasto" icon={Coins} description="Controla el gasto por conversación y por día.">
                <div className="settings-costs__limits">
                  <Input label="Límite por conversación" type="number" suffix="USD" value={draft.conversationLimit} onChange={(event) => update("conversationLimit", event.target.value)} />
                  <Input label="Límite diario" type="number" suffix="USD" value={draft.dailyLimit} onChange={(event) => update("dailyLimit", event.target.value)} />
                </div>
                <div className="settings-costs__footer"><Button variant="primary" disabled={saving("conversationLimit") || saving("dailyLimit") || !numericLimitsValid} onClick={() => void save("conversationLimit", "/panel/api/settings/limits", { conversation_limit: Number(draft.conversationLimit), daily_limit: Number(draft.dailyLimit) }, draft.conversationLimit)}>Guardar límites</Button>{footer()}</div>
              </Card>
              <Card title="Precio Meta" icon={Receipt} description="Costo por mensaje de servicio." headerAction={<Badge tone="neutral"><CalendarDays aria-hidden="true" />Vigente desde el 1 oct 2026</Badge>}>
                <Input label="Costo por mensaje" type="number" suffix="USD" value={draft.metaCost} onChange={(event) => update("metaCost", event.target.value)} />
                <div className="settings-costs__footer"><Button variant="primary" disabled={saving("metaCost") || !isValidNonNegative(draft.metaCost)} onClick={() => void save("metaCost", "/panel/api/settings/meta", { service_message_cost: Number(draft.metaCost) }, draft.metaCost)}>Guardar precio</Button>{footer()}</div>
              </Card>
            </div>
            <Card title="Qué ocurre al alcanzar los límites" icon={Info} description="Así responde el sistema cuando se llega a ciertos niveles de uso.">
              <div className="settings-costs__thresholds">
                <div className="settings-costs__threshold">
                  <span className="settings-costs__threshold-icon"><ShieldCheck aria-hidden="true" /></span>
                  <div className="settings-costs__threshold-copy"><strong>80% · Respuestas más conservadoras</strong><span>El agente se vuelve más conservador.</span></div>
                </div>
                <div className="settings-costs__threshold">
                  <span className="settings-costs__threshold-icon"><UserRound aria-hidden="true" /></span>
                  <div className="settings-costs__threshold-copy"><strong>100% · Derivación a una persona</strong><span>Se detienen todas las llamadas de pago y la conversación pasa a una persona.</span></div>
                </div>
              </div>
            </Card>
          </div> : null}
        {active === "capabilities" ? capabilityHost : null}
        {active === "model-api-key" ? <Card title="API key de modelos" description="Configura la clave de DeepSeek para las llamadas al modelo.">
          <div className="settings-model-key">
            <p className="settings-model-key__origin">{modelApiKeyOrigin}</p>
            {modelApiKeyStatus?.configured ? <code className="settings-model-key__masked">{modelApiKeyStatus.masked}</code> : null}
            <Input label="API key de DeepSeek" type="password" autoComplete="new-password" value={modelApiKey} onChange={(event) => setModelApiKey(event.target.value)} />
            <div className="settings-model-key__actions">
              <Button disabled={modelApiKeyBusy || !modelApiKey.trim()} onClick={() => void saveModelKey()}>Guardar</Button>
              <Button variant="danger" disabled={modelApiKeyBusy || modelApiKeyStatus?.source !== "panel"} onClick={() => void deleteModelKey()}>Borrar</Button>
            </div>
            {modelApiKeyFeedback ? <p className="settings-model-key__feedback" role="status">{modelApiKeyFeedback}</p> : null}
          </div>
        </Card> : null}
        {active === "email" ? <Card title="Correo" description="Configura el servidor SMTP que usa el sistema para enviar correos.">
          <div className="settings-email">
            <p className="settings-email__origin">{emailPasswordOrigin}</p>
            {emailPasswordStatus?.configured ? <code className="settings-email__masked">{emailPasswordStatus.masked}</code> : null}
            <Input label="Servidor SMTP" value={emailDraft.host} onChange={(event) => setEmailDraft({ ...emailDraft, host: event.target.value })} />
            <Input label="Puerto" inputMode="numeric" value={emailDraft.port} onChange={(event) => setEmailDraft({ ...emailDraft, port: Number(event.target.value.replace(/\D/g, "")) })} />
            <Input label="Remitente" value={emailDraft.from_address} onChange={(event) => setEmailDraft({ ...emailDraft, from_address: event.target.value })} />
            <Input label="Usuario" value={emailDraft.user} onChange={(event) => setEmailDraft({ ...emailDraft, user: event.target.value })} />
            <Select label="Seguridad" value={emailDraft.tls} onChange={(event) => setEmailDraft({ ...emailDraft, tls: event.target.value as SmtpEmailSettings["tls"] })} options={[{ value: "none", label: "Sin cifrado" }, { value: "starttls", label: "STARTTLS (587)" }, { value: "ssl", label: "SSL (465)" }]} />
            <div className="settings-email__actions">
              <Button disabled={emailBusy || !emailValid} onClick={() => void saveEmail()}>Guardar correo</Button>
            </div>
            <Input label="Contraseña SMTP" type="password" autoComplete="new-password" value={emailPassword} onChange={(event) => setEmailPassword(event.target.value)} />
            <div className="settings-email__actions">
              <Button disabled={emailBusy || emailPassword === ""} onClick={() => void saveSmtpPasswordHandler()}>Guardar contraseña</Button>
              <Button variant="danger" disabled={emailBusy || !emailPasswordStatus?.configured} onClick={() => void deleteSmtpPasswordHandler()}>Borrar contraseña</Button>
            </div>
            {emailFeedback ? <p className="settings-email__feedback" role="status">{emailFeedback}</p> : null}
          </div>
        </Card> : null}
      </div>}
    </Tabs>}
    </Tabs>
    </div>
    <div className={`settings-save-bar${hasPendingChanges ? " is-dirty" : ""}`} role="group" aria-label="Estado y acciones de guardado">
      <span className="settings-save-bar__state">{hasPendingChanges ? <><span aria-hidden="true">●</span>Cambios sin guardar</> : <><span aria-hidden="true">✓</span>Sin cambios pendientes</>}</span>
      <div className="settings-save-bar__actions"><Button variant="secondary" disabled={!hasPendingChanges} onClick={discardPendingChanges}>Descartar</Button><Button disabled={!hasPendingChanges || pendingDraftKeys.some((key) => saving(key)) || state === "saving"} onClick={() => void savePendingChanges()}>Guardar cambios</Button></div>
    </div>
    {state === "empty" ? <Button onClick={retry}>Reintentar</Button> : null}
  </PageFrame>;
}
