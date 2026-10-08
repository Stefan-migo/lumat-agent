import { useCallback, useEffect, useRef, useState } from "react";
import { CircleHelp, ShieldAlert, SlidersHorizontal } from "lucide-react";
import { apiFetch, getAssistantCapabilities, postJson } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { AssistantCapabilities, Settings as SettingsData } from "../../types";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Card } from "../primitives/Card";
import { HelpPanel } from "../primitives/HelpPanel";
import { Input } from "../primitives/Input";
import { Select } from "../primitives/Select";
import { Tabs } from "../primitives/Tabs";
import { Textarea } from "../primitives/Textarea";
import { DataTable, tabularNum, type Column } from "../shared/DataTable";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { PushSettings } from "./PushSettings";
import "./Settings.css";

export type SettingsState = AsyncDataState | "saved" | "saving" | "validation" | "server-error" | "stale";
export interface SettingsProps { data?: SettingsData | null; state?: SettingsState; onRetry?: () => void; capabilities?: AssistantCapabilities; }
const EMPTY_MESSAGES = { greeting: "", cannot_answer: "", clarification: "", farewell: "", out_of_hours: "" };
const DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const SECTIONS = [
  { id: "agent", label: "Agente" }, { id: "messages", label: "Mensajes" },
  { id: "schedule", label: "Horarios y avisos" }, { id: "costs", label: "Costos" },
  { id: "capabilities", label: "Capacidades" },
];
type HoursData = SettingsData["hours"];
type Drafts = {
  scope: string; keywords: string; tone: string; messages: SettingsData["messages"]; hours: HoursData;
  conversationLimit: string; dailyLimit: string; metaCost: string;
};
type DraftKey = keyof Drafts;
const GENERIC_NOTE = "Los cambios se aplican al guardar.";
const SCHEDULE_NOTE = "Completa los días y las horas para guardar.";

function draftsFrom(data?: SettingsData | null): Drafts {
  return {
    scope: data ? Object.entries(data.scope_rules).sort(([a], [b]) => a.localeCompare(b)).map(([category, mode]) => `${category}=${mode}`).join("\n") : "",
    keywords: data?.keywords.join("\n") ?? "", tone: data?.tone ?? "", messages: data?.messages ?? EMPTY_MESSAGES,
    hours: data?.hours ?? { timezone: "America/Santiago", schedule: [] },
    conversationLimit: String(data?.conversation_limit ?? ""), dailyLimit: String(data?.daily_limit ?? ""), metaCost: String(data?.meta_cost ?? ""),
  };
}

function isValidHours(hours: HoursData) {
  return hours.timezone.trim() !== "" && hours.schedule.length > 0 && hours.schedule.every((entry) =>
    entry.days.length > 0 && entry.open !== "" && entry.close !== "" && entry.open < entry.close);
}

function isValidNonNegative(value: string) {
  // Reference bounds are pending the owner's visual pass; accept any finite non-negative number.
  return value.trim() !== "" && Number.isFinite(Number(value)) && Number(value) >= 0;
}

function sameValue(left: unknown, right: unknown) {
  return typeof left === "object" && left !== null && typeof right === "object" && right !== null
    ? JSON.stringify(left) === JSON.stringify(right)
    : Object.is(left, right);
}

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

