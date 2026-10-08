import { useCallback, useEffect, useRef, useState } from "react";
import { CircleHelp, Globe2, ShieldAlert, ShieldCheck, SlidersHorizontal, Trash2, UserRound } from "lucide-react";
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
import { MessagePreview } from "../primitives/MessagePreview";
import { DayToggle } from "../primitives/DayToggle";
import { StatCard } from "../shared/StatCard";
import { PageFrame } from "../shared/PageFrame";
import { StateMessage } from "../shared/StateMessage";
import { PushSettings } from "./PushSettings";
import "./Settings.css";

export type SettingsState = AsyncDataState | "saved" | "saving" | "validation" | "server-error" | "stale";
export interface SettingsProps { data?: SettingsData | null; state?: SettingsState; onRetry?: () => void; capabilities?: AssistantCapabilities; }
const EMPTY_MESSAGES = { greeting: "", cannot_answer: "", clarification: "", farewell: "", out_of_hours: "" };
const SHORT_DAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const TIMEZONES = typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [];
const SECTIONS = [
  { id: "agent", label: "Agente" }, { id: "messages", label: "Mensajes" },
  { id: "schedule", label: "Horarios y avisos" }, { id: "costs", label: "Costos" },
  { id: "capabilities", label: "Capacidades" },
];
const MESSAGE_TEMPLATES = [
  { id: "greeting", label: "Saludo" },
  { id: "cannot_answer", label: "Cuando no puede responder" },
  { id: "clarification", label: "Aclaración" },
  { id: "farewell", label: "Despedida" },
  { id: "out_of_hours", label: "Fuera de horario" },
] as const;
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
  const [newDays, setNewDays] = useState<string[]>([]);
  const [newOpen, setNewOpen] = useState("09:00");
  const [newClose, setNewClose] = useState("18:00");
  const usedDays = hours.schedule.flatMap((entry) => entry.days).map((day) => SHORT_DAYS[day - 1]);
  const addSchedule = () => {
    const days = newDays.map((day) => SHORT_DAYS.indexOf(day) + 1).filter((day) => day > 0 && !usedDays.includes(SHORT_DAYS[day - 1]));
    if (!days.length || !newOpen || !newClose || newOpen >= newClose) return;
    onChange({ ...hours, schedule: [...hours.schedule, { days, open: newOpen, close: newClose }] });
    setNewDays([]);
  };
  const timezoneOptions = [...new Set([hours.timezone, ...TIMEZONES])].filter(Boolean).sort((left, right) => left.localeCompare(right));
  return <>
    <div className="settings-hours__timezone"><Globe2 aria-hidden="true" /><Select label="Zona horaria" value={hours.timezone} onChange={(event) => onChange({ ...hours, timezone: event.target.value })} options={timezoneOptions.map((timezone) => ({ value: timezone, label: timezone }))} /></div>
    <p>Define los días y el horario de atención. Cada día puede pertenecer a un solo horario.</p>
    <div className="settings-hours__list" aria-label="Horarios configurados">{hours.schedule.map((entry, index) => <div className="settings-hours__item" key={index}>
      <strong>Horario {index + 1}</strong><span>{entry.days.map((day) => SHORT_DAYS[day - 1]).join(", ") || "Sin días seleccionados"}</span><span>{entry.open} – {entry.close}</span>
      <Button variant="tertiary" aria-label={`Eliminar horario ${index + 1}`} onClick={() => onChange({ ...hours, schedule: hours.schedule.filter((_, currentIndex) => currentIndex !== index) })}><Trash2 aria-hidden="true" /> Eliminar</Button>
    </div>)}</div>
    <div className="settings-hours__new"><h3>Nuevo horario</h3>
      <DayToggle label="Días del nuevo horario" value={newDays} onChange={(value) => setNewDays(value.filter((day) => !usedDays.includes(day)))} />
      <div className="settings-hours__times"><Input label="Inicio" type="time" value={newOpen} onChange={(event) => setNewOpen(event.target.value)} /><Input label="Fin" type="time" value={newClose} onChange={(event) => setNewClose(event.target.value)} /></div>
      <Button variant="tertiary" disabled={!newDays.some((day) => !usedDays.includes(day)) || !newOpen || !newClose || newOpen >= newClose} onClick={addSchedule}>Agregar otro horario</Button>
    </div>
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
  const [activeMessage, setActiveMessage] = useState<(typeof MESSAGE_TEMPLATES)[number]["id"]>("greeting");
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
          <Card title="Tono del asistente" className="settings-messages__tone"><p>Define cómo suenan las respuestas del agente en cada conversación.</p><div className="settings-messages__tone-row"><Select label="Tono" value={draft.tone} onChange={(event) => update("tone", event.target.value)} options={[{ value: "", label: "Selecciona un tono" }, { value: "cercano", label: "Cercano" }, { value: "formal", label: "Formal" }, { value: "directo", label: "Directo" }]} /><Button variant="secondary" disabled={saving("tone") || !draft.tone.trim()} onClick={() => void save("tone", "/panel/api/settings/tone", { tone: draft.tone }, draft.tone)}>Guardar tono</Button></div>{footer()}</Card>
          <div className="settings-messages__layout">
            <Card title="Mensajes del asistente" className="settings-messages__editor"><p>Personaliza los mensajes estándar. El menú de categorías se agrega automáticamente al saludo.</p>
              <Tabs ariaLabel="Plantillas de mensajes" tabs={[...MESSAGE_TEMPLATES]} activeTab={activeMessage} onTabChange={(id) => setActiveMessage(id as typeof activeMessage)}>
                {(selected) => {
                  const template = MESSAGE_TEMPLATES.find(({ id }) => id === selected) ?? MESSAGE_TEMPLATES[0];
                  return <div className="settings-messages__edit">
                    <Textarea label={template.label} rows={5} value={draft.messages[template.id]} onChange={(event) => update("messages", { ...draft.messages, [template.id]: event.target.value })} />
                    <p className="settings-messages__info">Este mensaje se usa como respuesta automática para esta situación.</p>
                  </div>;
                }}
              </Tabs>
              <div className="settings-messages__footer"><Button variant="secondary" disabled={saving("messages") || Object.values(draft.messages).some((value) => !value.trim())} onClick={() => void save("messages", "/panel/api/settings/messages", draft.messages, draft.messages)}>Guardar mensajes</Button>{footer()}</div>
            </Card>
            <Card title="Vista previa" className="settings-messages__preview"><MessagePreview message={draft.messages[activeMessage]} /></Card>
          </div>
        </> : null}
        {active === "schedule" ? <div className="settings-hours__layout">
          <Card title="Horarios de atención"><HoursEditor hours={draft.hours} onChange={(value) => update("hours", value)} /><div className="settings-hours__footer"><Button variant="secondary" disabled={saving("hours") || !isValidHours(draft.hours)} onClick={() => void save("hours", "/panel/api/settings/hours", draft.hours, draft.hours)}>Guardar horarios</Button>{footer(SCHEDULE_NOTE)}</div></Card>
          <div className="settings-hours__aside"><Card title="Notificaciones push"><PushSettings embedded /></Card><Card title="Fuera de horario"><p>{draft.messages.out_of_hours || "Configura el mensaje que recibirán las personas fuera del horario de atención."}</p><Button variant="tertiary" onClick={() => { setActiveSection("messages"); setActiveMessage("out_of_hours"); }}>Editar mensaje →</Button></Card></div>
        </div> : null}
         {active === "costs" ? <>
           <Card title="Gasto actual" headerAction={snapshot ? <Badge tone="neutral">{snapshot.date}</Badge> : undefined}>
             {snapshot ? <StatCard metrics={[
               { label: "Gasto diario", value: `$${snapshot.daily_spend.toFixed(4)}`, context: snapshot.conversation_percent !== null ? `Conversación: ${snapshot.conversation_percent}% de $${snapshot.conversation_limit.toFixed(2)}` : undefined },
               { label: "Límite diario", value: `$${snapshot.daily_limit.toFixed(2)}` },
               { label: "Del límite utilizado", value: `${snapshot.daily_percent.toFixed(1)}%` },
             ]} /> : null}
           </Card>
           <Card title="Límites de gasto">
             <p>Define los topes máximos de gasto por conversación y por día.</p>
             <div className="settings-costs__limits">
               <div className="settings-costs__input"><Input label="Límite por conversación" type="number" value={draft.conversationLimit} onChange={(event) => update("conversationLimit", event.target.value)} /><span aria-hidden="true">USD</span></div>
               <div className="settings-costs__input"><Input label="Límite diario" type="number" value={draft.dailyLimit} onChange={(event) => update("dailyLimit", event.target.value)} /><span aria-hidden="true">USD</span></div>
             </div>
             <div className="settings-costs__footer"><Button variant="secondary" disabled={saving("conversationLimit") || saving("dailyLimit") || !numericLimitsValid} onClick={() => void save("conversationLimit", "/panel/api/settings/limits", { conversation_limit: Number(draft.conversationLimit), daily_limit: Number(draft.dailyLimit) }, draft.conversationLimit)}>Guardar límites</Button>{footer()}</div>
           </Card>
           <Card title="Precio Meta" headerAction={<Badge tone="neutral">Vigente desde 2026-10-01</Badge>}>
             <div className="settings-costs__input"><Input label="Costo por mensaje" type="number" value={draft.metaCost} onChange={(event) => update("metaCost", event.target.value)} /><span aria-hidden="true">USD</span></div>
             <div className="settings-costs__footer"><Button variant="secondary" disabled={saving("metaCost") || !isValidNonNegative(draft.metaCost)} onClick={() => void save("metaCost", "/panel/api/settings/meta", { service_message_cost: Number(draft.metaCost) }, draft.metaCost)}>Guardar precio</Button>{footer()}</div>
           </Card>
           <Card title="Qué ocurre al alcanzar los límites">
             <div className="settings-costs__threshold"><ShieldCheck aria-hidden="true" /><strong>80%</strong><span>Respuestas más conservadoras</span></div>
             <div className="settings-costs__threshold"><UserRound aria-hidden="true" /><strong>100%</strong><span>Derivación a una persona</span></div>
           </Card>
        </> : null}
        {active === "capabilities" ? capabilityHost : null}
      </div>}
    </Tabs>
    </div>
    {state === "empty" ? <Button onClick={retry}>Reintentar</Button> : null}
  </PageFrame>;
}
