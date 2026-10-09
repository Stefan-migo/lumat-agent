import { useCallback, useEffect, useRef, useState } from "react";
import { Bell, BookOpen, Brain, CircleHelp, Clock3, DoorOpen, Globe2, Headset, Info, MessageCircle, Plus, ShieldAlert, ShieldCheck, SlidersHorizontal, Trash2, UserRound, Wrench } from "lucide-react";
import { apiFetch, getAssistantCapabilities, postJson } from "../../api";
import { useAsyncData, type AsyncDataState } from "../../hooks/useAsyncData";
import type { AssistantCapabilities, Settings as SettingsData } from "../../types";
import { Button } from "../primitives/Button";
import { Badge } from "../primitives/Badge";
import { Accordion } from "../primitives/Accordion";
import { Card } from "../primitives/Card";
import { HelpPanel } from "../primitives/HelpPanel";
import { Input } from "../primitives/Input";
import { Select } from "../primitives/Select";
import { Menu } from "../primitives/Menu";
import { SearchInput } from "../primitives/SearchInput";
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
  { id: "greeting", label: "Saludo", description: "Inicio de conversación", icon: MessageCircle },
  { id: "cannot_answer", label: "Cuando no puede responder", description: "Derivación a un asesor", icon: Headset },
  { id: "clarification", label: "Aclaración", description: "Mensaje no entendido", icon: CircleHelp },
  { id: "farewell", label: "Despedida", description: "Cierre de conversación", icon: DoorOpen },
  { id: "out_of_hours", label: "Fuera de horario", description: "Atención no disponible", icon: Clock3 },
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
    resetDraft();
  };
  const resetDraft = () => { setNewDays([]); setNewOpen("09:00"); setNewClose("18:00"); };
  const timezoneOptions = [...new Set([hours.timezone, ...TIMEZONES])].filter(Boolean).sort((left, right) => left.localeCompare(right));
  return <>
    <div className="settings-hours__timezone"><Globe2 aria-hidden="true" /><Select label="Zona horaria" value={hours.timezone} onChange={(event) => onChange({ ...hours, timezone: event.target.value })} options={timezoneOptions.map((timezone) => ({ value: timezone, label: timezone }))} /></div>
    <section className="settings-hours__weekly" aria-label="Horarios semanales"><h3>Horarios semanales</h3>
    {hours.schedule.length ? <div className="settings-hours__list" aria-label="Horarios configurados">{hours.schedule.map((entry, index) => <div className="settings-hours__item" key={index}>
      <strong>Horario {index + 1}</strong><span>{entry.days.map((day) => SHORT_DAYS[day - 1]).join(", ") || "Sin días seleccionados"}</span><span>{entry.open} – {entry.close}</span>
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
  const groupNames: Record<string, string> = { kb: "Conocimiento y memoria", memory: "Conocimiento y memoria", web: "Web", system: "Sistema", agenda: "Operación", cases: "Operación", customers: "Operación", projects: "Operación" };
  const groupedTools = new Map<string, AssistantCapabilities["tools"]>();
  filteredTools.forEach((tool) => {
    const namespace = tool.name.includes(".") ? tool.name.split(".")[0] : "system";
    groupedTools.set(namespace, [...(groupedTools.get(namespace) ?? []), tool]);
  });
  const groups = [...groupedTools].map(([namespace, tools]) => ({ namespace, title: groupNames[namespace] ?? (namespace === "system" ? "Sistema" : namespace), tools }))
    .sort((left, right) => left.title.localeCompare(right.title) || left.namespace.localeCompare(right.namespace));
  const accessOptions = [{ value: "all", label: "Todos los accesos" }, { value: "read", label: "Solo lectura" }, { value: "write", label: "Puede escribir" }, { value: "limited", label: "Acceso limitado" }];
  const availability = (available: boolean) => <span className={`settings-capabilities__availability${available ? " is-available" : ""}`}><span aria-hidden="true" />{available ? "Disponible" : "No disponible"}</span>;
  return <div className="settings-capabilities__layout">
    <Card title="Herramientas del asistente" headerAction={<Badge tone="neutral">{capabilities.tools.length}</Badge>}>
      <div className="settings-capabilities__filters"><SearchInput aria-label="Buscar herramientas" placeholder="Buscar herramientas" onSearch={setQuery} /><Select label="Acceso" value={access} onChange={(event) => setAccess(event.target.value)} options={accessOptions} /></div>
      <div className="settings-capabilities__groups">{groups.map(({ namespace, title, tools }) => <Accordion key={namespace} title={title} count={tools.length} defaultExpanded>
        <ul className="settings-capabilities__tools">{tools.map((tool) => <li className="settings-capabilities__tool" key={tool.name}>
          <Wrench aria-hidden="true" /><span className="settings-capabilities__tool-copy"><strong>{tool.name.split(".").at(-1)?.replaceAll("_", " ")}</strong><code>{tool.name}</code></span>
          <Badge tone={toolAccess(tool) === "write" ? "warning" : "neutral"}>{toolAccess(tool) === "write" ? "Puede escribir" : toolAccess(tool) === "read" ? "Solo lectura" : "Acceso limitado"}</Badge>
        </li>)}</ul>
      </Accordion>)}</div>
      {!filteredTools.length ? <p className="settings-capabilities__empty">No hay herramientas que coincidan con la búsqueda.</p> : null}
    </Card>
    <Card title="Configuración activa" headerAction={<a className="btn btn--tertiary" href="/panel/app/kb">Consultar</a>}>
      <div className="settings-capabilities__availability-row"><BookOpen aria-hidden="true" /><span>Base de conocimientos</span>{availability(capabilities.kb_available)}</div>
      <div className="settings-capabilities__availability-row"><Brain aria-hidden="true" /><span>Memoria</span>{availability(capabilities.memory_available)}</div>
      <div className="settings-capabilities__paths"><div><strong>Persona</strong><span>{capabilities.personas.join(", ") || "Sin configurar"}</span></div><div><strong>Prompts</strong><span>{capabilities.prompts.join(", ") || "Sin configurar"}</span></div></div>
      <p className="settings__footer-note">{GENERIC_NOTE}</p>
    </Card>
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
     <div className="settings-tabs__select"><Menu label={SECTIONS.find(({ id }) => id === activeSection)?.label ?? "Agente"} ariaLabel="Sección" showChevron items={SECTIONS.map(({ id, label }) => ({ value: id, label }))} onSelect={setActiveSection} /></div>
    <Tabs ariaLabel="Secciones de configuración" tabs={SECTIONS} activeTab={activeSection} onTabChange={setActiveSection}>
      {(active) => <div className="settings-tabs__content">
        {active === "agent" ? <>
          <div className="settings-agent__row">
            <Card title="Alcance del agente" description="Define en qué categorías el agente responde de forma automática y en cuáles siempre deriva a una persona." icon={SlidersHorizontal} headerAction={<Badge tone="neutral">Avanzado</Badge>}>
              <div className="settings-agent__layout">
                <div className="settings-agent__form">
                  <Textarea label="Reglas de alcance" rows={4} placeholder="Ej: reparación=bot_resolve" value={draft.scope} onChange={(event) => update("scope", event.target.value)} />
                  <details><summary>Sintaxis avanzada</summary><p>Escribe una categoría y un modo en cada línea, separados por un signo igual. <code>bot_resolve</code> significa que el agente responde por su cuenta; <code>always_escalate</code> significa que deriva la conversación a una persona. Por ejemplo: <code>presupuesto=bot_resolve</code>.</p></details>
                  <div className="settings-agent__footer">{footer()}<Button disabled={saving("scope") || !draft.scope.trim() || !draft.scope.split("\n").map((line) => line.trim()).filter(Boolean).every((line) => { const [category, mode] = line.split("=").map((value) => value.trim()); return Boolean(category) && ["bot_resolve", "always_escalate"].includes(mode); })} onClick={saveScope}>Guardar alcance</Button></div>
                </div>
                <HelpPanel icon={CircleHelp} title="Cómo funciona"><p>El agente responde de forma automática en las categorías configuradas y deriva a una persona cuando la regla lo indica.</p><p>Usa una categoría por línea. Conserva las reglas actuales si no estás seguro del efecto de un cambio.</p></HelpPanel>
              </div>
            </Card>
          </div>
          <div className="settings-agent__row">
            <Card title="Detección de emergencias" description="Palabras que activan un aviso de emergencia. Se detectan en el próximo mensaje entrante." icon={ShieldAlert}>
              <div className="settings-agent__layout">
                <div className="settings-agent__form">
                  <Textarea label="Palabras clave de emergencia" rows={6} value={draft.keywords} onChange={(event) => update("keywords", event.target.value)} />
                  <p className="settings-agent__helper">Escribe una palabra o frase por línea.</p>
                  <div className="settings-agent__footer">{footer()}<Button disabled={saving("keywords") || !draft.keywords.split("\n").some((value) => value.trim())} onClick={() => void save("keywords", "/panel/api/settings/keywords", { keywords: draft.keywords.split("\n").map((value) => value.trim()).filter(Boolean) }, draft.keywords)}>Guardar palabras clave</Button></div>
                </div>
                <HelpPanel icon={ShieldAlert} title="Consideraciones"><p>Las palabras clave se revisan en cada mensaje entrante y activan el aviso correspondiente.</p><p>Incluye términos claros y evita agregar palabras ambiguas que puedan generar avisos innecesarios.</p></HelpPanel>
              </div>
            </Card>
          </div>
        </> : null}
        {active === "messages" ? <>
          <Card title="Tono del asistente" description="Define cómo suenan las respuestas en cada conversación." className="settings-messages__tone" headerAction={<div className="settings-messages__tone-row"><Menu label={draft.tone ? draft.tone[0].toUpperCase() + draft.tone.slice(1) : "Selecciona un tono"} ariaLabel="Tono" showChevron items={[{ value: "cercano", label: "Cercano" }, { value: "formal", label: "Formal" }, { value: "directo", label: "Directo" }]} onSelect={(value) => update("tone", value)} /><Button disabled={saving("tone") || !draft.tone.trim()} onClick={() => void save("tone", "/panel/api/settings/tone", { tone: draft.tone }, draft.tone)}>Guardar tono</Button></div>} >{null}</Card>
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
        </> : null}
        {active === "schedule" ? <div className="settings-hours__layout">
          <Card title="Horarios de atención" description="Define los días y las horas en que atiende tu equipo."><HoursEditor hours={draft.hours} onChange={(value) => update("hours", value)} /><div className="settings-hours__footer"><Button variant="secondary" disabled={saving("hours") || !isValidHours(draft.hours)} onClick={() => void save("hours", "/panel/api/settings/hours", draft.hours, draft.hours)}>Guardar horarios</Button>{footer(SCHEDULE_NOTE)}</div></Card>
          <div className="settings-hours__aside"><Card title="Notificaciones push" icon={Bell}><PushSettings embedded /></Card><Card title="Fuera de horario" icon={Clock3}><p>{draft.messages.out_of_hours || "Configura el mensaje que recibirán las personas fuera del horario de atención."}</p><Button variant="tertiary" className="settings-hours__edit-message" onClick={() => { setActiveSection("messages"); setActiveMessage("out_of_hours"); }}>Editar mensaje →</Button></Card></div>
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