function HoursEditor({ hours, onChange }: { hours: HoursData; onChange: (hours: HoursData) => void }) {
  const updateEntry = (index: number, entry: HoursData["schedule"][number]) => onChange({ ...hours, schedule: hours.schedule.map((current, currentIndex) => currentIndex === index ? entry : current) });
  const usedByOtherEntry = (index: number, day: number) => hours.schedule.some((entry, entryIndex) => entryIndex !== index && entry.days.includes(day));
  return <>
    <Input label="Zona horaria" value={hours.timezone} onChange={(event) => onChange({ ...hours, timezone: event.target.value })} />
    <p>Define los días y el horario de atención. Cada día puede pertenecer a un solo horario.</p>
    {hours.schedule.map((entry, index) => <div key={index}>
      <strong>Horario {index + 1}</strong><div>{DAYS.map((day, dayIndex) => {
        const weekday = dayIndex + 1;
        return <label key={day}><input type="checkbox" aria-label={`${day}, entrada ${index + 1}`} checked={entry.days.includes(weekday)} disabled={!entry.days.includes(weekday) && usedByOtherEntry(index, weekday)} onChange={() => updateEntry(index, { ...entry, days: entry.days.includes(weekday) ? entry.days.filter((value) => value !== weekday) : [...entry.days, weekday].sort((a, b) => a - b) })} /> {day}</label>;
      })}</div>
      <Input label={`Apertura ${index + 1}`} type="time" value={entry.open} onChange={(event) => updateEntry(index, { ...entry, open: event.target.value })} />
      <Input label={`Cierre ${index + 1}`} type="time" value={entry.close} onChange={(event) => updateEntry(index, { ...entry, close: event.target.value })} />
      <Button variant="tertiary" onClick={() => onChange({ ...hours, schedule: hours.schedule.filter((_, currentIndex) => currentIndex !== index) })}>Eliminar horario</Button>
    </div>)}
    <Button variant="tertiary" onClick={() => onChange({ ...hours, schedule: [...hours.schedule, { days: [], open: "09:00", close: "18:00" }] })}>Agregar horario</Button>
  </>;
}

export function AssistantCapabilitiesView({ capabilities }: { capabilities: AssistantCapabilities }) {
  return <Card title="Capacidades del asistente"><h3>Herramientas</h3><ul>{capabilities.tools.map((tool) => <li key={tool.name}><strong>{tool.name}</strong>: {tool.description}{" "}<Badge tone={tool.read_only ? "neutral" : "warning"}>{tool.read_only ? "Solo lectura" : "Puede escribir"}</Badge></li>)}</ul><h3>Configuración activa</h3><p>Personas: {capabilities.personas.join(", ")}</p><p>Prompts: {capabilities.prompts.join(", ")}</p><p>{capabilities.kb_available ? "KB disponible" : "KB no disponible"} · {capabilities.memory_available ? "Memoria disponible" : "Memoria no disponible"}</p></Card>;
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
  const [activeSection, setActiveSection] = useState("agent");
  const [pending, setPending] = useState<Partial<Record<DraftKey, boolean>>>({});
  const [saveState, setSaveState] = useState<SettingsState | null>(null);
  const [saveErrorDetail, setSaveErrorDetail] = useState<string | null>(null);

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
  const saveScope = () => {
    const rules: Record<string, string> = {};
    for (const line of draft.scope.split("\n").map((value) => value.trim()).filter(Boolean)) {
      const [category, mode] = line.split("=").map((value) => value.trim());
      if (!category || !["bot_resolve", "always_escalate"].includes(mode)) { setSaveState("validation"); return; }
      rules[category] = mode;
    }
    void save("scope", "/panel/api/settings/scope", { rules }, draft.scope);
  };
  const snapshot = data?.snapshot;
  const columns: Column<{ label: string; value: string }>[] = [
    { key: "label", header: "Fecha", render: (row) => row.label },
    { key: "daily_spend", header: "Gasto diario", render: (row) => tabularNum(row.value), align: "right" },
  ];
  const spendRows = snapshot ? [{ label: snapshot.date, value: `$${snapshot.daily_spend.toFixed(4)}` }, { label: "Límite diario", value: `$${snapshot.daily_limit.toFixed(2)}` }, { label: "% del límite", value: `${snapshot.daily_percent.toFixed(1)}%` }] : [];
  const state = saveState ?? pageState;
  const retry = onRetry ?? fetched.retry;
  const capabilityState = controlledCapabilities ? "ready" : fetchedCapabilities.state;
  const capabilityHost = capabilityState === "loading" ? <Card title="Capacidades del asistente"><StateMessage tone="info" role="status" spinner title="Cargando capacidades del asistente" /></Card>
    : capabilityState === "error" || capabilityState === "denied" ? <Card title="Capacidades del asistente"><StateMessage tone="danger" role="alert" title="No pudimos cargar las capacidades del asistente" /></Card>
      : capabilityData ? <AssistantCapabilitiesView capabilities={capabilityData} /> : null;
  const footer = (note = GENERIC_NOTE) => <p className="settings__footer-note">{note}</p>;
  const saving = (key: DraftKey) => Boolean(pending[key]);
  const numericLimitsValid = isValidNonNegative(draft.conversationLimit) && isValidNonNegative(draft.dailyLimit);
  if (!data || state === "loading" || state === "error" || state === "denied") return <PageFrame title="Configuración" meta="Preferencias globales del asistente" state={stateMessage(state)}>{null}</PageFrame>;
  return <PageFrame title="Configuración" meta="Preferencias globales del asistente" state={stateMessage(state, saveErrorDetail)}>
    <div className="settings-tabs">
    <div className="settings-tabs__select"><Select label="Sección" value={activeSection} onChange={(event) => setActiveSection(event.target.value)} options={SECTIONS.map(({ id, label }) => ({ value: id, label }))} /></div>
    <Tabs ariaLabel="Secciones de configuración" tabs={SECTIONS} activeTab={activeSection} onTabChange={setActiveSection}>
      {(active) => <div className="settings-tabs__content">
        {active === "agent" ? <>
          <div className="settings-agent__row">
            <Card title="Alcance del agente" icon={SlidersHorizontal} headerAction={<Badge tone="neutral">Avanzado</Badge>}>
              <p>Define en qué categorías el agente responde de forma automática y en cuáles siempre deriva a una persona.</p>
              <Textarea label="Reglas de alcance" rows={4} value={draft.scope} onChange={(event) => update("scope", event.target.value)} />
              <details><summary>Sintaxis avanzada · categoría=mode</summary><p>Formato técnico: una regla por línea con categoría=mode, donde mode es bot_resolve o always_escalate. No lo cambies sin conocer el efecto en las respuestas.</p></details>
              <div className="settings-agent__footer">{footer()}<Button variant="secondary" disabled={saving("scope") || !draft.scope.trim() || !draft.scope.split("\n").map((line) => line.trim()).filter(Boolean).every((line) => { const [category, mode] = line.split("=").map((value) => value.trim()); return Boolean(category) && ["bot_resolve", "always_escalate"].includes(mode); })} onClick={saveScope}>Guardar alcance</Button></div>
            </Card>
            <HelpPanel icon={CircleHelp} title="Cómo funciona"><p>El agente responde de forma automática en las categorías configuradas y deriva a una persona cuando la regla lo indica.</p><p>Usa una categoría por línea. Conserva las reglas actuales si no estás seguro del efecto de un cambio.</p></HelpPanel>
          </div>
          <div className="settings-agent__row">
            <Card title="Detección de emergencias" icon={ShieldAlert}>
              <p>Palabras que activan un aviso de emergencia. Se detectan en el próximo mensaje entrante.</p>
              <Textarea label="Palabras clave de emergencia" rows={6} value={draft.keywords} onChange={(event) => update("keywords", event.target.value)} />
              <p className="settings-agent__helper">Escribe una palabra o frase por línea.</p>
              <div className="settings-agent__footer">{footer()}<Button variant="secondary" disabled={saving("keywords") || !draft.keywords.split("\n").some((value) => value.trim())} onClick={() => void save("keywords", "/panel/api/settings/keywords", { keywords: draft.keywords.split("\n").map((value) => value.trim()).filter(Boolean) }, draft.keywords)}>Guardar palabras clave</Button></div>
            </Card>
            <HelpPanel icon={ShieldAlert} title="Consideraciones" tone="info"><p>Las palabras clave se revisan en cada mensaje entrante y activan el aviso correspondiente.</p><p>Incluye términos claros y evita agregar palabras ambiguas que puedan generar avisos innecesarios.</p></HelpPanel>
          </div>
        </> : null}
        {active === "messages" ? <>
          <Card title="Tono del asistente"><p>Define cómo suenan las respuestas del agente en cada conversación.</p><Select label="Tono" value={draft.tone} onChange={(event) => update("tone", event.target.value)} options={[{ value: "", label: "Selecciona un tono" }, { value: "cercano", label: "Cercano" }, { value: "formal", label: "Formal" }, { value: "directo", label: "Directo" }]} /><Button variant="secondary" disabled={saving("tone") || !draft.tone.trim()} onClick={() => void save("tone", "/panel/api/settings/tone", { tone: draft.tone }, draft.tone)}>Guardar tono</Button>{footer()}</Card>
          <Card title="Mensajes del asistente"><p>Personaliza los mensajes estándar. El menú de categorías se agrega automáticamente al saludo.</p>{(Object.keys(EMPTY_MESSAGES) as Array<keyof typeof EMPTY_MESSAGES>).map((key) => <Textarea key={key} label={{ greeting: "Saludo", cannot_answer: "Cuando no puede responder", clarification: "Aclaración", farewell: "Despedida", out_of_hours: "Fuera de horario" }[key]} rows={3} value={draft.messages[key]} onChange={(event) => update("messages", { ...draft.messages, [key]: event.target.value })} />)}<Button variant="secondary" disabled={saving("messages") || Object.values(draft.messages).some((value) => !value.trim())} onClick={() => void save("messages", "/panel/api/settings/messages", draft.messages, draft.messages)}>Guardar mensajes</Button>{footer()}</Card>
        </> : null}
        {active === "schedule" ? <>
          <Card title="Horarios de atención"><HoursEditor hours={draft.hours} onChange={(value) => update("hours", value)} /><Button variant="secondary" disabled={saving("hours") || !isValidHours(draft.hours)} onClick={() => void save("hours", "/panel/api/settings/hours", draft.hours, draft.hours)}>Guardar horarios</Button>{footer(SCHEDULE_NOTE)}</Card>
          <Card title="Notificaciones push"><PushSettings embedded /></Card>
        </> : null}
        {active === "costs" ? <>
          <Card title="Límites de gasto"><p>Topes de gasto por conversación y por día. Al 80% el agente se vuelve más conservador; al 100% se detienen las llamadas de pago y la conversación pasa a una persona.</p><Input label="Límite por conversación (USD)" type="number" value={draft.conversationLimit} onChange={(event) => update("conversationLimit", event.target.value)} /><Input label="Límite diario (USD)" type="number" value={draft.dailyLimit} onChange={(event) => update("dailyLimit", event.target.value)} /><Button variant="secondary" disabled={saving("conversationLimit") || saving("dailyLimit") || !numericLimitsValid} onClick={() => void save("conversationLimit", "/panel/api/settings/limits", { conversation_limit: Number(draft.conversationLimit), daily_limit: Number(draft.dailyLimit) }, draft.conversationLimit)}>Guardar límites</Button>{footer()}</Card>
          <Card title="Precio Meta"><p>Costo por mensaje de servicio (USD), vigente desde 2026-10-01.</p><Input label="Costo por mensaje (USD)" type="number" value={draft.metaCost} onChange={(event) => update("metaCost", event.target.value)} /><Button variant="secondary" disabled={saving("metaCost") || !isValidNonNegative(draft.metaCost)} onClick={() => void save("metaCost", "/panel/api/settings/meta", { service_message_cost: Number(draft.metaCost) }, draft.metaCost)}>Guardar precio</Button>{footer()}</Card>
          <Card title="Gasto actual"><DataTable columns={columns} rows={spendRows} rowKey={(row) => row.label} />{snapshot?.conversation_percent !== null ? <p>Conversación {snapshot?.conversation_percent}% de ${snapshot?.conversation_limit.toFixed(2)}</p> : null}</Card>
        </> : null}
        {active === "capabilities" ? capabilityHost : null}
      </div>}
    </Tabs>
    </div>
    {state === "empty" ? <Button onClick={retry}>Reintentar</Button> : null}
  </PageFrame>;
}
